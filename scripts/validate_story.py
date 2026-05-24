# -*- coding: utf-8 -*-
"""检查 chapters.json：同场景重复角色、选项分支完整性"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "chapters.json").read_text(encoding="utf-8"))

def names_in(chars):
    out = []
    for c in chars or []:
        k = c.get("asset_key", "")
        if k.startswith("char_"):
            out.append(k.split("_")[1])
    return out

issues = []
for ch in data["chapters"]:
    for b in ch["beats"]:
        for label, node in [("beat", b)]:
            n = names_in(node.get("characters"))
            if len(n) != len(set(n)):
                issues.append(f"重复立绘 {ch['chapter']}章 {node.get('id')}: {n}")
            if node.get("type") == "choice":
                if not node.get("options") or len(node["options"]) < 2:
                    issues.append(f"选项不足 {node.get('id')}")
                for opt in node.get("options", []):
                    if not opt.get("branch"):
                        issues.append(f"分支为空 {node.get('id')} -> {opt.get('text')}")

print("issues:", len(issues))
for i in issues[:20]:
    print(" -", i)
if not issues:
    print("OK: 无同场景重复角色，选项结构完整")
