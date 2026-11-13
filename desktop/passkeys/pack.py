#!/usr/bin/env python3
"""Packs the Dex Passkeys extension as a signed .crx (CRX3) and writes the files Chrome needs to
install it by policy, without any network:

  pack.py <extension folder> <key.pem> <out folder> [folder the files will live in on the bot's computer]

Writes <out>/dex-passkeys.crx and <out>/updates.xml, and prints the extension's id. The key
(RSA, made on first use) decides the id; keep it, or the id changes and Chrome installs a new one.
"""
import hashlib, io, json, os, struct, sys, zipfile
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def varint(n):
    out = b""
    while True:
        out += bytes([(n & 0x7F) | (0x80 if n > 0x7F else 0)])
        n >>= 7
        if not n:
            return out


def field(number, data):                       # one length-delimited protobuf field
    return varint((number << 3) | 2) + varint(len(data)) + data


def load_key(path):
    if not os.path.exists(path):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return serialization.load_pem_private_key(open(path, "rb").read(), None)


def pack(folder, key_path, out, install_dir=None):
    key = load_key(key_path)
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    crx_id = hashlib.sha256(public).digest()[:16]
    ext_id = "".join(chr(ord("a") + int(c, 16)) for c in crx_id.hex())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, names in sorted(os.walk(folder)):
            for name in sorted(names):
                full = os.path.join(root, name)
                info = zipfile.ZipInfo(os.path.relpath(full, folder), (2026, 1, 1, 0, 0, 0))   # same bytes every time
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, open(full, "rb").read())
    archive = buf.getvalue()
    signed = field(1, crx_id)                                         # SignedData { crx_id }
    signature = key.sign(b"CRX3 SignedData\x00" + struct.pack("<I", len(signed)) + signed + archive,
                         padding.PKCS1v15(), hashes.SHA256())
    header = field(2, field(1, public) + field(2, signature)) + field(10000, signed)   # CrxFileHeader
    version = json.load(open(os.path.join(folder, "manifest.json")))["version"]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "dex-passkeys.crx"), "wb") as f:
        f.write(b"Cr24" + struct.pack("<II", 3, len(header)) + header + archive)
    with open(os.path.join(out, "updates.xml"), "w") as f:       # where Chrome's policy finds the .crx
        f.write("<?xml version='1.0' encoding='UTF-8'?>\n<gupdate xmlns='http://www.google.com/update2/response' protocol='2.0'>\n"
                f"  <app appid='{ext_id}'>\n    <updatecheck codebase='file://{os.path.abspath(install_dir or out)}/dex-passkeys.crx' version='{version}' />\n"
                "  </app>\n</gupdate>\n")
    return ext_id, version


if __name__ == "__main__":
    ext_id, version = pack(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    print(ext_id, version)
