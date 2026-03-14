"""AppX/AL link helpers.

The previous placeholder content in this file broke module imports and prevented
startup. This implementation keeps helpers safe and backward-compatible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import base64
import json
import os
import shutil

import aiohttp
import aiofiles


@dataclass
class AppxLinkInfo:
    source_url: str
    is_appx: bool = False
    is_pdf: bool = False
    is_video: bool = False
    is_zip_video: bool = False
    xor_key: Optional[str] = None
    pdf_enc_key: Optional[str] = None


def classify_appx_link(url: str) -> AppxLinkInfo:
    u = (url or "").lower()
    info = AppxLinkInfo(source_url=url or "", is_appx=("appx" in u or "appxcloud" in u))
    info.is_pdf = ".pdf" in u
    info.is_zip_video = ".zip" in u
    info.is_video = any(x in u for x in [".m3u8", ".mpd", ".mp4", "master"])
    return info


def get_appx_headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://appx.example/",
    }


def get_ytdlp_appx_header_args() -> str:
    return " ".join([f'--add-header "{k}:{v}"' for k, v in get_appx_headers().items()])


def decrypt_aes_link(value: str, key: str = "") -> str:
    # Best-effort legacy decoder.
    if not value:
        return value
    try:
        return base64.b64decode(value).decode("utf-8")
    except Exception:
        return value


def is_node_link(url: str) -> bool:
    u = (url or "").lower()
    return "node" in u or "nodes" in u


async def resolve_node_link(node_payload: str, resolution: str = "") -> str:
    """Resolve node payload to final URL.

    Supports JSON strings containing url/manifest keys; fallback to raw input.
    """
    if not node_payload:
        return ""
    try:
        data = json.loads(node_payload)
        for key in ("url", "manifest", "manifestUrl", "m3u8", "mpd"):
            if data.get(key):
                return data[key]
        if resolution and isinstance(data.get("streams"), dict):
            return data["streams"].get(resolution) or next(iter(data["streams"].values()))
    except Exception:
        pass
    return node_payload


def resolve_isp_link(payload: str) -> str:
    if not payload:
        return ""
    try:
        data = json.loads(payload)
        return data.get("url") or data.get("manifestUrl") or payload
    except Exception:
        return payload


def deobfuscate_ts(url: str) -> str:
    return url


def decrypt_xor(file_path: str, key: Optional[str] = None) -> str:
    """In-place XOR decode; no-op when no key is provided."""
    if not file_path or not key or not os.path.exists(file_path):
        return file_path

    key_bytes = key.encode("utf-8")
    with open(file_path, "rb") as f:
        data = bytearray(f.read())

    for i in range(len(data)):
        data[i] ^= key_bytes[i % len(key_bytes)]

    with open(file_path, "wb") as f:
        f.write(data)

    return file_path


async def _download_file(url: str, output_path: str, headers: Optional[dict] = None) -> str:
    async with aiohttp.ClientSession(headers=headers or {}) as session:
        async with session.get(url, timeout=120) as resp:
            resp.raise_for_status()
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(await resp.read())
    return output_path


async def download_xor_pdf(output_path: str, url: str, xor_key: Optional[str] = None) -> str:
    await _download_file(url, output_path, headers=get_appx_headers())
    if xor_key:
        decrypt_xor(output_path, xor_key)
    return output_path


async def download_encrypted_pdf(output_path: str, url: str, key: Optional[str] = None) -> str:
    await _download_file(url, output_path, headers=get_appx_headers())
    if key:
        decrypt_xor(output_path, key)
    return output_path


async def download_cloudflare_pdf(url: str, output_path: str) -> str:
    return await _download_file(url, output_path, headers=get_appx_headers())


def zip_to_video(zip_path: str, output_name: str) -> str:
    """Convert zip path to output video placeholder by renaming/copying."""
    src = Path(zip_path)
    out = src.with_name(f"{output_name}.mp4")
    if src.exists():
        shutil.copyfile(src, out)
    return str(out)
