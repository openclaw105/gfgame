# -*- coding: utf-8 -*-
"""从项目视频提取封面/结局 BGM，输出压缩版 MP3（体积约为 WAV 的 1/4）。"""
from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
SRC_CANDIDATES = [ROOT / "音频1.mp4", ROOT / "测试.mp4"]
OUT_WAV = ROOT / "bgm" / "bgm_10_title_ending.wav"
OUT_MP3 = ROOT / "bgm" / "bgm_10_title_ending.mp3"
BGM_MANIFEST = ROOT / "bgm" / "bgm_manifest.json"
CURSOR_MANIFEST = ROOT / "cursor_asset_manifest.json"
BGM_ID = "bgm_title_ending"
# 首尾交叉淡化时长（秒），使 HTML5 loop 衔接顺滑
LOOP_CROSSFADE = 0.6
# 仅去直流/爆音，不做长淡入淡出（长 fade 会破坏循环）
EXTRACT_AF = "highpass=f=40,lowpass=f=9000"
TARGET_RMS = 3100
REF_BGM = ROOT / "bgm" / "bgm_11_gallery_studio.mp3"
if not REF_BGM.is_file():
    REF_BGM = ROOT / "bgm" / "bgm_01_gallery_studio.wav"
# 单声道 80kbps ≈ 30s 约 300KB，听感仍可接受
MP3_BITRATE = "80k"
MAX_BYTES = 1_000_000


def resolve_src() -> Path | None:
    for p in SRC_CANDIDATES:
        if p.is_file():
            return p
    return None


def _run_capture(ff: str, args: list[str]) -> str:
    proc = subprocess.run([ff, *args], capture_output=True)
    text = (proc.stdout or b"") + (proc.stderr or b"")
    return text.decode("utf-8", errors="replace")


def run_ffmpeg(args: list[str]) -> None:
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run([ff, *args], capture_output=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace")
        raise RuntimeError(err or "ffmpeg failed")


def probe_duration(path: Path) -> float:
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    text = _run_capture(ff, ["-hide_banner", "-i", str(path)])
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not m:
        raise RuntimeError(f"无法读取时长：{path}")
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def wav_rms(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        sw = w.getsampwidth()
        ch = w.getnchannels()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError("仅支持 16-bit PCM")
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    if ch > 1:
        samples = samples[::ch]
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def read_wav_mono(path: Path) -> tuple[list[int], wave._wave_params]:
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        ch = w.getnchannels()
        raw = w.readframes(w.getnframes())
    samples = list(struct.unpack(f"<{len(raw) // 2}h", raw))
    if ch > 1:
        samples = samples[::ch]
    return samples, params


def write_wav_mono(path: Path, samples: list[int], params: wave._wave_params) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(params.sampwidth)
        out.setframerate(params.framerate)
        out.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def apply_seamless_loop(path: Path, crossfade_sec: float = LOOP_CROSSFADE) -> int:
    """将尾部与头部交叉混合，便于 loop 时首尾振幅连续。"""
    samples, params = read_wav_mono(path)
    rate = params.framerate
    n = min(int(rate * crossfade_sec), len(samples) // 4)
    if n < 64:
        return 0
    out = samples[:]
    for j in range(n):
        w = (j + 1) / n
        tail_i = len(samples) - n + j
        out[tail_i] = int(round((1 - w) * samples[tail_i] + w * samples[j]))
    for j in range(n):
        w = (j + 1) / n
        out[j] = int(round((1 - w) * samples[j] + w * samples[len(samples) - n + j]))
    write_wav_mono(path, out, params)
    return n


def normalize_wav_rms(path: Path, target: float) -> float:
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    samples = list(struct.unpack(f"<{len(frames) // 2}h", frames))
    cur = wav_rms(path)
    if cur < 1:
        return 1.0
    gain = target / cur
    peak = max(abs(s) for s in samples) or 1
    if peak * gain > 32000:
        gain = 32000 / peak
    scaled = [int(max(-32768, min(32767, round(s * gain)))) for s in samples]
    with wave.open(str(path), "wb") as out:
        out.setparams(params)
        out.writeframes(struct.pack(f"<{len(scaled)}h", *scaled))
    return gain


def wav_info(path: Path) -> tuple[float, int]:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate(), path.stat().st_size


def resolve_target_rms() -> float:
    if REF_BGM.is_file():
        return wav_rms(REF_BGM)
    return float(TARGET_RMS)


def encode_mp3(wav_path: Path, mp3_path: Path, bitrate: str = MP3_BITRATE) -> None:
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(wav_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "22050",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            "-write_xing",
            "0",
            str(mp3_path),
        ]
    )


def sync_cursor_manifest(entry: dict) -> None:
    data = json.loads(CURSOR_MANIFEST.read_text(encoding="utf-8"))
    manifest = [b for b in data.setdefault("bgm_manifest", []) if b.get("id") != BGM_ID]
    manifest.append(entry)
    data["bgm_manifest"] = manifest
    data.setdefault("summary", {})["active_bgm_count"] = len(manifest)
    CURSOR_MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_manifest_entry(src_name: str, duration: float, nbytes: int) -> dict:
    return {
        "id": BGM_ID,
        "file": "bgm/bgm_10_title_ending.mp3",
        "environment": "封面/结局",
        "source_track": src_name,
        "source_pack": "项目自带视频提取",
        "author": "项目素材",
        "scene_reason": "封面与结局画面循环背景音乐。",
        "format": "mp3",
        "sample_rate": 22050,
        "channels": 1,
        "duration_seconds": round(duration, 2),
        "bytes": nbytes,
        "bitrate_kbps": int(MP3_BITRATE.replace("k", "")),
        "size_limit_bytes": MAX_BYTES,
        "loop": True,
        "version": "v4_seamless_loop",
        "loop_crossfade_seconds": LOOP_CROSSFADE,
        "license_note": f"Extracted from {src_name}, MP3 mono for smaller download.",
    }


def extract_wav_from_video(src: Path, out_wav: Path) -> float:
    duration = probe_duration(src)
    print(f"Source: {src.name} ({duration:.2f}s), loop crossfade {LOOP_CROSSFADE}s")
    args = [
        "-y",
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
    print(f"Loop seam crossfade: {n} samples ({n / 22050:.2f}s)")
    target_rms = resolve_target_rms()
    gain = normalize_wav_rms(out_wav, target_rms)
    print(f"WAV normalized RMS {wav_rms(out_wav):.0f} (target {target_rms:.0f}, gain x{gain:.3f})")
    return wav_info(out_wav)[0]


def compress_wav_to_mp3(wav_path: Path, mp3_path: Path) -> tuple[float, int]:
    duration = probe_duration(wav_path)
    bitrate = MP3_BITRATE
    encode_mp3(wav_path, mp3_path, bitrate)
    nbytes = mp3_path.stat().st_size
    if nbytes > MAX_BYTES and bitrate == "80k":
        print(f"MP3 {nbytes} bytes > {MAX_BYTES}, retry 64k…")
        encode_mp3(wav_path, mp3_path, "64k")
        nbytes = mp3_path.stat().st_size
        bitrate = "64k"
    print(f"MP3 {mp3_path.name}: {nbytes} bytes ({nbytes / 1024:.1f} KB), {bitrate}")
    return duration, nbytes


def main() -> None:
    OUT_MP3.parent.mkdir(parents=True, exist_ok=True)
    src = resolve_src()
    src_name = src.name if src else "bgm_10_title_ending.wav"

    if src:
        duration = extract_wav_from_video(src, OUT_WAV)
    elif OUT_WAV.is_file():
        print(f"No video source; reprocess existing {OUT_WAV.name}")
        apply_seamless_loop(OUT_WAV, LOOP_CROSSFADE)
        duration, _ = wav_info(OUT_WAV)
        target_rms = resolve_target_rms()
        normalize_wav_rms(OUT_WAV, target_rms)
    else:
        raise SystemExit("找不到 音频1.mp4 / 测试.mp4，且无 bgm_10_title_ending.wav 可压缩")

    duration, nbytes = compress_wav_to_mp3(OUT_WAV, OUT_MP3)

    if OUT_WAV.is_file():
        OUT_WAV.unlink()
        print(f"Removed intermediate {OUT_WAV.name}")

    entry = build_manifest_entry(src_name, duration, nbytes)
    bgm_list = [b for b in json.loads(BGM_MANIFEST.read_text(encoding="utf-8")) if b.get("id") != BGM_ID]
    bgm_list.append(entry)
    BGM_MANIFEST.write_text(json.dumps(bgm_list, ensure_ascii=False, indent=2), encoding="utf-8")
    sync_cursor_manifest(entry)

    print(f"Wrote {OUT_MP3} ({duration:.2f}s)")
    print(f"Updated {BGM_MANIFEST} and {CURSOR_MANIFEST}")


if __name__ == "__main__":
    main()
