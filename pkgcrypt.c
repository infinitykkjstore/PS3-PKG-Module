#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#define PY_SSIZE_T_CLEAN
#include <Python.h>

/* --- embedded SHA-1 (RFC 3174) --- */
typedef struct {
    uint32_t state[5];
    uint64_t count;
    unsigned char buffer[64];
} sha1_ctx;

static void sha1_transform(uint32_t state[5], const unsigned char block[64]) {
    #define ROTL32(x, n) (((x) << (n)) | ((x) >> (32 - (n))))
    #define SHA1_F(i, b, c, d) \
        (((i) < 20) ? (((b) & (c)) | ((~(b)) & (d))) : \
         ((i) < 40) ? ((b) ^ (c) ^ (d)) : \
         ((i) < 60) ? (((b) & (c)) | ((b) & (d)) | ((c) & (d))) : \
                     ((b) ^ (c) ^ (d)))
    #define SHA1_K(i) ((uint32_t)(((i) < 20) ? 0x5A827999 : \
                                   ((i) < 40) ? 0x6ED9EBA1 : \
                                   ((i) < 60) ? 0x8F1BBCDC : 0xCA62C1D6))

    uint32_t w[80], a, b, c, d, e, temp;
    int i;
    for (i = 0; i < 16; i++)
        w[i] = ((uint32_t)block[i*4] << 24) | ((uint32_t)block[i*4+1] << 16) |
               ((uint32_t)block[i*4+2] << 8)  | block[i*4+3];
    for (i = 16; i < 80; i++)
        w[i] = ROTL32(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
    a = state[0]; b = state[1]; c = state[2]; d = state[3]; e = state[4];
    for (i = 0; i < 80; i++) {
        temp = ROTL32(a, 5) + SHA1_F(i, b, c, d) + e + w[i] + SHA1_K(i);
        e = d; d = c; c = ROTL32(b, 30); b = a; a = temp;
    }
    state[0] += a; state[1] += b; state[2] += c; state[3] += d; state[4] += e;
    #undef ROTL32
    #undef SHA1_F
    #undef SHA1_K
}

static void sha1_init(sha1_ctx *ctx) {
    ctx->state[0] = 0x67452301;
    ctx->state[1] = 0xEFCDAB89;
    ctx->state[2] = 0x98BADCFE;
    ctx->state[3] = 0x10325476;
    ctx->state[4] = 0xC3D2E1F0;
    ctx->count = 0;
}

static void sha1_update(sha1_ctx *ctx, const unsigned char *data, size_t len) {
    size_t idx = (size_t)(ctx->count & 63);
    ctx->count += len;
    if (idx) {
        size_t fill = 64 - idx;
        if (len < fill) { memcpy(ctx->buffer + idx, data, len); return; }
        memcpy(ctx->buffer + idx, data, fill);
        sha1_transform(ctx->state, ctx->buffer);
        data += fill; len -= fill;
    }
    while (len >= 64) {
        sha1_transform(ctx->state, data);
        data += 64; len -= 64;
    }
    if (len) memcpy(ctx->buffer, data, len);
}

static void sha1_final(sha1_ctx *ctx, unsigned char digest[20]) {
    size_t idx = (size_t)(ctx->count & 63);
    ctx->buffer[idx++] = 0x80;
    if (idx > 56) { memset(ctx->buffer + idx, 0, 64 - idx); sha1_transform(ctx->state, ctx->buffer); idx = 0; }
    memset(ctx->buffer + idx, 0, 56 - idx);
    uint64_t bits = ctx->count << 3;
    for (int i = 0; i < 8; i++) ctx->buffer[56 + 7 - i] = (unsigned char)(bits >> (i * 8));
    sha1_transform(ctx->state, ctx->buffer);
    for (int i = 0; i < 5; i++)
        { digest[i*4]   = (ctx->state[i] >> 24) & 0xff;
          digest[i*4+1] = (ctx->state[i] >> 16) & 0xff;
          digest[i*4+2] = (ctx->state[i] >> 8) & 0xff;
          digest[i*4+3] = ctx->state[i] & 0xff; }
}

static void sha1_hash(const unsigned char *data, size_t len, unsigned char out[20]) {
    sha1_ctx ctx;
    sha1_init(&ctx);
    sha1_update(&ctx, data, len);
    sha1_final(&ctx, out);
}
/* --- end SHA-1 --- */

static void inc_counter(uint8_t *key) {
    uint64_t ctr = ((uint64_t)key[0x38] << 56) | ((uint64_t)key[0x39] << 48) |
                   ((uint64_t)key[0x3a] << 40) | ((uint64_t)key[0x3b] << 32) |
                   ((uint64_t)key[0x3c] << 24) | ((uint64_t)key[0x3d] << 16) |
                   ((uint64_t)key[0x3e] <<  8) | (uint64_t)key[0x3f];
    ctr++;
    key[0x38] = (ctr >> 56) & 0xff;
    key[0x39] = (ctr >> 48) & 0xff;
    key[0x3a] = (ctr >> 40) & 0xff;
    key[0x3b] = (ctr >> 32) & 0xff;
    key[0x3c] = (ctr >> 24) & 0xff;
    key[0x3d] = (ctr >> 16) & 0xff;
    key[0x3e] = (ctr >>  8) & 0xff;
    key[0x3f] = (ctr >>  0) & 0xff;
}

static PyObject* pkg_crypt(PyObject *self, PyObject *args) {
    const uint8_t *key, *input;
    Py_ssize_t key_length, input_length;
    int length, remaining, offset = 0;

    if (!PyArg_ParseTuple(args, "y#y#i", &key, &key_length, &input, &input_length, &length))
        return NULL;

    uint8_t *key_copy = (uint8_t*)malloc(64);
    memcpy(key_copy, key, 64);

    unsigned char *ret = (unsigned char*)malloc(length);
    remaining = length;

    while (remaining > 0) {
        int bytes_to_dump = remaining;
        if (bytes_to_dump > 0x10)
            bytes_to_dump = 0x10;

        unsigned char hash[20];
        sha1_hash(key_copy, 64, hash);

        int j;
        for (j = 0; j < bytes_to_dump; j++)
            ret[offset + j] = input[offset + j] ^ hash[j];

        offset += bytes_to_dump;
        remaining -= bytes_to_dump;
        inc_counter(key_copy);
    }

    free(key_copy);
    PyObject *py_ret = Py_BuildValue("y#", ret, length);
    free(ret);
    return py_ret;
}

static PyObject* key_crypt(PyObject *self, PyObject *args) {
    const uint8_t *key;
    Py_ssize_t key_length;
    int i;

    if (!PyArg_ParseTuple(args, "y#", &key, &key_length))
        return NULL;

    uint8_t *copy = (uint8_t*)malloc(64);
    memcpy(copy, key, 64);
    for (i = 0; i < 0x10000; i++)
        inc_counter(copy);
    free(copy);

    Py_RETURN_NONE;
}

static PyObject* register_sha1_callback(PyObject *self, PyObject *args) {
    Py_RETURN_NONE;
}

static PyMethodDef cryptMethods[] = {
    {"pkgcrypt", pkg_crypt, METH_VARARGS, "Fast PKG decryption (SHA1 + XOR)"},
    {"keycrypt", key_crypt, METH_VARARGS, "Advance counter on key"},
    {"register_sha1_callback", register_sha1_callback, METH_VARARGS, "No-op (kept for compatibility)"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef pkgcryptmodule = {
    PyModuleDef_HEAD_INIT,
    "pkgcrypt",
    NULL,
    -1,
    cryptMethods
};

PyMODINIT_FUNC PyInit_pkgcrypt(void) {
    return PyModule_Create(&pkgcryptmodule);
}
