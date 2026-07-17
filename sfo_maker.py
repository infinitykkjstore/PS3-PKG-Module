"""
sfo_maker - Create PS3 PARAM.SFO files from scratch

CLI:
  python sfo_maker.py -o PARAM.SFO [--title ...] [--title-id ...] ...
"""

from __future__ import annotations
import argparse
import struct
import sys
from typing import Union

SFO_MAGIC = b'\x00PSF'
HEADER_SIZE = 20
INDEX_ENTRY_SIZE = 16

FORMAT_UTF8 = 0x0004
FORMAT_UTF8_NULL = 0x0204
FORMAT_INT32 = 0x0404

FORMAT_NAMES = {
    0x0004: 'Utf8',
    0x0204: 'Utf8Null',
    0x0404: 'Int32',
}

class SFOEntry:
    def __init__(
        self,
        key: str,
        fmt: int,
        value: Union[str, int],
        value_max_length: int | None = None,
    ):
        self.key = key
        self.format = fmt
        if fmt == FORMAT_INT32:
            if not isinstance(value, int):
                raise TypeError('Int32 format requires an integer value')
            self.value = value
            self.value_length = 4
            self.value_max_length = 4 if value_max_length is None else value_max_length
        elif fmt == FORMAT_UTF8:
            if not isinstance(value, str):
                raise TypeError('Utf8 format requires a string value')
            encoded = value.encode('utf-8')
            self._raw = encoded
            self.value_length = len(encoded)
            self.value_max_length = (
                self.value_length if value_max_length is None else value_max_length
            )
            self.value = value
        elif fmt == FORMAT_UTF8_NULL:
            if not isinstance(value, str):
                raise TypeError('Utf8Null format requires a string value')
            encoded = value.encode('utf-8')
            self._raw = encoded
            self.value_length = len(encoded) + 1
            self.value_max_length = (
                self.value_length if value_max_length is None else value_max_length
            )
            self.value = value
        else:
            raise ValueError(f'Unknown format: 0x{fmt:04x}')

    def build_value_bytes(self) -> bytes:
        if self.format == FORMAT_INT32:
            buf = struct.pack('<I', self.value)
            diff = self.value_max_length - len(buf)
            if diff > 0:
                buf += b'\x00' * diff
            return buf[:self.value_max_length]
        elif self.format == FORMAT_UTF8:
            buf = bytearray(self._raw)
            diff = self.value_max_length - len(buf)
            if diff > 0:
                buf.extend(b'\x00' * diff)
            return bytes(buf[:self.value_max_length])
        elif self.format == FORMAT_UTF8_NULL:
            buf = bytearray(self._raw) + b'\x00'
            diff = self.value_max_length - len(buf)
            if diff > 0:
                buf.extend(b'\x00' * diff)
            return bytes(buf[:self.value_max_length])

    def __repr__(self):
        return f'SFOEntry({self.key!r}, 0x{self.format:04x}, {self.value!r})'


def make_sfo(
    entries: list[SFOEntry],
    major_version: int = 1,
    minor_version: int = 1,
    reserved1: int = 0,
) -> bytes:
    count = len(entries)
    keys_offset = HEADER_SIZE + count * INDEX_ENTRY_SIZE

    key_table = b''
    key_offsets = []
    for e in entries:
        key_offsets.append(len(key_table))
        key_bytes = e.key.encode('utf-8') + b'\x00'
        key_table += key_bytes

    while len(key_table) % 4 != 0:
        key_table += b'\x00'

    values_offset = keys_offset + len(key_table)

    value_table = b''
    value_offsets = []
    for e in entries:
        value_offsets.append(len(value_table))
        value_table += e.build_value_bytes()

    header = struct.pack(
        '<4sBBhIII',
        SFO_MAGIC,
        major_version,
        minor_version,
        reserved1 & 0xFFFF,
        keys_offset,
        values_offset,
        count,
    )

    index_table = b''
    for i, e in enumerate(entries):
        index_table += struct.pack(
            '<HHIII',
            key_offsets[i],
            e.format,
            e.value_length,
            e.value_max_length,
            value_offsets[i],
        )

    return header + index_table + key_table + value_table


def make_default_sfo(
    title: str = 'The Simpsons - Road Rage',
    title_id: str = 'SLUS20305',
    category: str = '2P',
    bootable: int = 1,
    attribute: int = 0,
    parental_level: int = 0,
    ps3_system_ver: str = '03.4000',
    region_deny: int = 0,
) -> bytes:
    entries = [
        SFOEntry('ATTRIBUTE', FORMAT_INT32, attribute),
        SFOEntry('BOOTABLE', FORMAT_INT32, bootable),
        SFOEntry('CATEGORY', FORMAT_UTF8_NULL, category, value_max_length=4),
        SFOEntry('PARENTAL_LEVEL', FORMAT_INT32, parental_level),
        SFOEntry('PS3_SYSTEM_VER', FORMAT_UTF8_NULL, ps3_system_ver),
        SFOEntry('REGION_DENY', FORMAT_INT32, region_deny),
        SFOEntry('TITLE', FORMAT_UTF8_NULL, title, value_max_length=128),
        SFOEntry('TITLE_ID', FORMAT_UTF8_NULL, title_id, value_max_length=16),
    ]
    return make_sfo(entries)


def cli():
    parser = argparse.ArgumentParser(description='Create a PS3 PARAM.SFO file')
    parser.add_argument('-o', '--output', default='PARAM.SFO', help='Output file (default: PARAM.SFO)')
    parser.add_argument('--title', default='The Simpsons - Road Rage', help='Game title')
    parser.add_argument('--title-id', default='SLUS20305', help='Title ID')
    parser.add_argument('--category', default='2P', help='Category (HG, DG, 2P, etc)')
    parser.add_argument('--bootable', type=int, default=1, help='Bootable flag (0 or 1)')
    parser.add_argument('--attribute', type=int, default=0, help='Attribute')
    parser.add_argument('--parental-level', type=int, default=0, help='Parental control level')
    parser.add_argument('--ps3-system-ver', default='03.4000', help='Minimum PS3 system version')
    parser.add_argument('--region-deny', type=int, default=0, help='Region deny flags')
    args = parser.parse_args()

    data = make_default_sfo(
        title=args.title,
        title_id=args.title_id,
        category=args.category,
        bootable=args.bootable,
        attribute=args.attribute,
        parental_level=args.parental_level,
        ps3_system_ver=args.ps3_system_ver,
        region_deny=args.region_deny,
    )
    with open(args.output, 'wb') as f:
        f.write(data)
    print(f'SFO criado: {args.output} ({len(data)} bytes)')


if __name__ == '__main__':
    cli()
