# -*- coding: utf-8 -*-
"""从外部 MP3 截取 30s 生成画展 BGM（bgm_11），替换 bgm_gallery_studio。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from extract_cover_bgm import (
    BGM_MANIFEST,
    CURSOR_MANIFEST,
    LOOP_CROSSFADE,
    apply_seamless_loop,
    compress_wav_to_mp3,
    normalize_wav_rms,
    probe_duration,
    run_ffmpeg,
    wav_info,
    wav_rms,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = Path(r"c:\Users\shaos\Downloads\M500004g1mT04UVJnS.mp3")
OUT_WAV = ROOT / "bgm" / "bgm_11_gallery_studio.wav"
OUT_MP3 = ROOT / "bgm" / "bgm_11_gallery_studio.mp3"
BGM_ID = "bgm_gallery_studio"
CLIP_SEC = 30.0
CLIP_START = 0.0
MAX_BYTES = 800_000
MP3_BITRATE = "96k"
EXTRACT_AF = "highpass=f=40,lowpass=f=12000"
# 音量对齐：优先与封面 BGM10 一致，否则旧画展 WAV
REF_CANDIDATES = [
    ROOT / "bgm" / "bgm_10_title_ending.mp3",
    ROOT / "bgm" / "bgm_01_gallery_studio.wav",
    ROOT / "bgm" / "bgm_02_rain_nightroad.wav",
]
OLD_FILE = "bgm/bgm_01_gallery_studio.wav"
NEW_FILE = "bgm/bgm_11_gallery_studio.mp3"


def resolve_ref_rms() -> float:
    for ref in REF_CANDIDATES:
        if not ref.is_file():
            continue
        if ref.suffix.lower() == ".wav":
            return wav_rms(ref)
        tmp = ROOT / "bgm" / "_ref_rms_probe.wav"
        try:
            run_ffmpeg(
                [
                    "-y",
                    "-i",
                    str(ref),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "22050",
                    "-t",
                    "20",
                    str(tmp),
                ]
            )
            return wav_rms(tmp)
        finally:
            tmp.unlink(missing_ok=True)
    return 3100.0


def extract_clip(src: Path, out_wav: Path) -> float:
    total = probe_duration(src)
    if total < CLIP_SEC + 0.5:
        raise SystemExit(f"源文件过短（{total:.1f}s），需要至少 {CLIP_SEC}s")
    print(f"Source: {src} ({total:.1f}s) -> clip {CLIP_START:.1f}s + {CLIP_SEC}s")
    args = [
        "-y",
        "-ss",
        f"{CLIP_START:.3f}",
        "-t",
        f"{CLIP_SEC:.3f}",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "22050",
    ]
    if EXTRACT_AF:
        args.extend(["-af", EXTRACT_AF])
    args.append(str(out_wav))
    run_ffmpeg(args)
    n = apply_seamless_loop(out_wav, LOOP_CROSSFADE)
    print(f"Loop crossfade: {n} samples ({n / 22050:.2f}s)")
    target = resolve_ref_rms()
    gain = normalize_wav_rms(out_wav, target)
    print(f"RMS {wav_rms(out_wav):.0f} (target {target:.0f}, gain x{gain:.3f})")
    return wav_info(out_wav)[0]


def build_manifest_entry(src_name: str, duration: float, nbytes: int, bitrate: str) -> dict:
    return {
        "id": BGM_ID,
        "file": NEW_FILE,
        "environment": "画展/画室",
        "source_track": src_name,
        "source_pack": "用户提供的 QQ 音乐导出",
        "author": "项目素材",
        "scene_reason": "柔和钢琴氛围，用于画展、画室及沿用原 bgm_gallery_studio 的场景。",
        "format": "mp3",
        "sample_rate": 22050,
        "channels": 1,
        "duration_seconds": round(duration, 2),
        "bytes": nbytes,
        "bitrate_kbps": int(bitrate.replace("k", "")),
        "size_limit_bytes": MAX_BYTES,
        "loop": True,
        "version": "v11_mp3_gallery_clip",
        "loop_crossfade_seconds": LOOP_CROSSFADE,
        "clip_start_seconds": CLIP_START,
        "clip_duration_seconds": CLIP_SEC,
        "license_note": f"30s clip from {src_name}; for personal game project.",
    }


def patch_json_strings(obj, old: str, new: str) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and old in v:
                obj[k] = v.replace(old, new)
            else:
                patch_json_strings(v, old, new)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and old in item:
                obj[i] = item.replace(old, new)
            else:
                patch_json_strings(item, old, new)


def sync_manifests(entry: dict) -> None:
    bgm_list = json.loads(BGM_MANIFEST.read_text(encoding="utf-8"))
    bgm_list = [b for b in bgm_list if b.get("id") != BGM_ID]
    bgm_list.insert(0, entry)
    BGM_MANIFEST.write_text(json.dumps(bgm_list, ensure_ascii=False, indent=2), encoding="utf-8")

    data = json.loads(CURSOR_MANIFEST.read_text(encoding="utf-8"))
    manifest = [b for b in data.setdefault("bgm_manifest", []) if b.get("id") != BGM_ID]
    manifest.insert(0, entry)
    data["bgm_manifest"] = manifest
    patch_json_strings(data, OLD_FILE, NEW_FILE)
    # 仅恢复备份目录中的旧路径，避免误改 backup_* 条目
    for item in data.get("cursor_index", {}).get("bgm_backups", []):
        if "backup_" in item.get("rel_path", ""):
            item["rel_path"] = item["rel_path"].replace(
                "bgm_11_gallery_studio.mp3", "bgm_01_gallery_studio.wav"
            )
            if "abs_path" in item:
                item["abs_path"] = item["abs_path"].replace(
                    "bgm_11_gallery_studio.mp3", "bgm_01_gallery_studio.wav"
                )
    CURSOR_MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def bump_registry_cache_bust() -> None:
    reg = ROOT / "js" / "registry.js"
    text = reg.read_text(encoding="utf-8")
    old, new = "20260530b", "20260530c"
    if old in text:
        reg.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"Bumped ASSET_CACHE_BUST: {old} -> {new}")


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.is_file():
        raise SystemExit(f"找不到源文件: {src}")

    OUT_MP3.parent.mkdir(parents=True, exist_ok=True)
    duration = extract_clip(src, OUT_WAV)

    bitrate = MP3_BITRATE
    from extract_cover_bgm import encode_mp3

    encode_mp3(OUT_WAV, OUT_MP3, bitrate)
    nbytes = OUT_MP3.stat().st_size
    if nbytes > MAX_BYTES:
        for br in ("80k", "64k"):
            print(f"MP3 {nbytes} > {MAX_BYTES}, retry {br}…")
            encode_mp3(OUT_WAV, OUT_MP3, br)
            nbytes = OUT_MP3.stat().st_size
            bitrate = br
            if nbytes <= MAX_BYTES:
                break

    OUT_WAV.unlink(missing_ok=True)
    print(f"Wrote {OUT_MP3} ({duration:.2f}s, {nbytes / 1024:.1f} KB, {bitrate})")

    if nbytes > MAX_BYTES:
        raise SystemExit(f"MP3 仍超过 {MAX_BYTES} 字节限制")

    entry = build_manifest_entry(src.name, duration, nbytes, bitrate)
    sync_manifests(entry)
    bump_registry_cache_bust()
    print(f"Updated {BGM_MANIFEST}, {CURSOR_MANIFEST}")
    print(f"场景仍使用 id「{BGM_ID}」，文件已换为 {NEW_FILE}")


if __name__ == "__main__":
    main()
