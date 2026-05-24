# -*- coding: utf-8 -*-
"""规范化 男角色/肖战 立绘并刷新 cursor_asset_manifest.json 中的元数据。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
XZ_DIR = ROOT / "男角色" / "肖战"
MANIFEST = ROOT / "cursor_asset_manifest.json"
MAX_H = 620
MAX_W = 720


def normalize_png(path: Path) -> tuple[int, int, int]:
    img = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    scale = min(MAX_W / img.width, MAX_H / img.height)
    nw = max(1, int(img.width * scale))
    nh = max(1, int(img.height * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
    canvas.paste(img, (0, 0), img)
    canvas.save(path, "PNG", optimize=True)
    return nw, nh, path.stat().st_size


def main() -> None:
    if not XZ_DIR.is_dir():
        raise SystemExit(f"目录不存在: {XZ_DIR}")

    meta: dict[str, tuple[int, int, int]] = {}
    for png in sorted(XZ_DIR.glob("*.png")):
        emotion = png.stem
        w, h, size = normalize_png(png)
        rel = f"男角色/肖战/{png.name}".replace("\\", "/")
        meta[emotion] = (w, h, size)
        print(f"  {png.name}: {w}x{h} ({size // 1024} KB)")

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    updated = 0
    for item in data.get("cursor_index", []):
        if item.get("character") != "肖战":
            continue
        emo = item.get("emotion")
        if emo not in meta:
            continue
        w, h, size = meta[emo]
        rel = f"男角色/肖战/{emo}.png"
        item["rel_path"] = rel
        item["web_path"] = rel
        item["abs_path"] = str((ROOT / rel).resolve())
        item["bytes"] = size
        item["width"] = w
        item["height"] = h
        item["mode"] = "RGBA"
        item["active"] = True
        updated += 1

    grouped = data.get("characters_grouped", {}).get("肖战", [])
    for item in grouped:
        emo = item.get("emotion")
        if emo in meta:
            w, h, size = meta[emo]
            rel = f"男角色/肖战/{emo}.png"
            item.update(
                rel_path=rel,
                web_path=rel,
                abs_path=str((ROOT / rel).resolve()),
                bytes=size,
                width=w,
                height=h,
                mode="RGBA",
                active=True,
            )

    data["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: 更新 {updated} 条肖战条目")


if __name__ == "__main__":
    main()
