# -*- coding: utf-8 -*-
"""扫描 结局/ 目录，将 PNG 写入 cursor_asset_manifest.json 并重新打包离线数据。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "cursor_asset_manifest.json"
ENDING_DIR = ROOT / "结局"


def ending_title_from_stem(stem: str) -> str:
    s = stem.strip()
    if s.startswith("《") and s.endswith("》"):
        return s[1:-1]
    return s


def build_entry(png: Path) -> dict:
    title = ending_title_from_stem(png.stem)
    rel = f"结局/{png.name}"
    key = f"ending_《{title}》"
    return {
        "asset_key": key,
        "type": "ending_cg",
        "category": "结局",
        "name": f"《{title}》",
        "rel_path": rel,
        "abs_path": str(png.resolve()),
        "web_path": rel,
        "active": True,
        "matched_in_md": title == "爱与梦想终将圆满",
        "md_mapping": {"ending": title.replace("，", ""), "image_keywords": "HE"},
        "tags": ["ending", f"《{title}》"],
    }


def main():
    if not ENDING_DIR.is_dir():
        print(f"Missing {ENDING_DIR}")
        sys.exit(1)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = []
    for png in sorted(ENDING_DIR.glob("*.png")):
        entries.append(build_entry(png))
    manifest.setdefault("assets_by_category", {})["ending_cg"] = entries
    manifest["summary"]["ending_cg_count"] = len(entries)
    manifest["summary"]["md_ending_count"] = len(entries)
    manifest["summary"]["md_ending_matched_count"] = len(entries)
    planning = manifest.setdefault("planning_from_md", {})
    planning["ending_cg_mapping"] = [
        {"ending": ending_title_from_stem(p.stem).replace("，", ""), "matched": True, "rel_path": f"结局/{p.name}"}
        for p in sorted(ENDING_DIR.glob("*.png"))
    ]
    for item in entries:
        manifest.setdefault("cursor_index", [])
        keys = {x.get("asset_key") for x in manifest["cursor_index"]}
        if item["asset_key"] not in keys:
            manifest["cursor_index"].append(item)
        else:
            for i, x in enumerate(manifest["cursor_index"]):
                if x.get("asset_key") == item["asset_key"]:
                    manifest["cursor_index"][i] = item
                    break
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(entries)} ending CGs")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "bundle_offline_data.py")], cwd=str(ROOT), check=False)


if __name__ == "__main__":
    main()
