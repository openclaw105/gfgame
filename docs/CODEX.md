# Codex 接手文档 — 葵与星光旅人

> 工程根目录：`D:\k\GFgame`  
> 完整说明：[`../AGENTS.md`](../AGENTS.md)  
> 最后更新：2026-05-31（结局 CG 全量更新 + `bg_画作`）

## 快速启动

```powershell
cd D:\k\GFgame
python -m http.server 8787
```

## 改剧情必跑

```powershell
python scripts/generate_chapters.py
python scripts/bundle_offline_data.py
```

## 第 2 章剧情链（当前）

| 顺序 | 内容 |
|------|------|
| C1 | 买兔 / 不买 / 只拍照 |
| C2 | 刮奖：**仅买过兔** 出现本抉择（`requires_branch_tag: buy`）；未买整段跳过 |
| 主线 | 买兔后 **仅 C1 分支** 柜姐提示一次「满额抽赏去服务台」；主线 mid 不剧透兑奖 |
| 支线 | `CH02_SQ_CASHIER` 仅 `buy` 时出现（无兑奖台词） |
| 奇遇 | `CH02_ENC_GAI` 卖拐（`at: 8`，中庭） |
| C3 | 偷拍热搜选项 |
| 主线 | 侧门歇脚 → 薇薇递链接 → 对比图 → 闪回口罩「别拍」 |
| C4 | **对比图与真人一对上** 的接话（自报名 / 护里线 / 原来是你）；分支内「闪回褪去 + 侧门现身」 |
| 主线 | 正式认识 → 握手 → 往公寓走 |
| C5 | **妈来电**（握手之后；肖战退半步） |
| C6 | 章末抉择 |

**引擎标记：** `xz_reveal`、`xz_flashback_masked`；选项可带 `requires_branch_tag`（如 `buy`）。

**结构：** `CH02_MID` 14 条 + `CH02_PAD` 11 条 = 25（填满 `mid_slots_between_choices`）。`mid` 第 14 条占满 C3 前插槽，避免揭秘台词挤进 C3 之前。

## 肖战立绘速查

| 场景 | 立绘 |
|------|------|
| 第 1 章 | `???` + 伪装1 |
| 第 1–2 章画作特写 | `bg_画作` ← `背景图/画作.png`（《街角星光》） |
| 第 2 章闪回 | 肖战 + 伪装1（`xz_flashback_masked`），背景 `bg_画作` |
| 第 2 章侧门初见 | 肖战 + 一般/情绪 |
| 第 3 章+ | 正常情绪 |

## 第 6 章

仅 `bg_啤酒节` / `bg_后台走廊` / `bg_演唱会1`。`CH06_DEMO` 用后台走廊 BGM 仍为 `bgm_festival_concert`。

## 机缘卡

顶栏 ✦ → `openFatePanel()`；30 万/张；游戏菜单无兑换项。

## 校验命令

```powershell
python scripts/audit_endings.py   # 期望 10/10
python scripts/generate_chapters.py  # 期望无剧透/重复中奖/台词重复
```

## 备份

最新全量镜像：`D:\k\gameback\GFgame_20260531_endings_art_ok`

```powershell
robocopy "D:\k\GFgame" "D:\k\gameback\GFgame_YYYYMMDD_label" /MIR /MT:8 /XD node_modules .git __pycache__
```

上一版：`D:\k\gameback\GFgame_20260530_audit_ok`（审计通过，不含本次 CH02 叙事修正）

## 源文件

| 用途 | 文件 |
|------|------|
| 剧情 | `scripts/story_content.py` |
| 生成 | `scripts/generate_chapters.py` |
| 运行 | `js/engine.js`（`requires_branch_tag`、`lottery_once`+`buy`）, `js/registry.js` |
| 生成物 | `data/chapters.json`, `js/offline-data.js` |
