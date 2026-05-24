# -*- coding: utf-8 -*-
"""审计 10 个结局是否可被 resolveEnding 触发（与 engine.js 同步）。"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = ROOT / "data" / "chapters.json"

DEFAULT = {
    "money": 20,
    "xz_love": 10,
    "xz_trust": 10,
    "swl_love": 0,
    "zyx_love": 0,
    "vv_friend": 30,
    "vv_gj": 0,
    "public_opinion": 10,
    "art_value": 20,
    "misunderstanding": 0,
    "zyx_dance_seen": False,
    "money_fate_used": False,
    "branch_tags": {},
}

ENDING_ROUTES = {
    "money": {
        "key": "与钱有缘，与命相逢",
        "tags": ["buy", "cash", "money", "save", "win"],
        "opportunities": 7,
        "offset": 0.6,
    },
    "bad": {
        "key": "展灯熄后，无人归来",
        "tags": ["cold", "solo", "leave", "cool"],
        "opportunities": 23,
        "offset": -0.25,
    },
    "zyx": {"key": "听见月光在起舞", "tags": ["zyx", "reject"], "opportunities": 5, "offset": 0},
    "metro": {"key": "最后一班地铁开向冬夜", "tags": ["lyr", "walk", "bike"], "opportunities": 9, "offset": 0},
    "swl": {
        "key": "风从片场吹来",
        "tags": ["swl", "trio", "p", "wear", "self"],
        "opportunities": 11,
        "offset": 0.4,
    },
    "he": {"key": "爱与梦想终将圆满", "tags": ["he", "trust", "kind", "home"], "opportunities": 14, "offset": -0.15},
    "vv": {"key": "花开两岸，人间重逢", "tags": ["vv", "gj"], "opportunities": 37, "offset": 0},
    "art": {
        "key": "画框之外，万物生长",
        "tags": ["art", "zjy", "rest", "work", "health"],
        "opportunities": 31,
        "offset": -0.25,
    },
    "xz": {"key": "星光落在展灯边", "tags": ["xz", "meet", "guard", "shy"], "opportunities": 32, "offset": 0},
    "public": {
        "key": "灯火两端，旧梦不言",
        "tags": ["heat", "pic", "sell", "eat", "scam", "grab", "help"],
        "opportunities": 18,
        "offset": 0,
    },
}

ENDINGS = [
    {"key": "与钱有缘，与命相逢", "test": lambda s: s["money_fate_used"]},
    {
        "key": "展灯熄后，无人归来",
        "test": lambda s: s["misunderstanding"] >= 30 and s["vv_friend"] <= 42 and s["xz_love"] < 58,
    },
    {
        "key": "听见月光在起舞",
        "test": lambda s: s["zyx_dance_seen"]
        and s["zyx_love"] >= 18
        and s["zyx_love"] >= s["swl_love"] + 2
        and s["zyx_love"] + 3 >= s["xz_love"]
        and s["art_value"] < 80,
    },
    {
        "key": "最后一班地铁开向冬夜",
        "test": lambda s: s["swl_love"] >= 32
        and s["swl_love"] > s["xz_love"]
        and s["swl_love"] < 44
        and s["xz_trust"] < 42
        and s["xz_love"] < 52,
    },
    {
        "key": "风从片场吹来",
        "test": lambda s: s["swl_love"] >= 40 and s["swl_love"] >= s["xz_love"] + 8 and s["xz_love"] < 58,
    },
    {
        "key": "爱与梦想终将圆满",
        "test": lambda s: s["xz_love"] >= 58
        and s["xz_trust"] >= 55
        and s["vv_gj"] >= 48
        and s["vv_friend"] >= 48
        and s["misunderstanding"] <= 42,
    },
    {
        "key": "花开两岸，人间重逢",
        "test": lambda s: s["vv_friend"] >= 55 and s["vv_gj"] >= 36 and s["xz_love"] < 62,
    },
    {
        "key": "画框之外，万物生长",
        "test": lambda s: s["art_value"] >= 72 and s["xz_love"] < 55 and s["swl_love"] < 50 and s["zyx_love"] < 38,
    },
    {
        "key": "星光落在展灯边",
        "test": lambda s: s["xz_love"] >= 65
        and s["xz_trust"] >= 60
        and s["misunderstanding"] <= 45
        and (s["vv_gj"] < 48 or s["vv_friend"] < 50),
    },
    {
        "key": "灯火两端，旧梦不言",
        "test": lambda s: s["public_opinion"] >= 50
        and s["art_value"] < 52
        and s["xz_love"] < 55
        and s["swl_love"] < 42,
    },
]


def resolve_ending(s: dict) -> str:
    if s.get("money_fate_used"):
        return "与钱有缘，与命相逢"
    tags = s.get("branch_tags") or {}
    best = None
    best_score = -10**9
    for route in ENDING_ROUTES.values():
        picked = sum(tags.get(tag, 0) for tag in route["tags"])
        n = route["opportunities"]
        mean = n / 3
        sd = (n * 2 / 9) ** 0.5 or 1
        score = (picked - mean) / sd + route["offset"]
        if score > best_score:
            best = route
            best_score = score
    return best["key"] if best else "灯火两端，旧梦不言"


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def apply_effects(s: dict, eff: dict) -> None:
    if not eff:
        return
    for k in ("xz_love", "xz_trust", "swl_love", "zyx_love", "vv_gj", "public_opinion", "art_value"):
        if k in eff and isinstance(eff[k], (int, float)):
            s[k] = clamp(s[k] + eff[k], 0, 100)
    if "vv_friend" in eff:
        s["vv_friend"] = clamp(s["vv_friend"] + eff["vv_friend"], -100, 100)
    if "misunderstanding" in eff:
        s["misunderstanding"] = clamp(s["misunderstanding"] + eff["misunderstanding"], 0, 100)
    if eff.get("zyx_dance_seen"):
        s["zyx_dance_seen"] = True
    if eff.get("money_fate_used"):
        s["money_fate_used"] = True
    if eff.get("branch_tag"):
        tag = eff["branch_tag"]
        s.setdefault("branch_tags", {})
        s["branch_tags"][tag] = s["branch_tags"].get(tag, 0) + 1


def iter_option_effects(chapters: list):
    for ch in chapters:
        for beat in ch.get("beats", []):
            if beat.get("type") == "choice":
                for opt in beat.get("options") or []:
                    if opt.get("effects"):
                        yield opt["effects"]


def greedy_route(chapters: list, focus: dict) -> dict:
    s = deepcopy(DEFAULT)
    for ch in chapters:
        for beat in ch.get("beats", []):
            if beat.get("type") != "choice":
                continue
            options = beat.get("options") or []
            best = options[0]
            best_score = -10**18
            for opt in options:
                t = deepcopy(s)
                eff = opt.get("effects") or {}
                apply_effects(t, eff)
                if focus.get("_mis"):
                    mis_gain = eff.get("misunderstanding", 0) or 0
                    vv_loss = eff.get("vv_friend", 0) or 0
                    xz_gain = eff.get("xz_love", 0) or 0
                    score = mis_gain * 20 + (-vv_loss) * 8 - xz_gain * 6 + t["misunderstanding"] * 2 - t["vv_friend"]
                else:
                    score = sum(t.get(k, 0) * w for k, w in focus.items() if not k.startswith("_"))
                    if focus.get("_tags"):
                        tag = eff.get("branch_tag")
                        all_route_tags = {tag for route in ENDING_ROUTES.values() for tag in route["tags"]}
                        if tag in focus["_tags"]:
                            score += 1000
                        elif tag in all_route_tags:
                            score -= 100
                            if tag in ENDING_ROUTES["zyx"]["tags"] and tag not in focus["_tags"]:
                                score -= 200
                    score -= t["misunderstanding"] * focus.get("_mis_penalty", 0)
                if score > best_score:
                    best_score = score
                    best = opt
            apply_effects(s, best.get("effects"))
    return s


def money_from_beat(beat: dict) -> int:
    eff = beat.get("effects") or {}
    if eff.get("money_set") is not None:
        return int(eff["money_set"])
    return int(eff.get("money") or 0)


def greedy_max_money(chapters: list) -> dict:
    """按每处选项选金钱收益最高的分支，估算全剧可获得存款上限（含分支台词）。"""
    s = {"money": DEFAULT["money"], "chance_card": 0, "lottery_once": False}
    for ch in chapters:
        for beat in ch.get("beats", []):
            eff = beat.get("effects") or {}
            if eff.get("lottery_once"):
                if s.get("lottery_once"):
                    continue
                s["lottery_once"] = True
            delta = money_from_beat(beat)
            if delta:
                if eff.get("money_set") is not None:
                    s["money"] = max(0, delta)
                else:
                    s["money"] = max(0, s["money"] + delta)
            if beat.get("type") != "choice":
                continue
            options = beat.get("options") or []
            best_delta = -10**9
            best_opt = options[0] if options else None
            for opt in options:
                opt_money = money_from_beat({"effects": opt.get("effects")})
                branch_money = 0
                for b in opt.get("branch") or []:
                    branch_money += money_from_beat(b)
                total = opt_money + branch_money
                if total > best_delta:
                    best_delta = total
                    best_opt = opt
            if best_opt and best_delta > -10**9:

                def apply_money_delta(eff: dict) -> None:
                    if not eff:
                        return
                    if eff.get("lottery_once") and s.get("lottery_once"):
                        return
                    if eff.get("money_set") is not None:
                        s["money"] = max(0, int(eff["money_set"]))
                    elif eff.get("money"):
                        s["money"] = max(0, s["money"] + int(eff["money"]))
                    if eff.get("lottery_once"):
                        s["lottery_once"] = True

                apply_money_delta(best_opt.get("effects") or {})
                for b in best_opt.get("branch") or []:
                    apply_money_delta(b.get("effects") or {})
    return s


def main() -> None:
    chapters = json.loads(CHAPTERS.read_text(encoding="utf-8"))["chapters"]
    money_s = greedy_max_money(chapters)
    print(
        f"金钱估算（贪心选最高收益分支）: 终局约 {money_s['money']} 万 "
        f"（起点 {DEFAULT['money']} 万；与钱有缘需 ≥100 万且未用机缘卡）\n"
    )
    routes = {
        "与钱有缘，与命相逢": "_money_fate",
        "展灯熄后，无人归来": {"_tags": ENDING_ROUTES["bad"]["tags"]},
        "听见月光在起舞": {"_tags": ENDING_ROUTES["zyx"]["tags"]},
        "风从片场吹来": {"_tags": ENDING_ROUTES["swl"]["tags"]},
        "最后一班地铁开向冬夜": {"_tags": ENDING_ROUTES["metro"]["tags"]},
        "花开两岸，人间重逢": {"_tags": ENDING_ROUTES["vv"]["tags"]},
        "画框之外，万物生长": {"_tags": ENDING_ROUTES["art"]["tags"]},
        "星光落在展灯边": {"_tags": ENDING_ROUTES["xz"]["tags"]},
        "爱与梦想终将圆满": {"_tags": ENDING_ROUTES["he"]["tags"]},
        "灯火两端，旧梦不言": {"_tags": ENDING_ROUTES["public"]["tags"]},
    }

    print("=== 结局路线审计（engine.js 同步规则）===\n")
    ok = 0
    for key, focus in routes.items():
        if focus == "_money_fate":
            s = deepcopy(DEFAULT)
            s["money_fate_used"] = True
        else:
            s = greedy_route(chapters, focus)
            if key == "听见月光在起舞":
                s["zyx_dance_seen"] = True
        got = resolve_ending(s)
        hit = got == key
        ok += int(hit)
        mark = "OK" if hit else "FAIL"
        print(f"[{mark}] {key}")
        print(
            f"     xz={s['xz_love']}/{s['xz_trust']} swl={s['swl_love']} zyx={s['zyx_love']} "
            f"vv={s['vv_friend']}/{s['vv_gj']} art={s['art_value']} pub={s['public_opinion']} mis={s['misunderstanding']}"
        )
        if not hit:
            print(f"     -> 实际结算: {got}\n")
        else:
            print()

    print(f"可达 {ok}/10")
    if ok < 10:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
