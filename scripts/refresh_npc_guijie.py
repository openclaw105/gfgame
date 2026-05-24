# -*- coding: utf-8 -*-
"""刷新路人角色/柜姐1、柜姐2 的 manifest 元数据并重建离线包。"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("需要 Pillow: pip install pillow")

ROOT = Path(__file__).resolve().parents[1]
NPC_DIR = ROOT / "路人角色"
MANIFEST = ROOT / "cursor_asset_manifest.json"
GUIJIE_FILES = ("柜姐1.png", "柜姐2.png")
GUIJIE_KEYS = ("npc_柜姐1", "npc_柜姐2")


def file_meta(path: Path) -> dict:
    with Image.open(path) as im:
        w, h = im.size
        mode = im.mode
    return {
        "bytes": path.stat().st_size,
        "width": w,
        "height": h,
        "mode": mode,
    }


def patch_item(item: dict, png: Path, key: str) -> None:
    rel = f"路人角色/{png.name}".replace("\\", "/")
    meta = file_meta(png)
    item.update(
        asset_key=key,
        type="npc_character",
        category="路人角色",
        character=png.stem,
        emotion="default",
        name=png.stem,
        rel_path=rel,
        abs_path=str(png.resolve()),
        web_path=rel,
        active=True,
        **meta,
    )


def main() -> None:
    paths = {name: NPC_DIR / name for name in GUIJIE_FILES}
    for name, path in paths.items():
        if not path.is_file():
            raise SystemExit(f"缺少素材: {path}")

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    updated = 0
    key_to_png = {GUIJIE_KEYS[i]: paths[GUIJIE_FILES[i]] for i in range(2)}

    for item in data.get("cursor_index", []):
        key = item.get("asset_key")
        if key in key_to_png:
            patch_item(item, key_to_png[key], key)
            updated += 1
            print(f"  {key}: {item['width']}x{item['height']} ({item['bytes'] // 1024} KB)")

    def touch(item: dict) -> None:
        key = item.get("asset_key")
        if key in key_to_png:
            patch_item(item, key_to_png[key], key)

    for item in data.get("assets_by_category", {}).get("npc_character", []):
        touch(item)
    for block in data.get("assets_by_category", {}).values():
        if not isinstance(block, list):
            continue
        for item in block:
            if isinstance(item, dict):
                touch(item)

    for name, png in paths.items():
        stem = png.stem
        grouped = data.get("characters_grouped", {}).get(stem, [])
        for item in grouped:
            if item.get("asset_key") in key_to_png:
                patch_item(item, png, item["asset_key"])

    data["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: 更新 {updated} 条柜姐条目")

    bundle = ROOT / "scripts" / "bundle_offline_data.py"
    subprocess.run([sys.executable, str(bundle)], cwd=str(ROOT), check=True)


if __name__ == "__main__":
    main()
