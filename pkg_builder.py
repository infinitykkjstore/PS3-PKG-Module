#!/usr/bin/env python3
"""
PS3 Custom PKG Builder - Monta um .pkg custom a partir de ./custom/
A estrutura de diretorios em custom/ espelha o HDD do PS3:
    custom/dev_hdd0/... -> /dev_hdd0/... no console
"""
import os, sys, struct, hashlib, argparse

PKG_MAGIC = 0x7F504B47

TYPE_RAW = 3
TYPE_DIRECTORY = 4
FLAG_OVERWRITE = 0x80000000

PREFIX_PATH = b'../../'
PREFIX_LEN = len(PREFIX_PATH)


def _u64(d, o):
    return struct.unpack('>Q', d[o:o+8])[0]


def _key_to_context(key_16):
    k = bytearray(64)
    k[0:8] = key_16[0:8]
    k[8:16] = key_16[0:8]
    k[16:24] = key_16[8:16]
    k[24:32] = key_16[8:16]
    return k


def _inc_ctr(k):
    ctr = _u64(bytes(k), 0x38)
    ctr = (ctr + 1) & 0xFFFFFFFFFFFFFFFF
    k[0x38:0x40] = struct.pack('>Q', ctr)


def _set_ctr(k, value):
    k[0x38:0x40] = struct.pack('>Q', value & 0xFFFFFFFFFFFFFFFF)


def _crypt(data, key_16):
    k = _key_to_context(key_16)
    out = bytearray(len(data))
    for i in range(0, len(data), 16):
        h = hashlib.sha1(bytes(k)).digest()[:16]
        block = data[i:i+16]
        for j in range(len(block)):
            out[i+j] = block[j] ^ h[j]
        _inc_ctr(k)
    return bytes(out)


def _crypt_at_ctr(data, key_16, ctr_value):
    k = _key_to_context(key_16)
    _set_ctr(k, ctr_value)
    h = hashlib.sha1(bytes(k)).digest()[:len(data)]
    return bytes(a ^ b for a, b in zip(data, h))


def _aligned(v, a=16):
    return (v + a - 1) & ~(a - 1)


def build_pkg(input_dir, content_id, output_path):
    input_dir = os.path.normpath(input_dir) + os.sep
    base_len = len(input_dir)

    files = []

    for root, dirs, fnames in os.walk(input_dir):
        for d in sorted(dirs):
            full = os.path.join(root, d) + os.sep
            rel = full[base_len:].replace(os.sep, '/')
            if not rel:
                continue
            files.append({
                'name': rel,
                'is_dir': True,
                'size': 0,
            })
        for f in sorted(fnames):
            full = os.path.join(root, f)
            rel = full[base_len:].replace(os.sep, '/')
            files.append({
                'name': rel,
                'is_dir': False,
                'size': os.path.getsize(full),
                'path': full,
            })

    item_cnt = len(files)

    # --- build header (zeros for QADigest now) ---
    content_id_bytes = content_id.encode('ascii', errors='replace').ljust(48, b'\x00')[:48]

    header = struct.pack('>IIIIIIQQQ',
        PKG_MAGIC, 0x01, 0xC0, 0x05,
        0x80, item_cnt,
        0,   # packageSize (placeholder)
        0x140,  # dataOff
        0,   # dataSize (placeholder)
    )
    header += content_id_bytes
    header += b'\x00' * 16  # QADigest placeholder
    header += b'\x00' * 16  # KLicensee placeholder

    assert len(header) == 0x80, f"Header size: {len(header)} != 0x80"

    # --- build file table data ---
    first_enc = bytearray()

    # Phase 1: assign fileNameOff (after all entries)
    name_off = 0x20 * item_cnt
    for f in files:
        name_len = PREFIX_LEN + len(f['name'])
        aligned = _aligned(name_len)
        f['name_off'] = name_off
        f['name_len_aligned'] = aligned
        f['name_len_total'] = name_len
        name_off += aligned

    # Phase 2: assign fileOff and pack entries
    data_off_area = name_off
    for f in files:
        f['file_off'] = data_off_area
        data_off_area += _aligned(f['size'])

    for f in files:
        flags = FLAG_OVERWRITE | (TYPE_DIRECTORY if f['is_dir'] else TYPE_RAW)
        entry = struct.pack('>IIQQII',
            f['name_off'],
            f['name_len_total'],
            f['file_off'],
            f['size'],
            flags,
            0,
        )
        first_enc += entry

    # Phase 3: pack names
    for f in files:
        raw_name = PREFIX_PATH + f['name'].encode('ascii', errors='replace')
        raw_name += b'\x00' * (f['name_len_aligned'] - f['name_len_total'])
        first_enc += raw_name

    # Phase 4: pack file data
    file_data_chunks = []
    for f in files:
        if f['is_dir']:
            continue
        with open(f['path'], 'rb') as fh:
            chunk = fh.read()
        chunk += b'\x00' * (_aligned(f['size']) - f['size'])
        file_data_chunks.append(chunk)

    file_data = b''.join(file_data_chunks)

    assert len(first_enc) == name_off, f"first_enc size: {len(first_enc)} != name_off {name_off}"

    # --- compute QA_Digest ---
    qa = hashlib.sha1()
    qa.update(header)
    qa.update(bytes(first_enc))
    qa_digest = qa.digest()

    # Update header with QADigest
    header = header[:0x60] + qa_digest + header[0x70:]

    # --- compute KLicensee (encrypted zeros using QADigest, counter=0xFFFFFFFFFFFFFFFF) ---
    licensee_enc = _crypt_at_ctr(b'\x00' * 16, qa_digest, 0xFFFFFFFFFFFFFFFF)
    header = header[:0x70] + licensee_enc

    data_size = len(first_enc) + len(file_data)
    package_size = 0x140 + data_size + 0x60

    header = struct.pack('>IIIIIIQQQ',
        PKG_MAGIC, 0x01, 0xC0, 0x05,
        0x80, item_cnt,
        package_size,
        0x140,
        data_size,
    ) + header[0x30:0x30+48] + header[0x60:0x60+16] + header[0x70:0x70+16]

    # --- write output ---
    with open(output_path, 'wb') as out:
        # 1. Header
        out.write(header)

        # 2. headerSHA = SHA1(header)[3:19]
        hdr_sha = hashlib.sha1(header).digest()[3:19]
        out.write(hdr_sha)

        # 3. Double-encrypted null padding
        meta_block = struct.pack('>IIIIIIIIIIIHHfIIHH',
            1,    # unk1
            4,    # unk2
            3,    # drmType (Free)
            2,    # unk4
            4,    # unk21
            9,    # contentType (Theme, default for custom)
            3,    # unk23
            4,    # unk24
            0xE,  # packageType (normal)
            4,    # unk32
            8,    # unk33
            0,    # secondaryVersion
            0,    # unk34
            float(data_size),  # dataSize as float
            5,    # unk42
            4,    # unk43
            0x1061, # packagedBy
            0,    # packageVersion
        )
        meta_sha = hashlib.sha1(meta_block).digest()[3:19]

        pad_null = b'\x00' * 0x30

        enc_once = _crypt(pad_null, meta_sha)
        enc_twice = _crypt(enc_once, hdr_sha)

        out.write(enc_twice)           # 0x30 bytes at 0x090
        out.write(meta_block)          # 0x40 bytes at 0x0C0
        out.write(meta_sha)            # 0x10 bytes at 0x100
        out.write(enc_once)            # 0x30 bytes at 0x110

        # 4. Encrypted data at 0x140
        all_data = bytes(first_enc) + file_data
        enc_data = _crypt(all_data, qa_digest)
        out.write(enc_data)

        # 5. 0x60 null padding
        out.write(b'\x00' * 0x60)

    return package_size


def main():
    parser = argparse.ArgumentParser(description='PS3 Custom PKG Builder')
    parser.add_argument('input_dir', nargs='?', default='custom',
                        help='Diretorio com estrutura de HDD (padrao: custom)')
    parser.add_argument('-o', '--output', help='Arquivo .pkg de saida')
    parser.add_argument('-c', '--content-id', default='CUSTOM-INSTALLER_00-0000000000000000',
                        help='Content ID (padrao: CUSTOM-INSTALLER_00-0000000000000000)')
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f'[ERRO] Diretorio nao encontrado: {args.input_dir}', file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = args.output
    else:
        out_path = args.content_id + '.pkg'

    try:
        total = build_pkg(args.input_dir, args.content_id, out_path)
        print(f'PKG criado: {out_path} ({total} bytes)')
        print(f'Content ID: {args.content_id}')
    except Exception as e:
        print(f'[ERRO] {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
