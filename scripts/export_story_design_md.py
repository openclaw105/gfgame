# -*- coding: utf-8 -*-
"""从 story_content + chapters.json 导出《剧情设计说明》Markdown。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from generate_chapters import (
    CHAPTER_HINTS,
    CHAPTERS_META,
    CHOICE_BEAT_POSITIONS,
    STORY,
    mid_slots_between_choices,
)
from story_content import branch_for, STORY as STORY_MAP

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "剧情设计说明.md"
CHAPTERS_JSON = ROOT / "data" / "chapters.json"

EFFECT_ZH = {
    "money": "金钱（选项点击不立刻改，见分支台词）",
    "money_set": "金钱设为",
    "chance_card": "机缘卡",
    "xz_love": "肖战好感",
    "xz_trust": "肖战信任",
    "swl_love": "宋威龙好感",
    "zyx_love": "张艺兴好感",
    "lyr_love": "李昀锐好感",
    "gj_love": "龚俊好感",
    "vv_friend": "薇薇羁绊",
    "vv_gj": "薇薇×龚俊",
    "public_opinion": "舆论",
    "art_value": "艺术值",
    "misunderstanding": "误会",
    "kindness": "善意",
    "bad_karma": "缺德",
    "title": "称号",
    "branch_tag": "分支标记（引擎用）",
}


def fmt_effects(eff: dict | None) -> str:
    if not eff:
        return "—"
    parts = []
    for k, v in eff.items():
        label = EFFECT_ZH.get(k, k)
        parts.append(f"{label} {v:+d}" if isinstance(v, (int, float)) and k != "title" else f"{label}={v}")
    return "；".join(parts)


def unpack_line(item) -> tuple[str, str, str | None]:
    if len(item) >= 3 and isinstance(item[2], str) and item[2].startswith("bg_"):
        return item[0], item[1], item[2]
    if len(item) >= 3 and isinstance(item[2], dict):
        return item[0], item[1], None
    return item[0], item[1], None


def mid_gap_summary(open_len: int) -> str:
    main_i = open_len
    cp_i = 0
    parts = []
    for cn in range(1, 7):
        pos = CHOICE_BEAT_POSITIONS[cp_i]
        n = 0
        while main_i + 1 < pos and main_i < CHOICE_BEAT_POSITIONS[-1]:
            main_i += 1
            n += 1
        parts.append(f"C{cn}前×{n}")
        main_i = pos
        cp_i += 1
    return "、".join(parts)


def mid_gap_labels(open_len: int) -> list[str]:
    """每条 mid 对应「插入在第几次选项之前」。"""
    labels = []
    main_i = open_len
    cp_i = 0
    for cn in range(1, 7):
        pos = CHOICE_BEAT_POSITIONS[cp_i]
        while main_i + 1 < pos and main_i < CHOICE_BEAT_POSITIONS[-1]:
            labels.append(f"选项C{cn}前")
            main_i += 1
        main_i = pos
        cp_i += 1
    return labels


def format_dialog_block(who: str, text: str, bg: str | None, extra: dict | None = None) -> str:
    bg_s = f" `{bg}`" if bg else ""
    eff_s = ""
    if extra:
        eff_s = f"　｜效果：{fmt_effects(extra)}"
    return f"- **{who}**{bg_s}：{text}{eff_s}"


def chapter_meta_section(n: int) -> str:
    meta = CHAPTERS_META[n - 1]
    hints = CHAPTER_HINTS.get(n, [])
    lines = [
        f"| 主背景池 | {', '.join(meta.get('scene_pool', []))} |",
        f"| 过渡背景 | {', '.join(meta.get('transition_bg') or []) or '—'} |",
        f"| 章末背景 | {meta.get('finale_bg', '—')} |",
        f"| BGM | {meta.get('bgm', '—')} |",
        f"| 填充背景 | {meta.get('pad_bg', '—')} |",
    ]
    hint_rows = [f"| {', '.join(keys)} | `{bg}` |" for keys, bg in hints]
    return "\n".join(
        [
            "| 项目 | 值 |",
            "|------|-----|",
            *lines,
            "",
            "**背景关键词（无显式 bg 时可能匹配）**",
            "",
            "| 关键词 | 背景 |",
            "|--------|------|",
            *(hint_rows or ["| — | — |"]),
        ]
    )


def branch_section(ch_n: int, choices, branch_dict: dict, speakers) -> list[str]:
    out = []
    for ci, (question, opts) in enumerate(choices):
        out.append(f"#### 选项 {ci + 1}：{question}")
        out.append("")
        for oi, (txt, eff, tag) in enumerate(opts):
            custom = branch_dict.get(ci)
            is_custom = custom and oi < len(custom)
            out.append(f"##### {chr(65 + oi)}. {txt}")
            out.append("")
            out.append(f"- 选项效果（点击时，**不含金钱**）：{fmt_effects({k: v for k, v in (eff or {}).items()})}")
            out.append(f"- 分支 tag：`{tag}`")
            out.append(f"- 台词来源：{'**专属分支**' if is_custom else '⚠️ **默认模板**（建议补写）'}")
            out.append("")
            lines = custom[oi] if is_custom else branch_for(ch_n, ci, oi, txt, speakers)
            for item in lines:
                if len(item) >= 3 and isinstance(item[2], dict):
                    who, line, ex = item[0], item[1], item[2]
                    out.append(format_dialog_block(who, line, None, ex))
                else:
                    who, line = item[0], item[1]
                    out.append(format_dialog_block(who, line, None))
            out.append("")
    return out


def encounter_section(encounters: list) -> list[str]:
    if not encounters:
        return ["（本章无奇遇选项）", ""]
    out = []
    for enc in encounters:
        out.append(f"### 奇遇 `{enc.get('id')}`（插入节拍约 #{enc.get('at')}）")
        out.append("")
        out.append(f"- 主持：{enc.get('host', '—')}　NPC：`{enc.get('npc', '—')}`")
        out.append(f"- 背景：`{enc.get('bg', '—')}`　热搜：{enc.get('hot', '—')}")
        out.append(f"- **问题**：{enc.get('question', '—')}")
        out.append("")
        if enc.get("intro"):
            out.append("**开场 intro：**")
            out.append("")
            for item in enc["intro"]:
                who, line = item[0], item[1]
                out.append(format_dialog_block(who, line, None))
            out.append("")
        for oi, opt in enumerate(enc.get("options", [])):
            if len(opt) >= 4:
                txt, eff, tag, blines = opt[0], opt[1], opt[2], opt[3]
            else:
                txt, eff, tag, blines = opt[0], opt[1], "?", []
            out.append(f"#### {chr(65 + oi)}. {txt}（tag: `{tag}`）")
            out.append(f"- 效果：{fmt_effects(eff)}")
            out.append("")
            for item in blines:
                if len(item) >= 3 and isinstance(item[2], dict):
                    out.append(format_dialog_block(item[0], item[1], None, item[2]))
                else:
                    out.append(format_dialog_block(item[0], item[1], None))
            out.append("")
    return out


def play_order_from_json(ch_data: dict) -> list[str]:
    rows = []
    for b in ch_data.get("beats", []):
        bid = b.get("id", "?")
        typ = b.get("type", "?")
        if typ == "choice":
            rows.append(f"| {bid} | 选项 | {b.get('background', '')} | **{b.get('question', '')}** |")
        elif typ == "dialog":
            sp = b.get("speaker", "")
            t = (b.get("text") or "").replace("|", "\\|")
            if len(t) > 48:
                t = t[:48] + "…"
            rows.append(f"| {bid} | 对话 | {b.get('background', '')} | {sp}：{t} |")
        elif typ == "converge":
            rows.append(f"| {bid} | 星回顾 | — | {b.get('text', '')} |")
        elif typ == "demo_invite":
            rows.append(f"| {bid} | DEMO | {b.get('background', '')} | 张艺兴 DEMO |")
        elif typ == "ending":
            rows.append(f"| {bid} | 终局 | — | — |")
        else:
            rows.append(f"| {bid} | {typ} | — | — |")
    return rows


def build_document() -> str:
    json_data = json.loads(CHAPTERS_JSON.read_text(encoding="utf-8")) if CHAPTERS_JSON.exists() else None
    ch_by_n = {c["chapter"]: c for c in json_data["chapters"]} if json_data else {}

    parts = [
        "# 葵与星光旅人 · 剧情设计说明",
        "",
        f"> 自动生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        "> 源文件：`scripts/story_content.py`（剧本） + `scripts/generate_chapters.py`（组装规则）  ",
        "> 实机播放顺序见各章 **「生成后播放顺序」**（来自 `data/chapters.json`）。  ",
        "> 修改剧本后请运行：`python scripts/generate_chapters.py` 再刷新游戏。",
        "",
        "---",
        "",
        "## 一、全局结构",
        "",
        "### 1.1 章节与节拍",
        "",
        "- 全剧 **10 章**，每章目标 **≥36 节拍**（`MIN_CHAPTER_BEATS = 36`）。",
        "- 每章固定 **6 次选项**（含第 6 次章末抉择），虚拟节拍锚点："
        f" **{CHOICE_BEAT_POSITIONS}**（与开场字数共同决定选项之间插入多少条主线对话）。",
        "- **开场 OPEN** → 按锚点插入 **MID 主线池** → 每次 **CHOICE** → 分支立即播放 → 继续主线。",
        "- 第 3 / 6 / 9 章末尾追加 **星回顾（converge）**；第 10 章末尾 **ending**。",
        "- 第 6 章含固定 **DEMO 邀请节拍**（`demo_beat`）。",
        "",
        "### 1.2 选项与数值",
        "",
        "| 规则 | 说明 |",
        "|------|------|",
        "| 选项点击 | 立刻应用选项上的效果，但 **金钱会剔除**（`choice_effects_no_money`） |",
        "| 金钱变动 | 写在 **分支台词** 的 `effects` 里，播到该句时才结算 |",
        "| 分支台词 | 选完后约 3 句：葵行为 → 对方反应 → 旁白收束；无专属则用默认模板 |",
        "| 默认模板 | 葵复述选项 +「行，按你说的来。」+ 旁白收束（⚠️ 需人工补分支） |",
        "",
        "### 1.3 背景图规则",
        "",
        "- 台词三元组 `(说话人, 文本, bg_xxx)`：**显式背景优先**。",
        "- 无显式 bg：按本章 **CHAPTER_HINTS** 关键词匹配；否则 **粘性保持** 上一场景。",
        "- **选项面板背景** = 上一节拍背景（不根据题干关键词跳场景）。",
        "- **分支台词背景** 默认继承选项面板背景，除非台词触发新关键词。",
        "- 第 2 章 **主线禁止** 出现「三十万 / 刮开票面 / 发票中奖」等剧透（仅分支可出现）。",
        "",
        "### 1.4 其他系统",
        "",
        "- **支线插入**：`side[]` 在指定 `at` 节拍索引插入（生成后列表下标）。",
        "- **奇遇**：`encounters[]` 含 intro + 三选项 + 长分支，插入 `at` 节拍。",
        "- **肖战立绘**：第 3 章前多为 `char_肖战_伪装1`；第 5 章肌肉衣关键词 → `char_肖战_肌肉`。",
        "",
        "---",
        "",
        "## 二、分章设计（源稿）",
        "",
    ]

    for n in range(1, 11):
        story = STORY_MAP[n]
        meta = CHAPTERS_META[n - 1]
        open_lines = story["open"]
        mid_lines = story["mid"]
        choices = story["choices"]
        finale = story["finale"]
        branch = story.get("branch", {})
        side = story.get("side", [])
        enc = story.get("encounters", [])
        gaps = mid_slots_between_choices(len(open_lines))
        gap_lbl = mid_gap_labels(len(open_lines))

        parts.append(f"## 第 {n} 章：{meta['title']}")
        parts.append("")
        parts.append(chapter_meta_section(n))
        parts.append("")
        parts.append(
            f"- 开场 {len(open_lines)} 句　｜ MID 池 {len(mid_lines)} 句（需 {gaps} 句）　｜ 插槽：{mid_gap_summary(len(open_lines))}"
        )
        if story.get("demo_beat"):
            parts.append("- 含 **DEMO 邀请** 特殊节拍")
        parts.append("")

        parts.append("### 开场 OPEN")
        parts.append("")
        for item in open_lines:
            who, text, bg = unpack_line(item)
            parts.append(format_dialog_block(who, text, bg))
        parts.append("")

        parts.append("### 主线 MID（按生成器消耗顺序）")
        parts.append("")
        for i, item in enumerate(mid_lines):
            who, text, bg = unpack_line(item)
            lbl = gap_lbl[i] if i < len(gap_lbl) else "—"
            parts.append(f"**[{i + 1}] {lbl}**")
            parts.append(format_dialog_block(who, text, bg))
        parts.append("")

        if side:
            parts.append("### 支线 SIDE（插入位置 `at`）")
            parts.append("")
            for sq in side:
                parts.append(f"- **`{sq['id']}`** @{sq['at']}　{sq['speaker']}：`{sq['text']}`　bg=`{sq.get('bg', '—')}`")
            parts.append("")

        parts.extend(encounter_section(enc))

        parts.append("### 六次选项与分支")
        parts.append("")
        from generate_chapters import SPEAKERS

        parts.extend(branch_section(n, choices, branch, SPEAKERS.get(n, SPEAKERS[1])))

        fq, fopts = finale
        parts.append("### 章末抉择 FINALE")
        parts.append("")
        parts.append(f"**{fq}**")
        parts.append("")
        for txt, eff, tag in fopts:
            parts.append(f"- **{txt}** — {fmt_effects(eff)}（tag: `{tag}`）")
        parts.append("")

        if n in ch_by_n:
            parts.append("### 生成后播放顺序（chapters.json）")
            parts.append("")
            parts.append("| ID | 类型 | 背景 | 摘要 |")
            parts.append("|----|------|------|------|")
            parts.extend(play_order_from_json(ch_by_n[n]))
            parts.append("")

        parts.append("---")
        parts.append("")

    parts.append("## 三、修改指引")
    parts.append("")
    parts.append("1. 改台词 / 选项 / 分支：编辑 `scripts/story_content.py` 对应 `CHxx_*` 常量。")
    parts.append("2. 改选项间主线句数：须满足 `len(mid) >= mid_slots_between_choices(len(open))`，见 `generate_chapters.py`。")
    parts.append("3. 改背景关键词：编辑 `CHAPTER_HINTS` 或给台词加第三参数 `bg_xxx`。")
    parts.append("4. 生成数据：`python scripts/generate_chapters.py` → 更新 `data/chapters.json` 与 `js/offline-data.js`。")
    parts.append("5. 带 ⚠️ **默认模板** 的选项建议补 `CHxx_BRANCH`，避免逻辑与题干脱节。")
    parts.append("")

    missing = []
    from generate_chapters import SPEAKERS

    for n in range(1, 11):
        story = STORY_MAP[n]
        br = story.get("branch", {})
        for ci, (q, opts) in enumerate(story["choices"]):
            for oi, (txt, eff, tag) in enumerate(opts):
                if not (br.get(ci) and oi < len(br[ci])):
                    missing.append(f"- 第{n}章 选项{ci + 1} {chr(65 + oi)}：{txt[:28]}…")
    if missing:
        parts.append("## 四、仍使用默认分支模板的选项（建议补写）")
        parts.append("")
        parts.extend(missing)
        parts.append("")

    return "\n".join(parts)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    md = build_document()
    OUT.write_text(md, encoding="utf-8")
    print(f"Wrote {OUT} ({len(md)} chars, {len(md.splitlines())} lines)")


if __name__ == "__main__":
    main()
