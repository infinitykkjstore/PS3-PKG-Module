"""
sfo_editor - Read, edit, and write PS3 PARAM.SFO files

CLI:
  python sfo_editor.py PARAM.SFO              # show contents
  python sfo_editor.py PARAM.SFO --set TITLE="New Title"
  python sfo_editor.py PARAM.SFO --title "New" --bootable 0
"""

from __future__ import annotations
import argparse
import struct
import os
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
        key_raw: bytes,
        fmt: int,
        value_length: int,
        value_max_length: int,
        value_offset: int,
        binary_value: bytes,
    ):
        self.key_raw = key_raw
        self.key = key_raw.rstrip(b'\x00').decode('utf-8')
        self.format = fmt
        self.value_length = value_length
        self.value_max_length = value_max_length
        self.value_offset = value_offset
        self.binary_value = binary_value

    @property
    def value(self) -> Union[str, int]:
        if self.format == FORMAT_INT32:
            return struct.unpack('<I', self.binary_value[:4])[0]
        elif self.format in (FORMAT_UTF8, FORMAT_UTF8_NULL):
            return self.binary_value[:self.value_length].rstrip(b'\x00').decode('utf-8', errors='replace')
        else:
            return self.binary_value.hex()

    @value.setter
    def value(self, val: Union[str, int]):
        if self.format == FORMAT_INT32:
            if not isinstance(val, int):
                raise TypeError('Int32 format requires an integer value')
            packed = struct.pack('<I', val)
            new_len = 4
        elif self.format == FORMAT_UTF8:
            if not isinstance(val, str):
                raise TypeError('Utf8 format requires a string value')
            packed = val.encode('utf-8')
            new_len = len(packed)
        elif self.format == FORMAT_UTF8_NULL:
            if not isinstance(val, str):
                raise TypeError('Utf8Null format requires a string value')
            packed = val.encode('utf-8') + b'\x00'
            new_len = len(val.encode('utf-8')) + 1
        else:
            raise ValueError(f'Unknown format: 0x{self.format:04x}')

        if new_len > self.value_max_length:
            raise ValueError(
                f'Value too long: {new_len} bytes, max is {self.value_max_length} bytes'
            )

        buf = bytearray(self.binary_value)
        buf[:len(packed)] = packed
        if len(packed) < len(buf):
            buf[len(packed):] = b'\x00' * (len(buf) - len(packed))
        self.binary_value = bytes(buf)
        self.value_length = new_len

    def __repr__(self):
        return f'SFOEntry({self.key!r}, 0x{self.format:04x}, {self.value!r})'


class SFOFile:
    def __init__(self):
        self.major_version = 1
        self.minor_version = 1
        self.reserved1 = 0
        self.entries: list[SFOEntry] = []
        self._source_path: str | None = None
        self._original_bytes: bytes | None = None
        self._dirty = False

    @classmethod
    def from_bytes(cls, data: bytes) -> SFOFile:
        if len(data) < HEADER_SIZE:
            raise ValueError('File too small for SFO header')

        magic = data[:4]
        if magic != SFO_MAGIC:
            raise ValueError(f'Invalid magic: {magic!r}')

        sfo = cls()
        sfo._original_bytes = data

        sfo.major_version = data[4]
        sfo.minor_version = data[5]
        sfo.reserved1 = struct.unpack('<h', data[6:8])[0]
        keys_offset = struct.unpack('<I', data[8:12])[0]
        values_offset = struct.unpack('<I', data[12:16])[0]
        count = struct.unpack('<I', data[16:20])[0]

        sfo.entries = []
        for i in range(count):
            off = HEADER_SIZE + i * INDEX_ENTRY_SIZE
            k_off = struct.unpack('<H', data[off:off+2])[0]
            fmt = struct.unpack('<H', data[off+2:off+4])[0]
            vlen = struct.unpack('<I', data[off+4:off+8])[0]
            vmax = struct.unpack('<I', data[off+8:off+12])[0]
            voff = struct.unpack('<I', data[off+12:off+16])[0]

            key_start = keys_offset + k_off
            key_end = data.index(0, key_start)
            key_raw = data[key_start:key_end + 1]

            val_start = values_offset + voff
            binary_value = data[val_start:val_start + vmax]

            entry = SFOEntry(
                key_raw=key_raw,
                fmt=fmt,
                value_length=vlen,
                value_max_length=vmax,
                value_offset=voff,
                binary_value=binary_value,
            )
            sfo.entries.append(entry)

        return sfo

    @classmethod
    def load(cls, path: str) -> SFOFile:
        with open(path, 'rb') as f:
            data = f.read()
        sfo = cls.from_bytes(data)
        sfo._source_path = path
        return sfo

    def save(self, path: str | None = None) -> None:
        target = path or self._source_path
        if target is None:
            raise ValueError('No path specified')
        bak = target + '.bak'
        if not os.path.exists(bak) and os.path.exists(target):
            os.rename(target, bak)
        data = self.to_bytes()
        with open(target, 'wb') as f:
            f.write(data)
        self._original_bytes = data
        self._dirty = False

    def to_bytes(self) -> bytes:
        count = len(self.entries)
        keys_offset = HEADER_SIZE + count * INDEX_ENTRY_SIZE

        key_table = b''
        key_offsets = []
        for e in self.entries:
            key_offsets.append(len(key_table))
            key_table += e.key_raw

        while len(key_table) % 4 != 0:
            key_table += b'\x00'

        values_offset = keys_offset + len(key_table)

        value_table = b''
        value_offsets = []
        for e in self.entries:
            value_offsets.append(len(value_table))
            value_table += e.binary_value

        header = struct.pack(
            '<4sBBhIII',
            SFO_MAGIC,
            self.major_version,
            self.minor_version,
            self.reserved1 & 0xFFFF,
            keys_offset,
            values_offset,
            count,
        )

        index_table = b''
        for i, e in enumerate(self.entries):
            index_table += struct.pack(
                '<HHIII',
                key_offsets[i],
                e.format,
                e.value_length,
                e.value_max_length,
                value_offsets[i],
            )

        return header + index_table + key_table + value_table

    def find_entry(self, key: str) -> SFOEntry | None:
        for e in self.entries:
            if e.key == key:
                return e
        return None

    def get_value(self, key: str) -> Union[str, int, None]:
        e = self.find_entry(key)
        return e.value if e else None

    def set_value(self, key: str, value: Union[str, int]):
        e = self.find_entry(key)
        if e is None:
            raise KeyError(f'Entry not found: {key}')
        e.value = value
        self._dirty = True

    @property
    def title(self) -> str:
        val = self.get_value('TITLE')
        return str(val) if val is not None else ''

    @title.setter
    def title(self, val: str):
        self.set_value('TITLE', val)

    @property
    def title_id(self) -> str:
        val = self.get_value('TITLE_ID')
        return str(val) if val is not None else ''

    @title_id.setter
    def title_id(self, val: str):
        self.set_value('TITLE_ID', val)

    @property
    def category(self) -> str:
        val = self.get_value('CATEGORY')
        return str(val) if val is not None else ''

    @category.setter
    def category(self, val: str):
        self.set_value('CATEGORY', val)

    @property
    def bootable(self) -> int:
        val = self.get_value('BOOTABLE')
        return int(val) if val is not None else 0

    @bootable.setter
    def bootable(self, val: int):
        self.set_value('BOOTABLE', val)

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def __repr__(self):
        return f'SFOFile({len(self.entries)} entries, v{self.major_version}.{self.minor_version})'


def read_sfo(path: str) -> SFOFile:
    return SFOFile.load(path)


def write_sfo(sfo: SFOFile, path: str | None = None) -> None:
    sfo.save(path)


def _fmt_name(f: int) -> str:
    return FORMAT_NAMES.get(f, f'0x{f:04x}')


def _show(sfo: SFOFile):
    print(f'SFO v{sfo.major_version}.{sfo.minor_version}  |  {len(sfo.entries)} entries')
    print()
    for e in sfo.entries:
        if e.format == FORMAT_INT32:
            val = f'{e.value} (0x{e.value:08x})'
        else:
            val = str(e.value)
        print(f'  {e.key:22s}  {_fmt_name(e.format):10s}  len={e.value_length:4d}  '
              f'max={e.value_max_length:4d}  val={val}')
    if sfo._source_path:
        size = os.path.getsize(sfo._source_path)
        print(f'\nFile: {sfo._source_path} ({size} bytes)')


def cli():
    parser = argparse.ArgumentParser(description='Read and edit PS3 PARAM.SFO files')
    parser.add_argument('sfo', help='Path to PARAM.SFO file')
    parser.add_argument('-o', '--output', help='Output file (default: edit in-place)')
    parser.add_argument('--show', action='store_true', help='Display SFO contents')
    parser.add_argument('--title', help='Set game title')
    parser.add_argument('--title-id', help='Set title ID')
    parser.add_argument('--category', help='Set category')
    parser.add_argument('--bootable', type=int, choices=[0, 1], help='Set bootable flag')
    parser.add_argument('--attribute', type=int, help='Set attribute')
    parser.add_argument('--parental-level', type=int, help='Set parental control level')
    parser.add_argument('--ps3-system-ver', help='Set minimum PS3 system version')
    parser.add_argument('--region-deny', type=int, help='Set region deny flags')
    parser.add_argument('--set', action='append', metavar='KEY=VALUE',
                        help='Set any field (e.g. --set TITLE="My Game")')
    args = parser.parse_args()

    sfo = SFOFile.load(args.sfo)
    changed = False

    direct = [
        ('title', args.title),
        ('title_id', args.title_id),
        ('category', args.category),
    ]
    for attr, val in direct:
        if val is not None:
            setattr(sfo, attr, val)
            changed = True

    int_fields = [
        ('bootable', args.bootable),
        ('attribute', args.attribute),
        ('parental_level', args.parental_level),
        ('region_deny', args.region_deny),
    ]
    for attr, val in int_fields:
        if val is not None:
            sfo.set_value(attr.upper(), val)
            changed = True

    if args.ps3_system_ver is not None:
        sfo.set_value('PS3_SYSTEM_VER', args.ps3_system_ver)
        changed = True

    if args.set:
        for kv in args.set:
            if '=' not in kv:
                print(f'error: --set argument must be KEY=VALUE, got {kv!r}', file=sys.stderr)
                sys.exit(1)
            key, val = kv.split('=', 1)
            entry = sfo.find_entry(key.upper())
            if entry is None:
                print(f'error: entry {key.upper()!r} not found in SFO', file=sys.stderr)
                sys.exit(1)
            if entry.format == FORMAT_INT32:
                entry.value = int(val, 0)
            else:
                entry.value = val
            changed = True

    if changed:
        target = args.output or args.sfo
        sfo.save(target)
        print(f'SFO salvo: {target}')
    else:
        _show(sfo)


if __name__ == '__main__':
    cli()
