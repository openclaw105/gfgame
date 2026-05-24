# -*- coding: utf-8 -*-
"""从 2.mp3 截取 30s 生成 bgm_13，替换商场与迪士尼 BGM（共用一曲）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from extract_cover_bgm import (
    BGM_MANIFEST,
    CURSOR_MANIFEST,
    LOOP_CROSSFADE,
    apply_seamless_loop,
    encode_mp3,
    normalize_wav_rms,
    probe_duration,
    run_ffmpeg,
    wav_info,
    wav_rms,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = Path(r"c:\Users\shaos\Downloads\2.mp3")
OUT_WAV = ROOT / "bgm" / "bgm_13_mall_dream.wav"
OUT_MP3 = ROOT / "bgm" / "bgm_13_mall_dream.mp3"
NEW_FILE = "bgm/bgm_13_mall_dream.mp3"
REPLACE_IDS = ("bgm_mall_toyshop", "bgm_dream_park")
CLIP_SEC = 30.0
CLIP_START = 0.0
MAX_BYTES = 800_000
MP3_BITRATE = "96k"
EXTRACT_AF = "highpass=f=40,lowpass=f=12000"
REF_CANDIDATES = [
    ROOT / "bgm" / "bgm_10_title_ending.mp3",
    ROOT / "bgm" / "bgm_11_gallery_studio.mp3",
    ROOT / "bgm" / "bgm_12_studio.mp3",
]
MALL_DREAM_BG_KEYS = frozenset(
    {
        "bg_商场1",
        "bg_商场2",
        "bg_玩具店",
        "bg_迪士尼",
        "bg_樱花公园1",
        "bg_樱花公园2",
    }
)


def resolve_ref_rms() -> float:
    for ref in REF_CANDIDATES:
        if not ref.is_file():
            continue
        if ref.suffix.lower() == ".wav":
            return wav_rms(ref)
        tmp = ROOT / "bgm" / "_ref_rms_probe.wav"
        try:
            run_ffmpeg(
                ["-y", "-i", str(ref), "-vn", "-ac", "1", "-ar", "22050", "-t", "20", str(tmp)]
            )
            return wav_rms(tmp)
        finally:
            tmp.unlink(missing_ok=True)
    return 3100.0


def extract_clip(src: Path, out_wav: Path) -> float:
    total = probe_duration(src)
    clip_len = min(CLIP_SEC, max(5.0, total - 0.5))
    if total < 5:
        raise SystemExit(f"源文件过短（{total:.1f}s）")
    print(f"Source: {src} ({total:.1f}s) -> clip {CLIP_START:.1f}s + {clip_len:.1f}s")
    args = [
        "-y",
        "-ss",
        f"{CLIP_START:.3f}",
        "-t",
        f"{clip_len:.3f}",
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


def entry_for(bgm_id: str, src_name: str, duration: float, nbytes: int, bitrate: str) -> dict:
    if bgm_id == "bgm_mall_toyshop":
        env = "商场/玩具店"
        reason = "明亮轻快，适合商场、玩具店、中奖和喜剧情绪。"
    else:
        env = "迪士尼/樱花公园"
        reason = "童话、梦幻、轻盈，适合迪士尼、樱花公园与和解气氛。"
    return {
        "id": bgm_id,
        "file": NEW_FILE,
        "environment": env,
        "source_track": src_name,
        "source_pack": "用户提供的音乐导出",
        "author": "项目素材",
        "scene_reason": reason,
        "format": "mp3",
        "sample_rate": 22050,
        "channels": 1,
        "duration_seconds": round(duration, 2),
        "bytes": nbytes,
        "bitrate_kbps": int(bitrate.replace("k", "")),
        "size_limit_bytes": MAX_BYTES,
        "loop": True,
        "version": "v13_mp3_mall_dream",
        "loop_crossfade_seconds": LOOP_CROSSFADE,
        "clip_start_seconds": CLIP_START,
        "clip_duration_seconds": round(duration, 2),
        "license_note": f"30s clip from {src_name}, shared by mall & dream park scenes.",
    }


def sync_manifests(src_name: str, duration: float, nbytes: int, bitrate: str) -> None:
    entries = {bid: entry_for(bid, src_name, duration, nbytes, bitrate) for bid in REPLACE_IDS}
    bgm_list = json.loads(BGM_MANIFEST.read_text(encoding="utf-8"))
    bgm_list = [b if b.get("id") not in REPLACE_IDS else entries[b["id"]] for b in bgm_list]
    BGM_MANIFEST.write_text(json.dumps(bgm_list, ensure_ascii=False, indent=2), encoding="utf-8")

    data = json.loads(CURSOR_MANIFEST.read_text(encoding="utf-8"))
    manifest = [
        b if b.get("id") not in REPLACE_IDS else entries[b["id"]] for b in data.get("bgm_manifest", [])
    ]
    data["bgm_manifest"] = manifest

    for item in data.get("cursor_index", []):
        if item.get("asset_key") not in MALL_DREAM_BG_KEYS:
            continue
        bid = item.get("recommended_bgm_key")
        if bid in REPLACE_IDS:
            item["recommended_bgm_file"] = NEW_FILE
        if "tags" in item and isinstance(item["tags"], list):
            item["tags"] = [
                t if t not in REPLACE_IDS else t for t in item["tags"]
            ]

    for item in data.get("planning_from_md", {}).get("background_mapping", []):
        if item.get("asset_key") in MALL_DREAM_BG_KEYS and item.get("recommended_bgm_key") in REPLACE_IDS:
            item["recommended_bgm_file"] = NEW_FILE

    CURSOR_MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def bump_registry_cache_bust() -> None:
    reg = ROOT / "js" / "registry.js"
    text = reg.read_text(encoding="utf-8")
    for old, new in (("20260530d", "20260530e"), ("20260530c", "20260530e")):
        if old in text:
            reg.write_text(text.replace(old, new, 1), encoding="utf-8")
            print(f"Bumped ASSET_CACHE_BUST -> {new}")
            return


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.is_file():
        raise SystemExit(f"找不到源文件: {src}")

    OUT_MP3.parent.mkdir(parents=True, exist_ok=True)
    duration = extract_clip(src, OUT_WAV)

    bitrate = MP3_BITRATE
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
        raise SystemExit(f"MP3 仍超过 {MAX_BYTES} 字节")

    sync_manifests(src.name, duration, nbytes, bitrate)
    bump_registry_cache_bust()
    print(f"Updated {REPLACE_IDS} -> {NEW_FILE}")
    print("场景仍用原 id（bgm_mall_toyshop / bgm_dream_park），请 Ctrl+F5 强刷")


if __name__ == "__main__":
    main()
