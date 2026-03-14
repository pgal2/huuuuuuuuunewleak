"""Helpers for CW links and N_m3u8DL-RE based downloads.

This module is intentionally lightweight so the bot can boot even when
optional CW tooling is not present.
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import parse_qs, urlparse, unquote


def get_download_info(url: str) -> tuple[str, str]:
    """Extract clean URL and DRM keys from CW links.

    Expected format examples:
    - https://.../master.mpd#keysV1=keyid:key
    - https://.../master.mpd?x=1#keysV1=keyid:key
    """
    if not url:
        return "", ""

    marker = "#keysV1="
    if marker not in url:
        return url, ""

    clean_url, key_part = url.split(marker, 1)
    keys = unquote(key_part).strip()
    return clean_url.strip(), keys


async def download_video_with_nre(mpd_url: str, keys_string: str, name: str) -> str | None:
    """Download DRM video using N_m3u8DL-RE if available.

    Returns downloaded file path when successful, otherwise None.
    """
    if not mpd_url or not name:
        return None

    output_path = os.path.abspath(f"{name}.mp4")

    cmd = [
        "N_m3u8DL-RE",
        mpd_url,
        "--save-name",
        name,
        "--save-dir",
        os.getcwd(),
        "--auto-select",
        "--binary-merge",
        "--del-after-done",
    ]

    if keys_string:
        # Accept either: "--key kid:key" style or comma-separated keys.
        cleaned = keys_string.replace("--key", "").strip()
        for piece in [k.strip() for k in cleaned.split(",") if k.strip()]:
            cmd.extend(["--key", piece])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _ = await process.communicate()
    except FileNotFoundError:
        return None

    if process.returncode != 0:
        return None

    if os.path.exists(output_path):
        return output_path

    # Some builds may output mkv/ts; find best candidate.
    for ext in ("mkv", "ts", "mp4"):
        candidate = os.path.abspath(f"{name}.{ext}")
        if os.path.exists(candidate):
            return candidate

    return None
