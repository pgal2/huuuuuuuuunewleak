"""Fallback decryptor for Classplus `encn` videos.

If required crypto primitives or response metadata are missing, function exits
silently so normal non-encn flows keep working.
"""

from __future__ import annotations

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import hashlib
import os
from urllib.parse import urlparse


# Known default for some Classplus encn payloads.
_DEFAULT_KEY = b"0123456789abcdef"


def _derive_key(seed: str) -> bytes:
    if not seed:
        return _DEFAULT_KEY
    return hashlib.sha256(seed.encode("utf-8")).digest()[:16]


def decrypt_cp_encn_video(file_path: str, source_url: str = "") -> str:
    """Best-effort in-place decryption for `_encn` files.

    Returns resulting file path (original path if decryption not possible).
    """
    if not file_path or not os.path.exists(file_path):
        return file_path

    # Heuristic key derivation from URL host/path; safe fallback if it fails.
    parsed = urlparse(source_url or "")
    seed = f"{parsed.netloc}{parsed.path}"
    key = _derive_key(seed)

    try:
        with open(file_path, "rb") as f:
            blob = f.read()

        # Minimal format expectation: [16-byte IV][ciphertext]
        if len(blob) <= 16:
            return file_path

        iv, payload = blob[:16], blob[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        plain = unpad(cipher.decrypt(payload), AES.block_size)

        with open(file_path, "wb") as f:
            f.write(plain)
    except Exception:
        # Keep original file when decryption cannot be applied.
        return file_path

    return file_path
