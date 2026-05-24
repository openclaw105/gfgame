/**
 * 从 cursor_asset_manifest.json 构建资源注册表
 */
const ASSET_CACHE_BUST = "20260524a";

class AssetRegistry {
  constructor() {
    this.manifest = null;
    this.byKey = new Map();
    this.bgmByKey = new Map();
    this.endings = new Map();
  }

  /** 从 asset_key 提取角色名，用于去重 */
  charNameFromKey(assetKey) {
    if (!assetKey) return null;
    if (assetKey.startsWith("npc_")) {
      const item = this.byKey.get(assetKey);
      return item?.character || assetKey.slice(4);
    }
    if (!assetKey.startsWith("char_")) return null;
    const parts = assetKey.split("_");
    return parts.length >= 2 ? parts[1] : null;
  }

  npcAssetKey(displayName) {
    const alias = {
      卖草莓阿姨: "刘哥",
      柜姐: "柜姐1",
    };
    const name = alias[displayName] || displayName;
    const tries = [`npc_${name}`, `npc_${displayName}`];
    for (const k of tries) {
      if (this.byKey.has(k)) return k;
    }
    return null;
  }

  applyManifest(manifest) {
    this.manifest = manifest;
    this.byKey.clear();
    this.bgmByKey.clear();
    this.endings.clear();
    (manifest.cursor_index || []).forEach((item) => {
      if (item.active !== false) this.byKey.set(item.asset_key, item);
    });
    (manifest.bgm_manifest || []).forEach((b) => {
      this.bgmByKey.set(b.id, b);
    });
    this.indexEndings(manifest);
    return this;
  }

  /** 结局名（含/不含顿号）与 manifest 条目对齐 */
  indexEndings(manifest) {
    this.endings.clear();
    const add = (name, item) => {
      if (!name || !item) return;
      this.endings.set(name, item);
      this.endings.set(name.replace(/，/g, ""), item);
    };
    (manifest.planning_from_md?.ending_cg_mapping || []).forEach((e) => {
      add(e.ending, e);
    });
    (manifest.assets_by_category?.ending_cg || []).forEach((e) => {
      add(e.md_mapping?.ending, e);
      const title = (e.name || "").replace(/^《|》$/g, "");
      add(title, e);
    });
    (manifest.cursor_index || []).forEach((item) => {
      if (item.type !== "ending_cg" && !String(item.asset_key || "").startsWith("ending_")) return;
      add(item.md_mapping?.ending, item);
      const title = (item.name || "").replace(/^《|》$/g, "");
      add(title, item);
    });
  }

  endingImageSrc(displayKey) {
    if (!displayKey) return null;
    const tries = [
      displayKey,
      displayKey.replace(/，/g, ""),
      `ending_《${displayKey}》`,
      `结局/《${displayKey}》.png`,
    ];
    for (const t of tries) {
      const hit = this.endings.get(t) || this.byKey.get(t);
      const path = hit?.web_path || hit?.rel_path;
      if (path) return `${encodeURI(path)}?v=${ASSET_CACHE_BUST}`;
    }
    for (const item of this.endings.values()) {
      const md = item.md_mapping?.ending || item.ending;
      if (!md) continue;
      if (md === displayKey || md === displayKey.replace(/，/g, "")) {
        const path = item.web_path || item.rel_path;
        if (path) return `${encodeURI(path)}?v=${ASSET_CACHE_BUST}`;
      }
    }
    return `${encodeURI(`结局/《${displayKey}》.png`)}?v=${ASSET_CACHE_BUST}`;
  }

  async load(url = "cursor_asset_manifest.json") {
    if (window.__KUI_STAR_OFFLINE__?.manifest) {
      return this.applyManifest(window.__KUI_STAR_OFFLINE__.manifest);
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error("无法加载 cursor_asset_manifest.json");
    return this.applyManifest(await res.json());
  }

  loadFromObject(manifest) {
    return this.applyManifest(manifest);
  }

  webPath(assetKey) {
    const item = this.byKey.get(assetKey);
    if (!item) return null;
    return encodeURI(item.web_path || item.rel_path);
  }

  bgmPath(bgmKey) {
    const b = this.bgmByKey.get(bgmKey);
    if (!b?.file) return null;
    return `${encodeURI(b.file)}?v=${ASSET_CACHE_BUST}`;
  }

  charAsset(character, emotion) {
    const key = `char_${character}_${emotion}`;
    if (this.byKey.has(key)) return key;
    const alt = `char_${character}_开心`;
    return this.byKey.has(alt) ? alt : null;
  }

  defaultAssetKey(charName, preferKeys = []) {
    const npcKey = this.npcAssetKey(charName);
    if (npcKey) return npcKey;
    for (const emo of preferKeys) {
      const k = `char_${charName}_${emo}`;
      if (this.byKey.has(k)) return k;
    }
    for (const emo of ["开心", "一般", "害羞", "悲伤", "疲惫", "无语"]) {
      const k = `char_${charName}_${emo}`;
      if (this.byKey.has(k)) return k;
    }
    return null;
  }

  resolveCharacters(list) {
    if (!list?.length) return [];
    const seen = new Set();
    const out = [];
    for (const c of list) {
      const key =
        c.asset_key ||
        (c.character && c.emotion ? `char_${c.character}_${c.emotion}` : null) ||
        (c.name ? this.defaultAssetKey(c.name) : null);
      const charName = key?.startsWith("npc_")
        ? this.byKey.get(key)?.character || key.slice(4)
        : this.charNameFromKey(key);
      if (charName && seen.has(charName)) continue;
      if (charName) seen.add(charName);
      let item = key ? this.byKey.get(key) : null;
      if (!item && key) {
        if (key.startsWith("npc_")) {
          item = this.byKey.get(key);
        } else {
          const base = key.replace(/_[^_]+$/, "");
          item =
            this.byKey.get(`${base}_开心`) ||
            this.byKey.get(`${base}_一般`) ||
            this.byKey.get(`${base}_害羞`);
        }
      }
      const web = item ? item.web_path : null;
      const src = web ? `${encodeURI(web)}?v=${ASSET_CACHE_BUST}` : null;
      out.push({
        asset_key: key,
        src,
        layout: c.layout || "center",
        sizeClass: c.sizeClass || this.sizeClassFor(charName, c.layout, key),
        name: c.name || charName || "",
      });
    }
    return out;
  }

  /** 奇遇 NPC（卖拐/三轮/黄哥/刘哥）在现有体型上再 ×120% */
  sizeClassFor(charName, layout, assetKey) {
    const npcLarge = new Set(["卖拐大叔", "三轮大叔", "黄哥", "刘哥", "卖草莓阿姨"]);
    if (npcLarge.has(charName) || (assetKey && /npc_(卖拐大叔|三轮大叔|黄哥|刘哥)/.test(assetKey))) {
      return "size-npc-large";
    }
    if (charName === "肖战" && assetKey && /肖战_伪装/.test(assetKey)) {
      return "size-xz-disguise";
    }
    if (charName === "肖战") {
      if (layout === "speaker-right") return "size-xz-right";
      return "size-default";
    }
    if (charName === "葵" || charName === "薇薇") return "size-heroine";
    if (layout === "speaker-right") return "size-heroine";
    return "size-default";
  }

  /** 根据台词推断立绘情绪（beats 未写 asset_key 时的兜底） */
  inferEmotionFromText(text, chapterNum = 99) {
    const t = String(text || "");
    if (/跳舞|起舞|舞步/.test(t)) return "跳舞";
    if (chapterNum < 3 && /伪装|口罩|帽子|墨镜|狗仔/.test(t)) return "伪装1";
    if (/哭|泪|难过|心碎|抱歉|对不起|失望|离别|再见/.test(t)) return "悲伤";
    if (/怒|气死|烦死|滚|讨厌你|混蛋/.test(t)) return "生气";
    if (/担心|没事吧|别怕|小心|受伤/.test(t)) return "担心";
    if (/累|困|熬夜|疲惫|打哈欠/.test(t)) return "疲惫";
    if (/害羞|脸红|不好意思|支支吾吾/.test(t)) return "害羞";
    if (/惊|哇|天啊|不会吧|愣/.test(t)) return "惊讶";
    if (/沉思|想想|沉默|良久/.test(t)) return "沉思";
    if (/笑|哈|开心|太好了|棒|谢|喜欢/.test(t)) return "开心";
    if (/无语|……|\.\.\./.test(t)) return "无语";
    return "一般";
  }

  xzIdentityRevealed(beat, chapterNum, state) {
    if (state?.xz_identity_revealed) return true;
    if (chapterNum >= 3) return true;
    if (beat?.xz_flashback_masked) return false;
    if (beat?.xz_reveal) return true;
    const t = beat?.text || "";
    return /摘下|摘掉|露出脸|真面目|我是肖战|原来是你|认出来|摘下口罩|原来叫肖战|原来他叫肖战|真的是肖战|真的是他|画展陌生人|顶流私服|卸了伪装|当普通观众|不是来营业/.test(
      t
    );
  }

  assetKeyForSpeaker(speaker, beat, chapterNum, state) {
    if (!speaker || speaker === "narrator") return null;
    const npcKey = this.npcAssetKey(speaker);
    if (npcKey) return npcKey;
    if (speaker === "肖战" && beat?.muscle_sprite) {
      return this.charAsset("肖战", "肌肉") || "char_肖战_肌肉";
    }
    if (speaker === "肖战" && beat?.xz_flashback_masked) {
      return this.charAsset("肖战", "伪装1") || "char_肖战_伪装1";
    }
    if (
      speaker === "肖战" &&
      chapterNum < 3 &&
      !this.xzIdentityRevealed(beat, chapterNum, state)
    ) {
      return this.charAsset("肖战", "伪装1") || "char_肖战_伪装1";
    }
    const raw = beat?.characters || [];
    const fromBeat = raw.find((c) => this.charNameFromKey(c.asset_key) === speaker);
    if (fromBeat?.asset_key) return fromBeat.asset_key;
    if (speaker === "张艺兴" && /跳舞|起舞|舞步/.test(beat?.text || "")) {
      return this.charAsset("张艺兴", "跳舞") || this.defaultAssetKey("张艺兴");
    }
    const emo = this.inferEmotionFromText(beat?.text, chapterNum);
    return this.charAsset(speaker, emo) || this.defaultAssetKey(speaker);
  }

  /** 立绘底边辉光色（仅人物脚下） */
  glowColorFor(charName) {
    const map = {
      葵: "rgba(232, 180, 220, 0.72)",
      肖战: "rgba(240, 200, 120, 0.78)",
      薇薇: "rgba(255, 160, 200, 0.7)",
      宋威龙: "rgba(120, 200, 255, 0.72)",
      张艺兴: "rgba(180, 140, 255, 0.75)",
      李昀锐: "rgba(100, 220, 200, 0.72)",
      龚俊: "rgba(120, 230, 160, 0.72)",
      孟子义: "rgba(255, 180, 140, 0.7)",
      赵今麦: "rgba(255, 220, 130, 0.7)",
      鞠婧祎: "rgba(255, 120, 180, 0.72)",
      张婧仪: "rgba(255, 190, 160, 0.72)",
      卢昱晓: "rgba(160, 230, 210, 0.72)",
      刘哥: "rgba(200, 200, 220, 0.55)",
      三轮大叔: "rgba(200, 180, 140, 0.5)",
      卖拐大叔: "rgba(180, 200, 160, 0.5)",
      黄哥: "rgba(255, 160, 90, 0.72)",
      卖拐大叔: "rgba(180, 200, 160, 0.55)",
      柜姐1: "rgba(255, 200, 160, 0.65)",
      柜姐2: "rgba(255, 190, 150, 0.65)",
      柜姐: "rgba(255, 200, 160, 0.65)",
      卖草莓阿姨: "rgba(255, 140, 180, 0.7)",
    };
    return map[charName] || "rgba(220, 200, 240, 0.55)";
  }
}

window.AssetRegistry = AssetRegistry;
