# -*- coding: utf-8 -*-
"""刷新背景图与封面 manifest 元数据，并重建离线包。"""
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
BG_DIR = ROOT / "背景图"
MANIFEST = ROOT / "cursor_asset_manifest.json"
COVER_ROOT = ROOT / "封面2.png"


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


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    updated = 0
    added = 0
    paths_on_disk = {}

    for png in BG_DIR.glob("*.png"):
        rel = f"背景图/{png.name}".replace("\\", "/")
        paths_on_disk[rel] = png

    indexed_rels = {
        (item.get("rel_path") or "").replace("\\", "/")
        for item in data.get("cursor_index", [])
    }

    for rel, png in sorted(paths_on_disk.items()):
        if rel in indexed_rels:
            continue
        name = png.stem
        data.setdefault("cursor_index", []).append(
            {
                "asset_key": f"bg_{name}",
                "type": "background",
                "category": "背景图",
                "name": name,
                "rel_path": rel,
                "abs_path": str(png.resolve()),
                "web_path": rel,
                "tags": [name],
                "active": True,
                **file_meta(png),
            }
        )
        added += 1

    for item in data.get("cursor_index", []):
        rel = (item.get("rel_path") or "").replace("\\", "/")
        if rel not in paths_on_disk:
            continue
        png = paths_on_disk[rel]
        meta = file_meta(png)
        item.update(
            abs_path=str(png.resolve()),
            web_path=rel,
            **meta,
            active=True,
        )
        updated += 1

    if COVER_ROOT.is_file():
        meta = file_meta(COVER_ROOT)
        rel = "封面2.png"
        cover = {
            "asset_key": "bg_封面",
            "type": "background",
            "category": "封面",
            "name": "封面2",
            "rel_path": rel,
            "abs_path": str(COVER_ROOT.resolve()),
            "web_path": rel,
            "tags": ["封面", "标题页"],
            "active": True,
            **meta,
        }
        idx = data.setdefault("cursor_index", [])
        found = False
        for item in idx:
            if item.get("asset_key") == "bg_封面":
                item.update(cover)
                found = True
                updated += 1
                break
        if not found:
            idx.append(cover)
            updated += 1

    data["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    idx = data.get("cursor_index", [])
    summary = data.setdefault("summary", {})
    summary["active_asset_count"] = sum(1 for item in idx if item.get("active") is not False)
    summary["background_count"] = sum(1 for item in idx if item.get("type") == "background" and item.get("active") is not False)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: 新增 {added} 条，更新 {updated} 条背景/封面")

    bundle = ROOT / "scripts" / "bundle_offline_data.py"
    subprocess.run([sys.executable, str(bundle)], cwd=str(ROOT), check=True)


if __name__ == "__main__":
    main()
