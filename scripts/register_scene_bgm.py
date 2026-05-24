# -*- coding: utf-8 -*-
"""注册 bgm/1.mp3–8.mp3；manifest 仅保留封面/CG 原曲 + 场景曲。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BGM_DIR = ROOT / "bgm"
BGM_MANIFEST = BGM_DIR / "bgm_manifest.json"
CURSOR_MANIFEST = ROOT / "cursor_asset_manifest.json"

SCENE_TRACKS = [
    ("bgm_scene_1", "1.mp3", "场景配乐①", "第1章及机场/街景过渡"),
    ("bgm_scene_2", "2.mp3", "场景配乐②", "第6章演唱会/第9章樱花公园等"),
    ("bgm_scene_3", "3.mp3", "场景配乐③", "第3/10章：布场、发布会、终章"),
    ("bgm_scene_4", "4.mp3", "场景配乐④", "第7章画室夜路专曲"),
    ("bgm_scene_5", "5.mp3", "场景配乐⑤", "第4/5/8章：会所、片场"),
    ("bgm_scene_6", "6.mp3", "场景配乐⑥", "商场/玩具店专曲"),
    ("bgm_scene_7", "7.mp3", "场景配乐⑦", "迪士尼专曲"),
    ("bgm_scene_8", "8.mp3", "场景配乐⑧", "啤酒节专曲"),
]

KEEP_IDS = frozenset({"bgm_gallery_studio", "bgm_studio", "bgm_title_ending"})

# 旧场景 BGM id → 新五曲（仅用于清理 manifest 元数据引用）
LEGACY_BGM_REMAP = {
    "bgm_nightroad": "bgm_scene_4",
    "bgm_mall_toyshop": "bgm_scene_2",
    "bgm_office_event": "bgm_scene_3",
    "bgm_club_mansion_suite": "bgm_scene_5",
    "bgm_film_set": "bgm_scene_5",
    "bgm_festival_concert": "bgm_scene_2",
    "bgm_airport_subway": "bgm_scene_1",
    "bgm_dream_park": "bgm_scene_2",
}

GALLERY_BG_KEYS = frozenset({"bg_欧洲画展", "bg_画作", "bg_画展外", "bg_欧洲街景"})
STUDIO_BG_KEYS = frozenset({"bg_画室白天", "bg_画室晚上"})

BG_BY_SCENE = [
    (frozenset({"bg_商场1", "bg_商场2", "bg_玩具店"}), "bgm_scene_6"),
    (frozenset({"bg_迪士尼"}), "bgm_scene_7"),
    (frozenset({"bg_啤酒节"}), "bgm_scene_8"),
    (frozenset({"bg_演唱会1", "bg_樱花公园1", "bg_樱花公园2"}), "bgm_scene_2"),
    (frozenset({"bg_办公室", "bg_布场1", "bg_布场2", "bg_布场3", "bg_发布会1"}), "bgm_scene_3"),
    (frozenset({"bg_夜路1", "bg_夜路2", "bg_夜路3", "bg_地铁"}), "bgm_scene_4"),
    (frozenset({"bg_会所1", "bg_会所2", "bg_豪宅", "bg_花园夜间", "bg_火锅包间", "bg_总统套房", "bg_片场1", "bg_片场2", "bg_片场3", "bg_片场4", "bg_车内"}), "bgm_scene_5"),
]


def probe_duration(path: Path) -> float | None:
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        return float(data["format"]["duration"])
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None


def build_entry(bgm_id: str, filename: str, environment: str, scene_reason: str) -> dict:
    path = BGM_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    duration = probe_duration(path)
    entry = {
        "id": bgm_id,
        "file": f"bgm/{filename}",
        "environment": environment,
        "source_track": filename,
        "source_pack": "用户新增场景 BGM",
        "author": "项目素材",
        "scene_reason": scene_reason,
        "format": "mp3",
        "bytes": path.stat().st_size,
        "loop": True,
        "version": "v15_user_scene_mp3",
        "loop_crossfade_seconds": 0.6,
        "license_note": f"User-provided {filename} for in-game scene loops.",
    }
    if duration is not None:
        entry["duration_seconds"] = round(duration, 2)
    return entry


def preserved_entries(existing: list[dict]) -> list[dict]:
    by_id = {b["id"]: b for b in existing if b.get("id") in KEEP_IDS}
    order = ["bgm_gallery_studio", "bgm_studio", "bgm_title_ending"]
    return [by_id[i] for i in order if i in by_id]


def scene_key_for_background(asset_key: str) -> str:
    if asset_key in GALLERY_BG_KEYS:
        return "bgm_gallery_studio"
    if asset_key in STUDIO_BG_KEYS:
        return "bgm_studio"
    for keys, bgm_id in BG_BY_SCENE:
        if asset_key in keys:
            return bgm_id
    if asset_key == "bg_机场":
        return "bgm_scene_1"
    if asset_key == "bg_后台走廊":
        return "bgm_scene_3"
    return "bgm_scene_1"


def patch_item_bgm_refs(item: dict, file_by_id: dict[str, str]) -> None:
    ak = item.get("asset_key") or ""
    if ak.startswith("bg_"):
        key = scene_key_for_background(ak)
    else:
        key = item.get("recommended_bgm_key")
        if key in LEGACY_BGM_REMAP:
            key = LEGACY_BGM_REMAP[key]
    if not key or key not in file_by_id:
        return
    item["recommended_bgm_key"] = key
    item["recommended_bgm_file"] = file_by_id[key]
    tags = item.get("tags")
    if isinstance(tags, list):
        kept = [t for t in tags if not (isinstance(t, str) and t.startswith("bgm_"))]
        item["tags"] = list(dict.fromkeys([*kept, key]))


def patch_cursor_manifest(data: dict, file_by_id: dict[str, str]) -> None:
    for item in data.get("assets_by_category", {}).get("backgrounds", []):
        patch_item_bgm_refs(item, file_by_id)
    for item in data.get("cursor_index", []):
        if item.get("type") == "background" or str(item.get("asset_key", "")).startswith("bg_"):
            patch_item_bgm_refs(item, file_by_id)
    for item in data.get("planning_from_md", {}).get("background_mapping", []):
        ak = item.get("asset_key")
        if ak:
            sk = scene_key_for_background(ak)
            if ak in GALLERY_BG_KEYS:
                sk = "bgm_gallery_studio"
            elif ak in STUDIO_BG_KEYS:
                sk = "bgm_studio"
            item["recommended_bgm_key"] = sk
            if sk in file_by_id:
                item["recommended_bgm_file"] = file_by_id[sk]
    notes = data.get("usage_notes") or []
    data["usage_notes"] = [
        n
        for n in notes
        if "nine top-level bgm" not in str(n).lower() and "wav" not in str(n).lower()
    ]
    data["usage_notes"].append(
        "场景 BGM 使用 bgm/1.mp3–8.mp3（bgm_scene_1–8）；封面/结局 CG 保留 bgm_title_ending、画展与画室原曲。"
    )


def sync_cursor(bgm_list: list[dict]) -> None:
    data = json.loads(CURSOR_MANIFEST.read_text(encoding="utf-8"))
    file_by_id = {b["id"]: b["file"] for b in bgm_list}
    data["bgm_manifest"] = bgm_list
    data.setdefault("summary", {})["active_bgm_count"] = len(bgm_list)
    patch_cursor_manifest(data, file_by_id)
    CURSOR_MANIFEST.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    existing = json.loads(BGM_MANIFEST.read_text(encoding="utf-8"))
    preserved = preserved_entries(existing)
    new_scene = [
        build_entry(bid, fn, env, reason) for bid, fn, env, reason in SCENE_TRACKS
    ]
    final = preserved + new_scene
    BGM_MANIFEST.write_text(
        json.dumps(final, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sync_cursor(final)
    print(f"BGM manifest: {len(final)} tracks (3 CG/cover + {len(new_scene)} scene)")
    print(f"Removed legacy scene BGM ids: {', '.join(LEGACY_BGM_REMAP)}")


if __name__ == "__main__":
    main()
