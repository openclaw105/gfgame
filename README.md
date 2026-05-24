# 葵与星光旅人

原创互动叙事网页游戏。素材与 `cursor_asset_manifest.json` 绑定。

**给 Codex / 自动化代理**：速查 [`docs/CODEX.md`](docs/CODEX.md)，完整说明 [`AGENTS.md`](AGENTS.md)。  
最新备份：`D:\k\gameback\GFgame_20260531_endings_art_ok`

## 运行方式

在项目根目录启动本地服务器（避免浏览器拦截 fetch 与中文路径）：

```powershell
cd D:\k\GFgame
python -m http.server 8787
```

浏览器打开：http://localhost:8787/

## 文件结构

| 路径 | 说明 |
|------|------|
| `index.html` | 入口 |
| `AGENTS.md` | Codex 工程说明（维护必读） |
| `cursor_asset_manifest.json` | 素材注册表 |
| `data/chapters.json` | 10 章剧情（生成物） |
| `scripts/story_content.py` | 剧情源 |
| `js/registry.js` | 资源加载 |
| `js/engine.js` | 引擎（金钱/机缘卡/结局/BGM） |
| `bgm/*.mp3` | 背景音乐（见 `bgm/bgm_manifest.json`） |
| `背景图/` `女角色/` `男角色/` | 立绘与场景 |

## 重新生成剧情数据

```powershell
python scripts/generate_chapters.py
python scripts/bundle_offline_data.py
```

## 操作

- 点击 **▼** 或空白推进对话
- 选项点击带音效与辉光
- 顶栏：☰ 菜单（数值、音乐）、热搜 #、微信、机缘卡 ✦（兑换/使用）、封面点击解锁 BGM
