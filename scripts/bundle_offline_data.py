# -*- coding: utf-8 -*-
"""将 JSON 配置打包为 js/offline-data.js，支持 file:// 双击 index.html 运行。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "cursor_asset_manifest.json"
CHAPTERS = ROOT / "data" / "chapters.json"
OUT = ROOT / "js" / "offline-data.js"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chapters = json.loads(CHAPTERS.read_text(encoding="utf-8"))
    payload = {"manifest": manifest, "chapters": chapters}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(
        "/* 离线数据包：由 scripts/bundle_offline_data.py 生成，勿手改 */\n"
        f"window.__KUI_STAR_OFFLINE__={body};\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
