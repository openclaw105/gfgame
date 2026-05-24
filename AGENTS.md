# 葵与星光旅人 — Codex 工程说明

> 项目根目录：`D:\k\GFgame`  
> 备份位置：`D:\k\gameback\` 下带时间戳目录（最新见下方）  
> 最后更新：2026-05-30  
> Codex 速查：[`docs/CODEX.md`](docs/CODEX.md)

## 项目是什么

原创娱乐圈乙女向 **网页视觉小说**。无构建步骤，静态资源 + Python 生成剧情 JSON。  
素材通过 `cursor_asset_manifest.json` 注册，运行时由 `js/registry.js` 加载。

## 如何运行

```powershell
cd D:\k\GFgame
python -m http.server 8787
```

浏览器打开 http://localhost:8787/ ，或双击 `启动游戏.bat`。

**必须** 用本地 HTTP 服务打开（`file://` 会导致 `fetch` / 中文路径失败）。

## 目录结构（改代码前先读）

| 路径 | 作用 |
|------|------|
| `index.html` | 入口；封面 BGM；游戏菜单仅「数值面板 / 音乐」 |
| `js/engine.js` | 主引擎：对话、选项、BGM、金钱/机缘卡、结局、微信/热搜 |
| `js/app.js` | UI 绑定；封面点击 `userGesture` 解锁 BGM |
| `js/registry.js` | 素材与 BGM；`ASSET_CACHE_BUST` 改资源后递增 |
| `js/offline-data.js` | **生成物**，勿手改 |
| `data/chapters.json` | **生成物**，10 章节拍与分支 |
| `scripts/story_content.py` | **剧情源**（含 `CH02_PAD` 等 pad 池） |
| `scripts/generate_chapters.py` | 生成 + 剧透/重复/金钱校验 |
| `scripts/bundle_offline_data.py` | 打包 offline-data.js |
| `scripts/audit_endings.py` | 10 结局可达性 + 金钱估算 |

`bgm/backup_*` 为历史备份，**不要** 在运行时引用。

## 常用维护命令

```powershell
cd D:\k\GFgame

python scripts/generate_chapters.py
python scripts/bundle_offline_data.py
python scripts/audit_endings.py
```

改 BGM / 立绘 / 背景后：递增 `ASSET_CACHE_BUST`（当前 `20260531a`），并同步 `index.html` 封面 `?v=`。新背景：`python scripts/register_background.py`；结局 CG：`python scripts/refresh_endings.py`。

## 剧情与玩法约定（勿破坏）

1. **对话**：禁止游戏化用语（如「龚俊线」「跟薇薇线」）；「对线」仅指网络骂战语境。
2. **肖战身份**  
   - 第 1 章：`???` + `char_肖战_伪装1`  
   - 第 2 章：`CH02_C3` 后热搜揭秘 → 闪回 `xz_flashback_masked` → `CH02_C4` 侧门真人现身与接话 → 正式认识/握手 → `CH02_C5` 妈来电  
   - 第 3 章起：正常肖战立绘  
3. **第 2 章结构**：`mid` + `pad` 合计须 **25 条**（`mid_slots_between_choices`）；揭秘/初见写在 `CH02_PAD`，从 C3 之后顺序注入。  
4. **第 2 章金钱**：主线无兑奖/三十万剧透；买兔后柜姐在 **C1 分支** 提示一次；`CH02_C2` 整段需 `buy`（未买跳过）；三十万仅刮票分支 `lottery_once`。  
5. **第 6 章背景**：仅啤酒节/后台/演唱会；无画室。画室从第 7 章起。  
6. **机缘卡**：仅顶栏 ✦ 面板兑换；菜单无兑换项。  
7. **封面 BGM**：单路径 `playCoverBgm`，勿多路 `play()`。

## 剧情校验（generate 自动跑）

| 检查 | 说明 |
|------|------|
| `audit_ch02_main_spoilers` | 主线无刮票剧透词 |
| `audit_ch02_double_lottery` | 三十万仅一处 |
| `audit_dialog_duplicates` | 章内同说话人+同台词不重复 |
| 微博台号匹配 / 重复 | 热搜词条规范 |
| `audit_endings.py` | 10/10 结局可达 |

## 金钱与机缘卡

见 `engine.js`：`exchangeMoneyForChanceCard`、`openFatePanel`、`checkMoneyFateBeforeEnding`。贪心路径终局约 136 万。

## 备份

```powershell
robocopy "D:\k\GFgame" "D:\k\gameback\GFgame_20260531_endings_art_ok" /MIR /MT:8
```

## 接手检查清单

1. `python scripts/generate_chapters.py` 无报错，台词重复检查通过  
2. `python scripts/audit_endings.py` → 10/10  
3. 浏览器 Ctrl+F5  
4. 第 2 章：未买兔跳过 C2 兑奖与柜姐支线；买兔仅 C1 分支提示兑奖一次  
