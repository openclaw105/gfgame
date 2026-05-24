# -*- coding: utf-8 -*-
"""将 背景图/ 下指定 PNG 注册进 cursor_asset_manifest.json（cursor_index + backgrounds）。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "cursor_asset_manifest.json"
BG_DIR = ROOT / "背景图"

try:
    from PIL import Image
except ImportError:
    Image = None


def probe_image(path: Path) -> dict:
    out = {"bytes": path.stat().st_size}
    if not Image:
        return out
    try:
        with Image.open(path) as im:
            out["width"], out["height"] = im.size
            out["mode"] = im.mode
    except OSError:
        pass
    return out


def build_bg_entry(asset_key: str, filename: str, usage: str, story: str) -> dict:
    png = BG_DIR / filename
    if not png.is_file():
        raise FileNotFoundError(png)
    rel = f"背景图/{filename}"
    meta = probe_image(png)
    return {
        "asset_key": asset_key,
        "type": "background",
        "category": "背景图",
        "name": filename.replace(".png", ""),
        "rel_path": rel,
        "abs_path": str(png.resolve()),
        "web_path": rel,
        "active": True,
        "matched_in_md": True,
        "recommended_bgm_key": "bgm_gallery_studio",
        "recommended_bgm_file": "bgm/bgm_11_gallery_studio.mp3",
        "md_mapping": {
            "asset_key": asset_key,
            "usage": usage,
            "story": story,
            "recommended_bgm_from_md": "空灵钢琴",
        },
        "tags": [filename.replace(".png", ""), "background", "bgm_gallery_studio"],
        **meta,
    }


def upsert_list(items: list, entry: dict, key_field: str = "asset_key") -> None:
    key = entry[key_field]
    for i, x in enumerate(items):
        if x.get(key_field) == key:
            items[i] = entry
            return
    items.append(entry)


def register_background(asset_key: str, filename: str, usage: str, story: str) -> None:
    entry = build_bg_entry(asset_key, filename, usage, story)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    upsert_list(manifest.setdefault("assets_by_category", {}).setdefault("backgrounds", []), entry)
    upsert_list(manifest.setdefault("cursor_index", []), entry)
    planning = manifest.setdefault("planning_from_md", {})
    mapping = planning.setdefault("background_mapping", [])
    slim = {
        "asset_key": asset_key,
        "usage": usage,
        "story": story,
        "recommended_bgm_from_md": "空灵钢琴",
        "matched": True,
        "rel_path": entry["rel_path"],
        "abs_path": entry["abs_path"],
        "recommended_bgm_key": "bgm_gallery_studio",
    }
    upsert_list(mapping, slim, "asset_key")
    summary = manifest.setdefault("summary", {})
    summary["background_count"] = len(
        [x for x in manifest["assets_by_category"]["backgrounds"] if x.get("active", True)]
    )
    summary["active_asset_count"] = max(
        summary.get("active_asset_count", 0),
        len([x for x in manifest["cursor_index"] if x.get("active", True)]),
    )
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Registered {asset_key} -> {entry['rel_path']}")


def main():
    register_background(
        "bg_画作",
        "画作.png",
        "《街角星光》画作特写",
        "第一章初遇与第二章对比闪回",
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "bundle_offline_data.py")],
        cwd=str(ROOT),
        check=False,
    )


if __name__ == "__main__":
    main()
