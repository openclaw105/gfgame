# -*- coding: utf-8 -*-
"""生成 chapters.json：自然对话、行为选项、路人奇遇。"""
import json
import subprocess
import sys
from pathlib import Path

from story_content import STORY, branch_for

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "chapters.json"

STUDIO_BACKGROUNDS = frozenset({"bg_画室白天", "bg_画室晚上"})
BGM_STUDIO = "bgm_studio"


def bgm_for_background(bg, chapter_bgm):
    if bg in STUDIO_BACKGROUNDS:
        return BGM_STUDIO
    return chapter_bgm


CHAPTERS_META = [
    {
        "n": 1,
        "title": "画展偶遇",
        "bg": "bg_欧洲画展",
        "bg2": "bg_画作",
        "bg3": "bg_画展外",
        "bgm": "bgm_gallery_studio",
        "scene_pool": ["bg_欧洲画展", "bg_画作", "bg_画展外", "bg_欧洲街景", "bg_画室晚上"],
        "finale_bg": "bg_画展外",
        "pad_bg": "bg_欧洲画展",
        "transition_bg": ["bg_机场", "bg_欧洲街景"],
    },
    {
        "n": 2,
        "title": "玩具店与回国热搜",
        "bg": "bg_商场1",
        "bg2": "bg_玩具店",
        "bg3": "bg_商场2",
        "bgm": "bgm_mall_toyshop",
        "scene_pool": ["bg_商场1", "bg_玩具店", "bg_商场2", "bg_画作"],
        "finale_bg": "bg_商场1",
        "pad_bg": "bg_商场1",
        "transition_bg": ["bg_机场"],
    },
    {
        "n": 3,
        "title": "办公室布场",
        "bg": "bg_办公室",
        "bg2": "bg_布场1",
        "bg3": "bg_布场2",
        "bgm": "bgm_office_event",
        "scene_pool": ["bg_办公室", "bg_布场1", "bg_布场2", "bg_布场3", "bg_后台走廊"],
        "finale_bg": "bg_布场2",
        "pad_bg": "bg_布场2",
    },
    {
        "n": 4,
        "title": "会所灯影",
        "bg": "bg_会所1",
        "bg2": "bg_豪宅",
        "bg3": "bg_花园夜间",
        "bgm": "bgm_club_mansion_suite",
        "scene_pool": ["bg_会所1", "bg_豪宅", "bg_花园夜间"],
        "finale_bg": "bg_会所1",
        "pad_bg": "bg_会所1",
    },
    {
        "n": 5,
        "title": "片场速写与肌肉衣",
        "bg": "bg_片场1",
        "bg2": "bg_片场2",
        "bg3": "bg_片场3",
        "bgm": "bgm_film_set",
        "scene_pool": ["bg_片场1", "bg_片场2", "bg_片场3", "bg_片场4"],
        "finale_bg": "bg_车内",
        "pad_bg": "bg_片场2",
        "transition_bg": ["bg_车内"],
    },
    {
        "n": 6,
        "title": "啤酒节与DEMO",
        "bg": "bg_啤酒节",
        "bg2": "bg_演唱会1",
        "bg3": "bg_后台走廊",
        "bgm": "bgm_festival_concert",
        "scene_pool": ["bg_啤酒节", "bg_演唱会1", "bg_后台走廊"],
        "finale_bg": "bg_后台走廊",
        "pad_bg": "bg_演唱会1",
        "transition_bg": [],
    },
    {
        "n": 7,
        "title": "画室夜路",
        "bg": "bg_画室白天",
        "bg2": "bg_夜路1",
        "bg3": "bg_夜路2",
        "bgm": "bgm_nightroad",
        "scene_pool": ["bg_画室白天", "bg_夜路1", "bg_夜路2", "bg_夜路3"],
        "finale_bg": "bg_画室晚上",
        "pad_bg": "bg_夜路1",
        "transition_bg": ["bg_地铁", "bg_画室晚上"],
    },
    {
        "n": 8,
        "title": "第二次会所聚会",
        "bg": "bg_会所2",
        "bg2": "bg_火锅包间",
        "bg3": "bg_花园夜间",
        "bgm": "bgm_club_mansion_suite",
        "scene_pool": ["bg_会所2", "bg_火锅包间", "bg_花园夜间"],
        "finale_bg": "bg_会所2",
        "pad_bg": "bg_会所2",
    },
    {
        "n": 9,
        "title": "樱花公园",
        "bg": "bg_樱花公园1",
        "bg2": "bg_樱花公园2",
        "bg3": "bg_樱花公园2",
        "bgm": "bgm_dream_park",
        "scene_pool": ["bg_樱花公园1", "bg_樱花公园2"],
        "finale_bg": "bg_樱花公园2",
        "pad_bg": "bg_樱花公园1",
        "transition_bg": ["bg_迪士尼"],
    },
    {
        "n": 10,
        "title": "星光终章",
        "bg": "bg_发布会1",
        "bg2": "bg_总统套房",
        "bg3": "bg_画室白天",
        "bgm": "bgm_gallery_studio",
        "scene_pool": ["bg_发布会1", "bg_总统套房", "bg_画室白天"],
        "finale_bg": "bg_画室白天",
        "pad_bg": "bg_发布会1",
    },
]

# 分章关键词优先；仅匹配本章 scene_pool / transition_bg 中的背景
CHAPTER_HINTS = {
    1: [
        (("巴黎", "通行证", "展厅", "现场光线", "预览厅"), "bg_欧洲画展"),
        (("《街角星光》", "画框", "署名", "角落署名", "画作"), "bg_画作"),
        (("馆外", "展馆外", "侧门", "玻璃门", "街角咖啡店"), "bg_画展外"),
        (("欧洲街景", "那条街", "街灯", "街角"), "bg_欧洲街景"),
        (
            ("航站楼", "进航站楼", "值机", "托运处", "登机口", "跑道灯", "启程那天", "接机口", "落地了"),
            "bg_机场",
        ),
    ],
    2: [
        (("公寓", "接风", "修画", "回国第一周"), "bg_商场1"),
        (("玩具", "快闪", "兔子"), "bg_玩具店"),
        (("服务台", "发票", "侧门", "卖拐", "甜品", "兑奖", "商场关门"), "bg_商场1"),
    ],
    3: [
        (("后勤", "办公室"), "bg_办公室"),
        (("纸箱", "灯架", "背景布", "物料", "布场", "彩排", "龚俊"), "bg_布场1"),
        (("场务", "灯光师", "贴标", "贴反"), "bg_布场2"),
        (("后台走廊",), "bg_后台走廊"),
    ],
    4: [
        (("会所", "邀请函", "敬酒", "名片", "卢老师", "聚会"), "bg_会所1"),
        (("豪宅", "别墅", "这边安静"), "bg_豪宅"),
        (("花园", "露台", "披肩", "透气"), "bg_花园夜间"),
        (("小吃街", "油烟", "烤串", "黄哥", "后门"), "bg_小吃街"),
    ],
    5: [
        (("片场", "郊区", "夜戏", "剧照", "肌肉衣", "探班", "监视器", "宋威龙"), "bg_片场1"),
        (("速写", "画本", "画着"), "bg_片场2"),
        (("场务", "补光", "灯光师"), "bg_片场3"),
        (("收工", "剧组车", "最后一天"), "bg_车内"),
    ],
    6: [
        (("啤酒节后台", "啤酒节", "耳返还"), "bg_啤酒节"),
        (("演唱会", "演出结束", "舞台", "线材"), "bg_演唱会1"),
        (("侧门", "躲后台", "后台", "休息室", "耳返", "控台"), "bg_后台走廊"),
        (("演唱会", "灯海", "散场", "空瓶"), "bg_演唱会1"),
    ],
    7: [
        (("画室灯", "锁门下楼", "改稿", "画笔"), "bg_画室白天"),
        (("末班车", "风很冷", "夜风", "楼下", "刘哥", "草莓", "没车"), "bg_夜路1"),
        (("地铁", "地铁站", "走十分钟"), "bg_地铁"),
        (("打车", "网约车", "车费"), "bg_夜路2"),
        (("三轮", "大叔", "车铃"), "bg_夜路3"),
    ],
    8: [
        (("第二次会所", "会所", "龚俊也在"), "bg_会所2"),
        (("火锅", "辣锅", "清汤", "微辣"), "bg_火锅包间"),
        (("花园", "夜谈", "散场", "提前离场"), "bg_花园夜间"),
    ],
    9: [
        (("樱花公园", "布展", "旧预览册", "展签", "展商", "妈"), "bg_樱花公园1"),
        (("遛狗", "椅背上"), "bg_樱花公园2"),
        (("迪士尼", "烟花"), "bg_迪士尼"),
    ],
    10: [
        (("开展", "发布会", "签名册", "记者"), "bg_发布会1"),
        (("总统套房", "套房", "赴约"), "bg_总统套房"),
        (("安心画画", "慢慢走回去"), "bg_画室白天"),
    ],
}

# 强关键词：台词出现则背景必须匹配，避免误报不用泛词（热搜/托运等）
BG_TEXT_EXPECT = {
    1: [
        (
            ("进航站楼", "拖着画筒进航站楼", "值机托运排", "接机口的长镜头", "落地了。行李"),
            "bg_机场",
        ),
        (("通行证进馆", "展厅只开了暖灯"), "bg_欧洲画展"),
    ],
}


class SceneTracker:
    """章节内背景粘性：仅在有显式标注或关键词时切换，禁止按节拍乱轮换。"""

    def __init__(self, ch_n, meta):
        self.ch_n = ch_n
        self.meta = meta
        self.pool, self.allowed = chapter_allowed_bgs(meta)
        self.current = self.pool[0]

    def force(self, bg):
        if bg and bg in self.allowed:
            self.current = bg
        return self.current

    def _match_hints(self, text, question):
        blob = f"{text or ''}{question or ''}"
        if not blob:
            return None
        for keys, bg in CHAPTER_HINTS.get(self.ch_n, []):
            if bg not in self.allowed:
                continue
            if any(k in blob for k in keys):
                return bg
        return None

    def resolve(self, text="", question="", explicit=None, phase=None):
        if explicit and explicit in self.allowed:
            self.current = explicit
            return self.current
        hinted = self._match_hints(text, question)
        if hinted:
            self.current = hinted
            return self.current
        if phase == "open":
            self.current = self.pool[0]
        elif phase == "finale":
            self.current = self.meta.get("finale_bg", self.pool[-1])
        return self.current

SPEAKERS = {
    1: [("narrator", None), ("葵", "char_葵_开心"), ("肖战", "char_肖战_伪装1"), ("薇薇", "char_薇薇_开心")],
    2: [("narrator", None), ("葵", "char_葵_无语"), ("薇薇", "char_薇薇_惊讶"), ("肖战", "char_肖战_伪装1")],
    3: [("narrator", None), ("薇薇", "char_薇薇_疲惫"), ("龚俊", "char_龚俊_开心"), ("肖战", "char_肖战_担心")],
    4: [("narrator", None), ("卢昱晓", "char_卢昱晓_悲伤"), ("宋威龙", "char_宋威龙_开心"), ("葵", "char_葵_害羞")],
    5: [("narrator", None), ("宋威龙", "char_宋威龙_开心"), ("张婧仪", "char_张婧仪_开心"), ("肖战", "char_肖战_生气")],
    6: [("narrator", None), ("张艺兴", "char_张艺兴_开心"), ("肖战", "char_肖战_沉思"), ("孟子义", "char_孟子义_开心")],
    7: [("narrator", None), ("李昀锐", "char_李昀锐_开心"), ("葵", "char_葵_疲惫"), ("肖战", "char_肖战_害羞")],
    8: [("narrator", None), ("薇薇", "char_薇薇_生气"), ("李昀锐", "char_李昀锐_开心"), ("龚俊", "char_龚俊_开心"), ("肖战", "char_肖战_害羞")],
    9: [("narrator", None), ("赵今麦", "char_赵今麦_开心"), ("鞠婧祎", "char_鞠婧祎_愤怒"), ("肖战", "char_肖战_忧伤")],
    10: [("narrator", None), ("葵", "char_葵_开心"), ("肖战", "char_肖战_开心"), ("张艺兴", "char_张艺兴_跳舞")],
}

ASSET = {
    "葵": "char_葵_害羞",
    "肖战": "char_肖战_一般",
    "薇薇": "char_薇薇_开心",
    "宋威龙": "char_宋威龙_开心",
    "张艺兴": "char_张艺兴_开心",
    "李昀锐": "char_李昀锐_开心",
    "龚俊": "char_龚俊_开心",
    "卢昱晓": "char_卢昱晓_悲伤",
    "张婧仪": "char_张婧仪_开心",
    "孟子义": "char_孟子义_开心",
    "赵今麦": "char_赵今麦_开心",
    "鞠婧祎": "char_鞠婧祎_愤怒",
    "卖拐大叔": "npc_卖拐大叔",
    "卖草莓阿姨": "npc_刘哥",
    "刘哥": "npc_刘哥",
    "黄哥": "npc_黄哥",
    "三轮大叔": "npc_三轮大叔",
    "柜姐": "npc_柜姐1",
    "柜姐1": "npc_柜姐1",
    "柜姐2": "npc_柜姐2",
    "场务小哥": "npc_路人甲年轻男1",
    "灯光师老周": "npc_路人甲中年男2",
    "布场阿姨": "npc_路人乙中年女1",
    "遛狗阿姨": "npc_路人乙中年女2",
    "写生小哥": "npc_路人甲年轻男2",
    "樱花游客": "npc_路人乙年轻女1",
    "保安大叔": "npc_路人甲中年男1",
}

NPC_SPEAKERS = frozenset(ASSET.keys()) - frozenset(
    {"葵", "肖战", "薇薇", "宋威龙", "张艺兴", "李昀锐", "龚俊", "卢昱晓", "张婧仪", "孟子义", "赵今麦", "鞠婧祎"}
)

CHOICE_BEAT_POSITIONS = [7, 14, 21, 28, 32, 35]
MIN_CHAPTER_BEATS = 36


def mid_slots_between_choices(open_len):
    """主线在六次选项之间需要填充的对话条数。"""
    main_i = open_len
    cp_i = 0
    count = 0
    for _ in range(6):
        pos = CHOICE_BEAT_POSITIONS[cp_i]
        while main_i + 1 < pos and main_i < CHOICE_BEAT_POSITIONS[-1]:
            main_i += 1
            count += 1
        main_i = pos
        cp_i += 1
    return count


def mid_pool_for(story):
    return list(story["mid"]) + list(story.get("pad", []))


def unpack_branch_line(item):
    muscle = False
    hot = None
    eff = None
    bg = None
    flags = None
    if len(item) >= 3:
        if isinstance(item[2], str) and item[2].startswith("bg_"):
            bg = item[2]
            if len(item) >= 4 and isinstance(item[3], dict):
                flags = item[3]
        elif isinstance(item[2], dict):
            flags = item[2]
    if flags:
        d = dict(flags)
        muscle = bool(d.pop("muscle_sprite", False))
        hot = d.pop("hot", None)
        eff = d if d else None
    return item[0], item[1], eff, muscle, hot, bg


def choice_effects_no_money(eff):
    """选项面板效果不含金钱，金钱只在分支台词 beat.effects 中触发。"""
    if not eff:
        return {}
    out = dict(eff)
    out.pop("money", None)
    out.pop("money_set", None)
    return out


NPC_HOST = {
    "npc_卖拐大叔": "卖拐大叔",
    "npc_黄哥": "黄哥",
    "npc_刘哥": "刘哥",
    "npc_三轮大叔": "三轮大叔",
    "npc_柜姐1": "柜姐",
    "npc_柜姐2": "柜姐",
}


def encounter_host_name(enc):
    return enc.get("host") or NPC_HOST.get(enc.get("npc"), "")


def encounter_choice_characters(ch_n, enc):
    npc = enc.get("npc")
    hero = "char_葵_无语"
    eid = enc.get("id", "")
    if eid.endswith("HUANG") or npc == "npc_黄哥":
        hero = "char_葵_开心"
    elif eid.endswith("TRIKE") or npc == "npc_三轮大叔":
        hero = "char_葵_疲惫"
    return scene_chars("葵", ch_n, hero=hero, npc=npc)


def unpack_story_line(item):
    """(speaker, line) 或 (speaker, line, bg_key) 或带 flags 字典"""
    flags = {}
    bg = None
    if len(item) >= 3:
        if isinstance(item[2], str) and item[2].startswith("bg_"):
            bg = item[2]
            if len(item) >= 4 and isinstance(item[3], dict):
                flags = item[3]
        elif isinstance(item[2], dict):
            flags = item[2]
    return item[0], item[1], bg, flags


def chapter_allowed_bgs(meta):
    pool = meta.get("scene_pool") or [meta["bg"], meta["bg2"], meta["bg3"]]
    extra = meta.get("transition_bg") or []
    finale = meta.get("finale_bg")
    allowed = list(dict.fromkeys(pool + extra + ([finale] if finale else [])))
    return pool, allowed


def scene_chars_for_line(
    speaker, ch_n, text, enc_npc=None, question="", muscle_sprite=False, xz_reveal=False
):
    """奇遇进行中：葵/旁白时保留奇遇 NPC 在画面；其他角色出场则正常对话站位。"""
    if speaker in ("葵", "narrator"):
        return scene_chars(
            "葵",
            ch_n,
            text=text,
            npc=enc_npc,
            xz_muscle=False,
            other=None,
            muscle_sprite=muscle_sprite,
            xz_reveal=xz_reveal,
        )
    if speaker in NPC_SPEAKERS:
        return scene_chars(speaker, ch_n, text=text, muscle_sprite=muscle_sprite, xz_reveal=xz_reveal)
    return scene_chars(speaker, ch_n, text=text, muscle_sprite=muscle_sprite, xz_reveal=xz_reveal)


def branch_dialog_beat(
    bid,
    who,
    line,
    ch_n,
    meta,
    bi,
    question,
    enc_npc=None,
    effects=None,
    scene_bg=None,
    encounter_npc=None,
    scene=None,
    muscle_sprite=False,
    xz_reveal=False,
    hot=None,
):
    chars = scene_chars_for_line(
        who, ch_n, line, enc_npc, question=question, muscle_sprite=muscle_sprite, xz_reveal=xz_reveal
    )
    if scene_bg:
        bg = scene_bg
        if scene:
            scene.force(scene_bg)
    elif scene:
        hinted = scene._match_hints(line, question)
        if hinted:
            bg = scene.force(hinted)
        else:
            bg = scene.current
    else:
        bg = meta["bg"]
    beat = {
        "id": bid,
        "type": "dialog",
        "speaker": who,
        "text": line,
        "background": bg,
        "bgm": bgm_for_background(bg, meta["bgm"]),
        "characters": chars,
    }
    if effects:
        beat["effects"] = effects
    if muscle_sprite:
        beat["muscle_sprite"] = True
    if xz_reveal:
        beat["xz_reveal"] = True
    if hot:
        tags = [t.strip() for t in str(hot).split(",") if t.strip()]
        if tags:
            beat["hot"] = tags[0]
            if len(tags) > 1:
                beat["hot_extra"] = tags[1:]
    host = NPC_HOST.get(encounter_npc or "", "")
    if encounter_npc and who in ("葵", "narrator"):
        beat["encounter_npc"] = encounter_npc
    return beat


def xz_identity_revealed_line(text):
    t = text or ""
    return any(
        k in t
        for k in (
            "摘下",
            "摘掉",
            "露出脸",
            "真面目",
            "我是肖战",
            "原来是你",
            "认出来",
            "摘下口罩",
            "原来叫肖战",
            "原来他叫肖战",
            "真的是肖战",
            "真的是他",
            "画展陌生人",
            "顶流私服",
            "卸了伪装",
            "当普通观众",
            "不是来营业",
            "原来是你",
            "正式认识",
            "没有口罩",
        )
    )


def xz_disguise_asset(ch_n, text=None, xz_reveal=False, xz_flashback_masked=False):
    """未亮明身份前，或第2章闪回（已揭秘名字、仍用口罩立绘）"""
    if xz_flashback_masked:
        return "char_肖战_伪装1"
    if ch_n >= 3 or xz_identity_revealed_line(text) or xz_reveal:
        return None
    return "char_肖战_伪装1"


def emotion_for(speaker, text, ch_n=None, muscle_sprite=False, xz_reveal=False, xz_flashback_masked=False):
    t = text or ""
    if speaker == "肖战" and muscle_sprite:
        return "肌肉"
    if speaker == "肖战" and xz_flashback_masked:
        return "伪装1"
    if speaker == "肖战" and xz_reveal and not xz_flashback_masked:
        return "一般"
    if (
        speaker == "肖战"
        and ch_n
        and ch_n < 3
        and not xz_reveal
        and not xz_flashback_masked
        and not xz_identity_revealed_line(text)
    ):
        return "伪装1"
    if speaker == "张艺兴" and any(k in t for k in ("跳舞", "起舞", "舞步")):
        return "跳舞"
    if any(k in t for k in ("哭", "泪", "难过", "心碎", "抱歉", "对不起", "失望", "离别")):
        return "悲伤"
    if any(k in t for k in ("怒", "气死", "烦死", "滚", "讨厌")):
        return "生气"
    if any(k in t for k in ("担心", "没事吧", "别怕", "小心", "受伤")):
        return "担心"
    if any(k in t for k in ("累", "困", "熬夜", "疲惫")):
        return "疲惫"
    if any(k in t for k in ("害羞", "脸红", "不好意思")):
        return "害羞"
    if any(k in t for k in ("惊", "哇", "天啊", "不会吧", "愣")):
        return "惊讶"
    if any(k in t for k in ("沉思", "想想", "沉默")):
        return "沉思"
    if any(k in t for k in ("笑", "哈", "开心", "太好了", "棒", "谢谢", "喜欢")):
        return "开心"
    if "……" in t or "..." in t:
        return "无语"
    return "一般"


def asset_for(speaker, ch_n, text=None, muscle_sprite=False, xz_reveal=False, xz_flashback_masked=False):
    if speaker == "narrator":
        return None
    if speaker in NPC_SPEAKERS:
        return ASSET[speaker]
    disguise = xz_disguise_asset(
        ch_n, text, xz_reveal=xz_reveal, xz_flashback_masked=xz_flashback_masked
    )
    if speaker == "肖战" and disguise:
        return disguise
    if text:
        emo = emotion_for(
            speaker,
            text,
            ch_n,
            muscle_sprite=muscle_sprite,
            xz_reveal=xz_reveal,
            xz_flashback_masked=xz_flashback_masked,
        )
        key = f"char_{speaker}_{emo}"
        sp = SPEAKERS.get(ch_n, SPEAKERS[1])
        if speaker in {n for n, _ in sp}:
            return key
        if speaker == "肖战" and (
            ch_n >= 3 or (xz_reveal and not xz_flashback_masked) or xz_identity_revealed_line(text)
        ):
            return key
    if speaker == "肖战" and ch_n >= 3:
        return "char_肖战_一般"
    sp = SPEAKERS.get(ch_n, SPEAKERS[1])
    for name, key in sp:
        if name == speaker:
            return key
    return ASSET.get(speaker, "char_葵_无语")


def scene_chars(
    speaker,
    ch_n,
    hero=None,
    other=None,
    npc=None,
    text=None,
    xz_muscle=False,
    muscle_sprite=False,
    xz_reveal=False,
    xz_flashback_masked=False,
):
    arr = []
    seen = set()
    h = hero or asset_for("葵", ch_n, text) or "char_葵_无语"
    if muscle_sprite and speaker == "肖战":
        other = "char_肖战_肌肉"
    elif xz_muscle and not other:
        other = "char_肖战_肌肉"

    def push(key, pos):
        if not key:
            return
        name = key[4:] if key.startswith("npc_") else (key.split("_")[1] if key.startswith("char_") else key)
        if name in seen:
            return
        seen.add(name)
        arr.append({"asset_key": key, "position": pos, "slot": len(arr)})

    if speaker == "葵":
        push(h, "hero-left")
        if other:
            push(other, "speaker-right")
        if npc:
            push(npc, "speaker-right")
    elif speaker == "narrator" and xz_muscle and other:
        push(h, "hero-left")
        push(other, "speaker-right")
    elif speaker and speaker != "narrator":
        push(h, "hero-left")
        push(
            npc
            or other
            or asset_for(
                speaker,
                ch_n,
                text,
                muscle_sprite=muscle_sprite,
                xz_reveal=xz_reveal,
                xz_flashback_masked=xz_flashback_masked,
            ),
            "speaker-right",
        )
    elif npc:
        push(h, "hero-left")
        push(npc, "center")
    return arr[:3]


def inject_side_quests(beats, ch_n, scene):
    story = STORY.get(ch_n, {})
    meta = CHAPTERS_META[ch_n - 1]
    for sq in story.get("side", []):
        idx = min(sq["at"], len(beats))
        if sq.get("bg"):
            scene.force(sq["bg"])
        beat = {
            "id": sq["id"],
            "type": "dialog",
            "speaker": sq["speaker"],
            "text": sq["text"],
            "background": sq.get("bg") or scene.resolve(text=sq["text"]),
            "bgm": bgm_for_background(sq.get("bg") or scene.current, meta["bgm"]),
            "characters": scene_chars_for_line(
                sq["speaker"], ch_n, sq["text"], sq.get("npc")
            ),
        }
        if sq.get("hot"):
            beat["hot"] = sq["hot"]
        if sq.get("requires_branch_tag"):
            beat["requires_branch_tag"] = sq["requires_branch_tag"]
        beats.insert(idx, beat)


def choice_panel_bg(meta, question, is_finale, scene, last_beat_bg=None):
    """选项面板沿用上一节拍背景，避免关键词误切场景。"""
    if is_finale:
        return meta.get("finale_bg", scene.pool[-1])
    if last_beat_bg and last_beat_bg in scene.allowed:
        return last_beat_bg
    return scene.current


def inject_encounters(beats, ch_n, speakers, scene):
    story = STORY.get(ch_n, {})
    meta = CHAPTERS_META[ch_n - 1]
    for enc in story.get("encounters", []):
        idx = min(enc["at"], len(beats))
        enc_npc = enc.get("npc")
        if enc.get("bg"):
            scene.force(enc["bg"])
        intro = enc.get("intro") or []
        if isinstance(intro, tuple):
            intro = [intro]
        for ii, item in enumerate(intro):
            who, line, line_eff, muscle, hot, line_bg = unpack_branch_line(item)
            beats.insert(
                idx + ii,
                branch_dialog_beat(
                    f"{enc['id']}_INTRO_{ii+1}",
                    who,
                    line,
                    ch_n,
                    meta,
                    ii,
                    enc.get("question", ""),
                    enc_npc,
                    line_eff,
                    line_bg or enc.get("bg"),
                    encounter_npc=enc_npc,
                    scene=scene,
                ),
            )
        choice_idx = idx + len(intro)
        options = []
        for oi, opt in enumerate(enc["options"]):
            if len(opt) >= 4:
                txt, opt_eff, tag, lines = opt[0], opt[1], opt[2], opt[3]
                branch = []
                for bi, item in enumerate(lines):
                    who, line, line_eff, muscle, hot, line_bg = unpack_branch_line(item)
                    branch.append(
                        branch_dialog_beat(
                            f"{enc['id']}_O{oi+1}_B{bi+1}",
                            who,
                            line,
                            ch_n,
                            meta,
                            bi,
                            enc.get("question", ""),
                            enc_npc,
                            line_eff,
                            line_bg or enc.get("bg"),
                            encounter_npc=enc_npc,
                            scene=scene,
                            muscle_sprite=muscle,
                            hot=hot,
                        )
                    )
            else:
                txt, opt_eff, tag = opt[0], opt[1], opt[2]
                lines = branch_for(ch_n, -1, oi, txt, speakers)
                branch = []
                for bi, item in enumerate(lines):
                    who, line, line_eff, muscle, hot, line_bg = unpack_branch_line(item)
                    branch.append(
                        branch_dialog_beat(
                            f"{enc['id']}_O{oi+1}_B{bi+1}",
                            who,
                            line,
                            ch_n,
                            meta,
                            bi,
                            enc.get("question", ""),
                            enc_npc,
                            line_eff,
                            line_bg or enc.get("bg"),
                            encounter_npc=enc_npc,
                            scene=scene,
                            muscle_sprite=muscle,
                            hot=hot,
                        )
                    )
            eff2 = choice_effects_no_money(opt_eff)
            eff2["branch_tag"] = tag
            options.append({"text": txt, "effects": eff2, "branch": branch})
        host = encounter_host_name(enc)
        choice_beat = {
            "id": enc["id"],
            "type": "choice",
            "question": enc.get("question"),
            "background": enc.get("bg") or scene.current,
            "bgm": bgm_for_background(enc.get("bg") or scene.current, meta["bgm"]),
            "characters": encounter_choice_characters(ch_n, enc),
            "encounter_npc": enc_npc,
            "host_speaker": host,
            "milestone": "encounter",
            "options": options,
        }
        if enc.get("hot"):
            choice_beat["hot"] = enc["hot"]
        beats.insert(choice_idx, choice_beat)


def build_chapter(meta):
    n = meta["n"]
    ch_id = f"CH{n:02d}"
    story = STORY[n]
    speakers = SPEAKERS.get(n, SPEAKERS[1])
    beats = []
    beat_idx = 0
    mid_i = 0
    mid_pool = mid_pool_for(story)
    need_mid = mid_slots_between_choices(len(story["open"]))
    if len(mid_pool) < need_mid:
        raise ValueError(
            f"第{n}章 mid+pad 仅 {len(mid_pool)} 条，需要 {need_mid} 条（禁止循环复用台词）"
        )
    scene = SceneTracker(n, meta)

    def add_line(speaker, text, bg=None, hot=None, npc=None, phase="main", flags=None):
        nonlocal beat_idx
        beat_idx += 1
        flags = flags or {}
        resolved = scene.resolve(text=text, explicit=bg, phase=phase)
        muscle_sprite = bool(flags.get("muscle_sprite"))
        xz_reveal = bool(flags.get("xz_reveal"))
        xz_flashback_masked = bool(flags.get("xz_flashback_masked"))
        beats.append({
            "id": f"{ch_id}_B{beat_idx:02d}",
            "type": "dialog",
            "speaker": speaker,
            "text": text,
            "background": resolved,
            "bgm": bgm_for_background(resolved, meta["bgm"]),
            "characters": scene_chars(
                speaker,
                n,
                text=text,
                npc=npc,
                muscle_sprite=muscle_sprite,
                xz_reveal=xz_reveal,
                xz_flashback_masked=xz_flashback_masked,
            ),
        })
        if muscle_sprite:
            beats[-1]["muscle_sprite"] = True
        if xz_reveal:
            beats[-1]["xz_reveal"] = True
        if xz_flashback_masked:
            beats[-1]["xz_flashback_masked"] = True
        hot_tag = hot or flags.get("hot")
        if hot_tag:
            tags = [t.strip() for t in str(hot_tag).split(",") if t.strip()]
            if tags:
                beats[-1]["hot"] = tags[0]
                if len(tags) > 1:
                    beats[-1]["hot_extra"] = tags[1:]

    def next_mid(explicit_bg=None):
        nonlocal mid_i
        if mid_i >= len(mid_pool):
            raise IndexError(f"第{n}章 mid 池已用尽（{mid_i}/{need_mid}），请补充 story_content")
        sp, txt, line_bg_key, flags = unpack_story_line(mid_pool[mid_i])
        mid_i += 1
        add_line(sp, txt, bg=explicit_bg or line_bg_key, phase="mid", flags=flags)

    for item in story["open"]:
        sp, txt, line_bg_key, flags = unpack_story_line(item)
        add_line(sp, txt, bg=line_bg_key, phase="open", flags=flags)

    if story.get("demo_beat"):
        beat_idx += 1
        demo_bg = meta.get("bg3") or meta.get("bg2") or meta["bg"]
        beats.append({
            "id": f"{ch_id}_DEMO",
            "type": "demo_invite",
            "speaker": "张艺兴",
            "text": "散场后工作室见。先戴耳机听段新编舞 DEMO，别在这儿挤。",
            "background": demo_bg,
            "bgm": meta["bgm"],
            "characters": scene_chars("张艺兴", n, text="跳舞"),
        })

    choice_positions = CHOICE_BEAT_POSITIONS
    cp_i = 0
    main_i = len(story["open"])

    for choice_num in range(1, 7):
        while main_i + 1 < choice_positions[cp_i] and main_i < choice_positions[-1]:
            main_i += 1
            next_mid()

        main_i = choice_positions[cp_i]
        is_finale = choice_num == 6
        ct = story["finale"] if is_finale else story["choices"][cp_i]
        beat_idx += 1
        cid = f"{ch_id}_C{choice_num}"
        last_bg = beats[-1].get("background") if beats else scene.pool[0]
        panel_bg = choice_panel_bg(meta, ct[0], is_finale, scene, last_bg)
        options = []
        for oi, (txt, choice_eff, tag) in enumerate(ct[1]):
            lines = branch_for(n, cp_i, oi, txt, speakers)
            branch = []
            for bi, item in enumerate(lines):
                who, line, line_eff, muscle, hot, line_bg = unpack_branch_line(item)
                branch.append(
                    branch_dialog_beat(
                        f"{cid}_O{oi+1}_B{bi+1}",
                        who,
                        line,
                        n,
                        meta,
                        bi,
                        ct[0],
                        None,
                        line_eff,
                        scene_bg=line_bg or panel_bg,
                        scene=scene,
                        muscle_sprite=muscle,
                        hot=hot,
                    )
                )
            eff2 = choice_effects_no_money(choice_eff)
            eff2["branch_tag"] = tag
            options.append({"text": txt, "effects": eff2, "branch": branch})

        choice_beat = {
            "id": cid,
            "type": "choice",
            "question": ct[0],
            "background": panel_bg,
            "bgm": bgm_for_background(panel_bg, meta["bgm"]),
            "characters": scene_chars(
                "葵",
                n,
                hero="char_葵_开心" if is_finale else "char_葵_无语",
            ),
            "options": options,
        }
        if is_finale:
            choice_beat["milestone"] = "chapter_finale"
        if "机缘卡" in (ct[0] or ""):
            choice_beat["requires_chance_card"] = True
        gate = story.get("choice_gate", {}).get(cp_i)
        if gate:
            choice_beat["requires_branch_tag"] = gate
        beats.append(choice_beat)
        cp_i += 1

    inject_side_quests(beats, n, scene)
    inject_encounters(beats, n, speakers, scene)

    tail = story.get("tail", [])
    tail_i = 0
    while len(beats) < MIN_CHAPTER_BEATS:
        if tail_i >= len(tail):
            break
        sp, txt, line_bg, flags = unpack_story_line(tail[tail_i])
        tail_i += 1
        scene.force(line_bg or meta.get("pad_bg", scene.pool[0]))
        add_line(sp, txt, bg=line_bg, phase="tail", flags=flags)

    if n in (3, 6, 9):
        beats.append({
            "id": f"{ch_id}_CONVERGE",
            "type": "converge",
            "cycle": n // 3,
            "text": "这一章的故事汇进了你的星图，下一程仍在前方。",
        })
    if n == 10:
        beats.append({"id": "CH10_ENDING", "type": "ending", "text": "终局判定启动。"})

    return {"chapter": n, "title": meta["title"], "beat_count": len(beats), "beats": beats}


CH02_MAIN_SPOILERS = ("三十万", "刮开票面", "刮发票——", "发票中奖", "兑奖处排长队")
DIALOGUE_FORBIDDEN = ("龚俊线", "跟薇薇线", "肖战线", "某某线")


def audit_ch02_double_lottery(chapters):
    """第2章仅应有一处三十万奖金（服务台刮票分支）。"""
    issues = []
    ch = next((c for c in chapters if c["chapter"] == 2), None)
    if not ch:
        return issues
    wins = []
    for b in ch["beats"]:
        eff = b.get("effects") or {}
        if eff.get("money") == 30 or (eff.get("lottery_once") and eff.get("money")):
            wins.append(b.get("id"))
    if len(wins) > 1:
        issues.append(f"  CH02 检测到 {len(wins)} 处三十万奖金: {', '.join(wins)}")
    elif len(wins) == 1 and not any("CH02_C2_O1" in w for w in wins):
        issues.append(f"  CH02 三十万应仅在服务台刮票分支，实际在 {wins[0]}")
    return issues


def audit_ch02_main_spoilers(chapters):
    issues = []
    ch = next((c for c in chapters if c["chapter"] == 2), None)
    if not ch:
        return issues
    for b in ch["beats"]:
        if b.get("type") != "dialog":
            continue
        if "_O" in b.get("id", ""):
            continue
        t = b.get("text") or ""
        for w in CH02_MAIN_SPOILERS:
            if w in t:
                issues.append(f"  CH02 主线 [{b['id']}] 剧透词「{w}」: {t[:36]}…")
                break
    return issues


def audit_background_mismatches(chapters):
    """检查台词关键词与背景是否明显不符。"""
    issues = []
    for ch in chapters:
        n = ch["chapter"]
        rules = BG_TEXT_EXPECT.get(n, [])
        if not rules:
            continue
        for b in ch["beats"]:
            if b.get("type") != "dialog":
                continue
            text = b.get("text") or ""
            bg = b.get("background") or ""
            for keys, expect in rules:
                if any(k in text for k in keys) and bg != expect:
                    issues.append(
                        f"  CH{n:02d} [{b['id']}] 期望 {expect} 实为 {bg} — {text[:40]}…"
                    )
                    break
        if n == 2:
            for b in ch["beats"]:
                if b.get("background") == "bg_机场":
                    issues.append(
                        f"  CH02 [{b['id']}] 第2章不应使用机场背景 — {(b.get('text') or b.get('question') or '')[:40]}…"
                    )
    return issues


def audit_xz_disguise_after_reveal(chapters):
    """第3章及以后不应再写入肖战伪装立绘（生成数据自检）。"""
    bad = []
    for ch in chapters:
        n = ch.get("chapter", 0)
        if n < 3:
            continue
        for b in ch.get("beats", []):
            for c in b.get("characters") or []:
                ak = c.get("asset_key") or ""
                if "肖战" in ak and "伪装" in ak:
                    bad.append(f"  ch{n} {b.get('id')} {ak} «{str(b.get('text', ''))[:36]}»")
    return bad


def audit_forbidden_dialogue(chapters):
    issues = []
    for ch in chapters:
        n = ch["chapter"]
        for b in ch.get("beats", []):
            for field in ("text", "question"):
                t = b.get(field) or ""
                for w in DIALOGUE_FORBIDDEN:
                    if w in t:
                        issues.append(f"  CH{n:02d} [{b.get('id')}] 禁用词「{w}」: {t[:40]}…")
            for opt in b.get("options") or []:
                ot = opt.get("text") or ""
                for w in DIALOGUE_FORBIDDEN:
                    if w in ot:
                        issues.append(f"  CH{n:02d} [{b.get('id')}] 选项禁用词「{w}」: {ot[:40]}…")
    return issues


def audit_dialog_duplicates(chapters):
    """检查章内是否出现相同说话人+相同台词（循环 mid 的典型症状）。"""
    issues = []
    for ch in chapters:
        seen = {}
        for b in ch["beats"]:
            if b.get("type") != "dialog":
                continue
            key = (b.get("speaker"), b.get("text"))
            if key in seen:
                issues.append(
                    f"  CH{ch['chapter']:02d}: 重复 [{b['id']}] 与 [{seen[key]}] — {key[1][:36]}…"
                )
            else:
                seen[key] = b["id"]
    return issues


def main():
    data = {
        "version": "kui_star_chapters_v3",
        "choice_beats": CHOICE_BEAT_POSITIONS,
        "chapters": [build_chapter(m) for m in CHAPTERS_META],
    }
    ch02_sp = audit_ch02_main_spoilers(data["chapters"])
    if ch02_sp:
        print("警告：第2章主线含中奖剧透（应仅在分支）：")
        for line in ch02_sp:
            print(line)

    bg_bad = audit_background_mismatches(data["chapters"])
    if bg_bad:
        print("警告：背景与台词不匹配：")
        for line in bg_bad[:40]:
            print(line)
        if len(bg_bad) > 40:
            print(f"  …共 {len(bg_bad)} 处")
    else:
        print("背景台词匹配检查：通过")

    xz_dis = audit_xz_disguise_after_reveal(data["chapters"])
    if xz_dis:
        raise SystemExit("第3章及以后仍含肖战伪装立绘，请检查 asset_for / SPEAKERS：\n" + "\n".join(xz_dis[:20]))

    ch02_lottery = audit_ch02_double_lottery(data["chapters"])
    if ch02_lottery:
        raise SystemExit("第2章重复中奖：\n" + "\n".join(ch02_lottery))

    forbid = audit_forbidden_dialogue(data["chapters"])
    if forbid:
        raise SystemExit("对话含禁用词（如「龚俊线」）：\n" + "\n".join(forbid[:20]))

    dup = audit_dialog_duplicates(data["chapters"])
    if dup:
        print("警告：章内台词重复：")
        for line in dup[:30]:
            print(line)
        if len(dup) > 30:
            print(f"  …共 {len(dup)} 处")
    else:
        print("章内台词重复检查：通过")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(c["beat_count"] for c in data["chapters"])
    print(f"Wrote {OUT} chapters={len(data['chapters'])} beats={total}")
    bundle = ROOT / "scripts" / "bundle_offline_data.py"
    subprocess.run([sys.executable, str(bundle)], cwd=str(ROOT), check=False)


if __name__ == "__main__":
    main()
