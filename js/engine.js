/** 封面与结局共用的循环 BGM（由 音频1.mp4 提取，音量对齐 scene BGM） */
const COVER_ENDING_BGM = "bgm_title_ending";
const COVER_ENDING_BGM_FILE = "bgm/bgm_10_title_ending.mp3";
const BGM_CACHE_BUST = "20260520d";
const BGM_VOLUME = 0.32;
const COVER_BGM_FADE_MS = 1500;

function resolveAudioUrl(src) {
  try {
    return new URL(src, location.href).href;
  } catch {
    return src;
  }
}

function audioPathname(srcOrUrl) {
  try {
    return new URL(srcOrUrl, location.href).pathname;
  } catch {
    return srcOrUrl;
  }
}

function audioMatchesSrc(audio, src) {
  if (!audio || !src) return false;
  const abs = resolveAudioUrl(src);
  if (audio.dataset.srcAbs === abs || audio.src === abs) return true;
  if (!audio.src) return false;
  return audioPathname(audio.src) === audioPathname(abs);
}

/**
 * 葵与星光旅人 — 主引擎
 */
class StarlightEngine {
  constructor(registry) {
    this.registry = registry;
    this.chapters = null;
    this.chapterIndex = 0;
    this.beatIndex = 0;
    this.branchQueue = [];
    this.displayBeat = null;
    this.branchActive = false;
    this.state = this.defaultState();
    this.bgmAudio = null;
    this.soundOn = true;
    this._currentBgKey = null;
    this._charSig = "";
    this._bgmFadeRaf = 0;
    this._lastBgmKey = null;
    this._seenChapterOpenings = new Set();
    this._chapterOpeningTimer = 0;
    this.els = {};
    /** 顺序敏感：先判定专精/坏结局，再 HE；阈值对齐剧情单周目可叠数值 */
    this.ENDINGS = [
      { key: "与钱有缘，与命相逢", test: (s) => s.money_fate_used },
      {
        key: "展灯熄后，无人归来",
        test: (s) => s.misunderstanding >= 30 && s.vv_friend <= 42 && s.xz_love < 58,
      },
      {
        key: "听见月光在起舞",
        test: (s) =>
          s.zyx_dance_seen &&
          s.zyx_love >= 18 &&
          s.zyx_love >= s.swl_love + 2 &&
          s.zyx_love + 3 >= s.xz_love &&
          s.art_value < 80,
      },
      {
        key: "最后一班地铁开向冬夜",
        test: (s) =>
          s.swl_love >= 32 &&
          s.swl_love > s.xz_love &&
          s.swl_love < 44 &&
          s.xz_trust < 42 &&
          s.xz_love < 52,
      },
      {
        key: "风从片场吹来",
        test: (s) => s.swl_love >= 40 && s.swl_love >= s.xz_love + 8 && s.xz_love < 58,
      },
      {
        key: "爱与梦想终将圆满",
        test: (s) =>
          s.xz_love >= 58 &&
          s.xz_trust >= 55 &&
          s.vv_gj >= 48 &&
          s.vv_friend >= 48 &&
          s.misunderstanding <= 42,
      },
      { key: "花开两岸，人间重逢", test: (s) => s.vv_friend >= 55 && s.vv_gj >= 36 && s.xz_love < 62 },
      {
        key: "画框之外，万物生长",
        test: (s) =>
          s.art_value >= 72 && s.xz_love < 55 && s.swl_love < 50 && s.zyx_love < 38,
      },
      {
        key: "星光落在展灯边",
        test: (s) =>
          s.xz_love >= 65 &&
          s.xz_trust >= 60 &&
          s.misunderstanding <= 45 &&
          (s.vv_gj < 48 || s.vv_friend < 50),
      },
      {
        key: "灯火两端，旧梦不言",
        test: (s) =>
          s.public_opinion >= 50 &&
          s.art_value < 52 &&
          s.xz_love < 55 &&
          s.swl_love < 42,
      },
    ];
    this.ENDING_ROUTES = {
      money: {
        key: "与钱有缘，与命相逢",
        tags: ["buy", "cash", "money", "save", "win"],
        opportunities: 7,
        offset: 0.6,
      },
      bad: {
        key: "展灯熄后，无人归来",
        tags: ["cold", "solo", "leave", "cool"],
        opportunities: 23,
        offset: -0.25,
      },
      zyx: {
        key: "听见月光在起舞",
        tags: ["zyx", "reject"],
        opportunities: 5,
        offset: 0,
      },
      metro: {
        key: "最后一班地铁开向冬夜",
        tags: ["lyr", "walk", "bike"],
        opportunities: 9,
        offset: 0,
      },
      swl: {
        key: "风从片场吹来",
        tags: ["swl", "trio", "p", "wear", "self"],
        opportunities: 11,
        offset: 0.4,
      },
      he: {
        key: "爱与梦想终将圆满",
        tags: ["he", "trust", "kind", "home"],
        opportunities: 14,
        offset: -0.15,
      },
      vv: {
        key: "花开两岸，人间重逢",
        tags: ["vv", "gj"],
        opportunities: 37,
        offset: 0,
      },
      art: {
        key: "画框之外，万物生长",
        tags: ["art", "zjy", "rest", "work", "health"],
        opportunities: 31,
        offset: -0.25,
      },
      xz: {
        key: "星光落在展灯边",
        tags: ["xz", "meet", "guard", "shy"],
        opportunities: 32,
        offset: 0,
      },
      public: {
        key: "灯火两端，旧梦不言",
        tags: ["heat", "pic", "sell", "eat", "scam", "grab", "help"],
        opportunities: 18,
        offset: 0,
      },
    };
  }

  defaultState() {
    return {
      chapter: 1,
      money: 20,
      money_peak: 20,
      next_card_prompt: 30,
      chance_card: 0,
      chance_card_used: 0,
      xz_love: 10,
      xz_trust: 10,
      swl_love: 0,
      zyx_love: 0,
      lyr_love: 0,
      gj_love: 0,
      vv_friend: 30,
      vv_gj: 0,
      public_opinion: 10,
      art_value: 20,
      misunderstanding: 0,
      kindness: 0,
      bad_karma: 0,
      titles: [],
      branch_history: [],
      branch_tags: {},
      reject_demo_count: 0,
      zyx_dance_seen: false,
      money_fate_used: false,
      hotTopics: [],
      female_bestie: {},
      xz_identity_revealed: false,
      wechat: [],
      wechatSynced: 0,
      wechatFlags: {},
    };
  }

  static WECHAT_TIMELINE = [
    {
      chapter: 1,
      msgs: [
        { from: "薇薇", text: "姐妹！巴黎画展那个戴口罩的……像不像顶流？" },
        { from: "葵", text: "别瞎猜，我就是来逛展的。" },
        { from: "薇薇", text: "拍张照发我！我要做表情包。" },
      ],
    },
    {
      chapter: 2,
      msgs: [
        { from: "薇薇", text: "今晚商场见，兔玩偶给你留着。" },
        { from: "葵", text: "十点半前回，还得修画。" },
        { from: "薇薇", text: "服务台那边排队好长，你记得把小票攥牢。" },
      ],
    },
    {
      chapter: 3,
      msgs: [
        { from: "薇薇", text: "肖战那场布场，你跟我盯物料。" },
        { from: "龚俊", text: "葵老师好，流程表发你了，有不懂随时问。" },
        { from: "薇薇", text: "龚俊人挺稳的诶……先别多想，干活。" },
      ],
    },
    {
      chapter: 4,
      msgs: [
        { from: "薇薇", text: "会所局我只去一小时，你别画太晚。" },
        { from: "葵", text: "嗯，蹭饭就撤。" },
        { from: "肖战", text: "（未读）今晚别硬撑，早点回。" },
      ],
    },
    {
      chapter: 5,
      msgs: [
        { from: "薇薇", text: "肌肉衣热搜爆了……你别下场评论。" },
        { from: "葵", text: "我戴耳机，听不见。" },
        { from: "宋威龙", text: "速写本我收好了，画得真好。" },
      ],
    },
    {
      chapter: 6,
      msgs: [
        { from: "张艺兴", text: "DEMO 发你了，耳机戴好再听。" },
        { from: "薇薇", text: "啤酒节后台别乱跑，我找不着你会急。" },
        { from: "肖战", text: "累了就说，别一个人扛。" },
      ],
    },
    {
      chapter: 7,
      msgs: [
        { from: "肖战", text: "到家说一声。" },
        { from: "李昀锐", text: "外套记得还我，别客气。" },
        { from: "薇薇", text: "宵夜还吃吗？龚俊问要不要一起。" },
      ],
    },
    {
      chapter: 8,
      msgs: [
        { from: "薇薇", text: "龚俊刚才敬我酒……手都在抖哈哈。" },
        { from: "葵", text: "你慢点喝，我帮你挡一杯。" },
        { from: "龚俊", text: "薇薇，散场我送你，车已叫好。" },
        { from: "薇薇", text: "（语音 12″）葵你说，他是不是有点意思？" },
      ],
    },
    {
      chapter: 9,
      msgs: [
        { from: "薇薇", text: "樱花公园布展，你把龚俊微信推我干嘛！" },
        { from: "葵", text: "你说想认真了解，我就推了。" },
        { from: "龚俊", text: "谢谢葵老师。薇薇，明天一起对流程？" },
        { from: "肖战", text: "旧预览册放你椅背上了，里面夹着展签。" },
      ],
    },
    {
      chapter: 10,
      msgs: [
        { from: "薇薇", text: "我和龚俊在一起了！！！姐妹你要当伴娘吗！" },
        { from: "龚俊", text: "葵，谢谢你。我们会好好对薇薇。" },
        { from: "肖战", text: "展后有空吗？想认真跟你把话说完。" },
        { from: "葵", text: "好。你们幸福，我就安心画画。" },
      ],
    },
  ];

  bindDom() {
    const ids = [
      "bg", "stage", "speakerName", "dialogueText", "choiceWrap", "chapterNum", "chapterTitle",
      "choicePanelLabel",
      "statsPanel", "hotPanel", "hotList", "phonePanel", "chatList", "startScreen",
      "gameUi", "endingScreen", "modalRoot", "flashOverlay", "beatProgress",
      "chapterCurtain", "chapterCurtainNum", "chapterCurtainTitle",
      "dialogueBox", "dialogueDock",
    ];
    ids.forEach((id) => {
      this.els[id] = document.getElementById(id);
    });
  }

  async init() {
    this.bindDom();
    this.bindLayoutSync();
    let chRes = window.__KUI_STAR_OFFLINE__?.chapters;
    if (!chRes) {
      const res = await fetch("data/chapters.json");
      if (!res.ok) throw new Error("无法加载 data/chapters.json");
      chRes = await res.json();
    }
    this.chaptersData = chRes;
    this.chapters = chRes.chapters;
  }

  clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  static EFFECT_ZH = {
    money: "金钱",
    chance_card: "机缘卡",
    xz_love: "肖战好感",
    xz_trust: "肖战信任",
    swl_love: "宋威龙好感",
    zyx_love: "张艺兴好感",
    lyr_love: "李昀锐好感",
    gj_love: "龚俊好感",
    vv_friend: "薇薇羁绊",
    vv_gj: "薇薇×龚俊",
    public_opinion: "舆论",
    art_value: "艺术值",
    misunderstanding: "误会",
    kindness: "善意",
    bad_karma: "缺德",
  };

  formatEffectToast(eff) {
    if (!eff) return "";
    const skip = new Set([
      "branch_tag",
      "flag",
      "title",
      "swl_night",
      "money_set",
      "zyx_dance_seen",
      "lottery_once",
    ]);
    const parts = [];
    for (const [k, v] of Object.entries(eff)) {
      if (skip.has(k) || typeof v !== "number") continue;
      const label = StarlightEngine.EFFECT_ZH[k];
      if (!label) continue;
      parts.push(`${label}${v > 0 ? "＋" : "－"}${Math.abs(v)}`);
    }
    return parts.join("　");
  }

  /** 选项点击时只应用非金钱效果；金钱在剧情台词 beat.effects 中结算 */
  effectsWithoutMoney(eff) {
    if (!eff) return null;
    const out = { ...eff };
    delete out.money;
    delete out.money_set;
    return Object.keys(out).length ? out : null;
  }

  applyEffects(eff) {
    if (!eff) return;
    const s = this.state;
    const num = (k, v, lo = 0, hi = 100) => {
      if (s[k] === undefined) return;
      s[k] = this.clamp(s[k] + v, lo, hi);
    };
    if (eff.money_set !== undefined) {
      s.money = Math.max(0, eff.money_set);
      s.money_peak = Math.max(s.money_peak, s.money);
      this.toast(`金钱已变为 ${s.money} 万`);
    } else if (eff.money) {
      let delta = eff.money;
      if (eff.lottery_once) {
        if (!s.branch_tags.buy) {
          delta = 0;
          this.toast("没有兔玩偶满额发票，无法兑这笔奖");
        } else if (s.branch_tags.ch02_lottery) {
          delta = 0;
        } else {
          s.branch_tags.ch02_lottery = 1;
          this.pushChat("薇薇", "姐妹！！发票三十万！！！我来了！！！", false);
        }
      }
      if (delta) {
        s.money = Math.max(0, s.money + delta);
        s.money_peak = Math.max(s.money_peak, s.money);
        const sign = delta > 0 ? "＋" : "－";
        this.toast(`金钱${sign}${Math.abs(delta)}万（现 ${s.money} 万）`);
        this.checkMoneyPrompt();
      } else if (eff.lottery_once) {
        this.toast("这笔奖金已经入账了");
      }
    }
    if (eff.chance_card) {
      if (eff.chance_card < 0 && s.chance_card <= 0) return;
      s.chance_card = Math.max(0, s.chance_card + eff.chance_card);
      if (eff.chance_card < 0) s.chance_card_used += 1;
    }
    num("xz_love", eff.xz_love || 0);
    num("xz_trust", eff.xz_trust || 0);
    num("swl_love", eff.swl_love || 0);
    num("zyx_love", eff.zyx_love || 0);
    num("lyr_love", eff.lyr_love || 0);
    num("gj_love", eff.gj_love || 0);
    num("vv_friend", eff.vv_friend || 0, -100, 100);
    num("vv_gj", eff.vv_gj || 0);
    num("public_opinion", eff.public_opinion || 0);
    num("art_value", eff.art_value || 0);
    num("misunderstanding", eff.misunderstanding || 0);
    num("kindness", eff.kindness || 0);
    num("bad_karma", eff.bad_karma || 0);
    if (eff.title && !s.titles.includes(eff.title)) {
      s.titles.push(eff.title);
      this.toast(`🏅 获得称号：「${eff.title}」`);
    }
    if ((typeof eff.vv_gj === "number" && eff.vv_gj >= 6) || s.vv_gj >= 55) {
      if (!this.state.wechatFlags?.vv_gj_ping) {
        this.pushChat("薇薇", "龚俊对我好像真有意思……", false);
        this.state.wechatFlags = this.state.wechatFlags || {};
        this.state.wechatFlags.vv_gj_ping = true;
      }
    }
    if (eff.zyx_dance_seen) s.zyx_dance_seen = true;
    if (typeof eff.reject_demo_count === "number") {
      s.reject_demo_count = this.clamp(s.reject_demo_count + eff.reject_demo_count, 0, 99);
    }
    if (eff.branch_tag) {
      s.branch_tags[eff.branch_tag] = (s.branch_tags[eff.branch_tag] || 0) + 1;
    }
    return this.formatEffectToast(eff);
  }

  exchangeMoneyForChanceCard(silent = false) {
    const s = this.state;
    if (s.money < 30) {
      if (!silent) this.toast(`兑换机缘卡需要 30 万（当前 ${s.money} 万）`);
      return false;
    }
    s.money -= 30;
    s.money_peak = Math.max(s.money_peak, s.money);
    s.chance_card += 1;
    while (s.money >= s.next_card_prompt) {
      s.next_card_prompt += 30;
    }
    if (!silent) this.toast(`花费 30 万，获得机缘卡 ×1（现 ${s.chance_card} 张）`);
    this.renderStats();
    this.save();
    return true;
  }

  checkMoneyPrompt() {
    const s = this.state;
    while (s.money >= s.next_card_prompt) {
      const threshold = s.next_card_prompt;
      s.next_card_prompt += 30;
      this.showModal("机缘卡兑换", `存款已达 ${threshold} 万。是否花费 30 万兑换 1 张机缘卡？`, [
        { text: "兑换", action: () => this.exchangeMoneyForChanceCard() },
        { text: "暂不兑换", action: () => {} },
      ]);
    }
  }

  toast(msg) {
    if (!this.els.modalRoot) return;
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    this.els.modalRoot.appendChild(el);
    setTimeout(() => el.remove(), 2200);
  }

  showModal(title, body, buttons) {
    const wrap = document.createElement("div");
    wrap.className = "modal-mask";
    wrap.innerHTML = `<div class="modal-card"><h3>${title}</h3><p>${body}</p><div class="modal-actions"></div></div>`;
    const actions = wrap.querySelector(".modal-actions");
    buttons.forEach((b) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-btn";
      btn.textContent = b.text;
      btn.addEventListener("click", () => {
        b.action?.();
        wrap.remove();
        this.renderStats();
        this.save();
      });
      actions.appendChild(btn);
    });
    this.els.modalRoot.appendChild(wrap);
  }

  resolveBgmSrc(key) {
    if (!key) return null;
    let src = this.registry?.bgmPath(key);
    if (!src && key === COVER_ENDING_BGM) {
      src = `${encodeURI(COVER_ENDING_BGM_FILE)}?v=${BGM_CACHE_BUST}`;
    }
    return src;
  }

  ensureBgmAudio() {
    if (this.bgmAudio) return this.bgmAudio;
    const prefetch = document.getElementById("coverBgmPrefetch");
    this.bgmAudio = prefetch || new Audio();
    this.bgmAudio.loop = true;
    this.bgmAudio.volume = BGM_VOLUME;
    if (!this.bgmAudio.preload) this.bgmAudio.preload = "auto";
    return this.bgmAudio;
  }

  setBgmSrc(src) {
    if (!src) return;
    const a = this.ensureBgmAudio();
    const abs = resolveAudioUrl(src);
    if (audioMatchesSrc(a, src)) {
      a.dataset.srcAbs = abs;
      return;
    }
    a.dataset.srcAbs = abs;
    a.src = src;
    a.load();
  }

  _cancelBgmFade() {
    if (this._bgmFadeRaf) {
      cancelAnimationFrame(this._bgmFadeRaf);
      this._bgmFadeRaf = 0;
    }
  }

  /** 封面/结局 BGM 从 0 淡入到目标音量 */
  _fadeInCoverBgm(a) {
    if (!a || !this.soundOn) return;
    this._cancelBgmFade();
    const target = BGM_VOLUME;
    const from = 0;
    a.volume = from;
    const t0 = performance.now();
    const tick = (now) => {
      if (!this.bgmAudio || this.bgmAudio !== a || a.paused) {
        this._bgmFadeRaf = 0;
        return;
      }
      const t = Math.min(1, (now - t0) / COVER_BGM_FADE_MS);
      a.volume = from + (target - from) * t;
      if (t < 1) {
        this._bgmFadeRaf = requestAnimationFrame(tick);
      } else {
        a.volume = target;
        this._bgmFadeRaf = 0;
      }
    };
    this._bgmFadeRaf = requestAnimationFrame(tick);
  }

  _onCoverBgmStarted(a, { fadeIn = true } = {}) {
    if (!a) return;
    a.muted = false;
    if (fadeIn && this.isCoverOrEndingScreen()) {
      this._fadeInCoverBgm(a);
    } else {
      this._cancelBgmFade();
      a.volume = BGM_VOLUME;
    }
  }

  playBgm(key, opts = {}) {
    const force = !!opts.force;
    if (!this.soundOn || !key) return;
    if (key === COVER_ENDING_BGM && this.isCoverOrEndingScreen()) {
      this.playCoverBgm();
      return;
    }
    const src = this.resolveBgmSrc(key);
    if (!src) {
      console.warn("[BGM] 未找到:", key);
      return;
    }
    const a = this.ensureBgmAudio();
    if (!force && a.dataset.key === key && audioMatchesSrc(a, src) && !a.paused) {
      return;
    }
    this._cancelBgmFade();
    a.dataset.key = key;
    this._lastBgmKey = key;
    a.loop = true;
    a.volume = BGM_VOLUME;
    if (!audioMatchesSrc(a, src)) this.setBgmSrc(src);
    this._attemptBgmPlay(key);
  }

  _attemptBgmPlay(key) {
    if (!this.bgmAudio) return;
    const a = this.bgmAudio;
    const tryPlay = () => {
      if (!a.paused) return;
      const p = a.play();
      if (!p?.catch) return;
      p.catch(() => {});
    };
    tryPlay();
    if (a.paused && a.readyState < 3) {
      a.addEventListener("canplay", tryPlay, { once: true });
    }
  }

  isCoverOrEndingScreen() {
    const start = this.els.startScreen || document.getElementById("startScreen");
    const ending = this.els.endingScreen || document.getElementById("endingScreen");
    const onStart = start && !start.classList.contains("hidden");
    const onEnding = ending && !ending.classList.contains("hidden");
    return onStart || onEnding || document.body.classList.contains("ending-active");
  }

  primeCoverBgm() {
    const src = this.resolveBgmSrc(COVER_ENDING_BGM);
    if (!src) return;
    this.setBgmSrc(src);
  }

  /** 封面/结局 BGM：加载时静音试播；用户点击封面后取消静音并 1.5s 淡入（单路径，不叠播） */
  playCoverBgm(opts = {}) {
    const userGesture = !!opts.userGesture;
    if (!this.soundOn || !this.isCoverOrEndingScreen()) return;
    const a = this.ensureBgmAudio();
    this.primeCoverBgm();
    a.dataset.key = COVER_ENDING_BGM;
    this._lastBgmKey = COVER_ENDING_BGM;
    a.loop = true;

    const begin = () => {
      if (!this.soundOn || !this.isCoverOrEndingScreen()) return;

      if (!a.paused) {
        if (!userGesture) return;
        if (!a.muted && a.volume >= BGM_VOLUME * 0.9 && !this._bgmFadeRaf) return;
        this._onCoverBgmStarted(a, { fadeIn: true });
        return;
      }

      const afterPlay = () => {
        if (!this.soundOn || !this.isCoverOrEndingScreen()) return;
        if (userGesture) {
          this._onCoverBgmStarted(a, { fadeIn: true });
        }
      };

      if (userGesture) {
        a.muted = false;
        a.volume = 0;
        const p = a.play();
        if (p?.then) p.then(afterPlay).catch(() => {});
        else afterPlay();
        return;
      }

      a.muted = true;
      a.volume = 0;
      const p = a.play();
      if (p?.catch) p.catch(() => {});
    };

    if (a.readyState >= 2) begin();
    else a.addEventListener("canplay", begin, { once: true });
  }

  autoplayCoverBgm() {
    this.playCoverBgm();
  }

  stopBgm() {
    this._cancelBgmFade();
    if (!this.bgmAudio) return;
    this.bgmAudio.pause();
  }

  /** 重新打开音乐时恢复当前场景 BGM */
  toggleSound() {
    this.soundOn = !this.soundOn;
    if (!this.soundOn) this.stopBgm();
    else this.resumeBgm();
    return this.soundOn;
  }

  resumeBgm() {
    if (!this.soundOn) return;
    if (this.isCoverOrEndingScreen()) {
      this.autoplayCoverBgm();
      return;
    }
    const key =
      this.bgmAudio?.dataset?.key ||
      this._lastBgmKey ||
      this.displayBeat?.bgm ||
      this.currentBeat()?.bgm;
    if (key) {
      this.playBgm(key, { force: true });
      return;
    }
    if (this.bgmAudio?.src) {
      this._attemptBgmPlay(this.bgmAudio.dataset.key || COVER_ENDING_BGM);
    }
  }

  currentChapter() {
    return this.chapters[this.chapterIndex];
  }

  currentBeat() {
    const ch = this.currentChapter();
    return ch?.beats?.[this.beatIndex];
  }

  /** 当前屏幕上正在展示的节拍（含分支对话） */
  activeBeat() {
    return this.displayBeat || this.currentBeat();
  }

  clampProgress() {
    if (!this.chapters?.length) {
      this.chapterIndex = 0;
      this.beatIndex = 0;
      return;
    }
    this.chapterIndex = Math.max(0, Math.min(this.chapterIndex, this.chapters.length - 1));
    const ch = this.chapters[this.chapterIndex];
    const maxBeat = Math.max(0, (ch?.beats?.length || 1) - 1);
    this.beatIndex = Math.max(0, Math.min(this.beatIndex, maxBeat));
  }

  startNew() {
    this.state = this.defaultState();
    this.chapterIndex = 0;
    this.beatIndex = 0;
    this.branchQueue = [];
    this.displayBeat = null;
    this.branchActive = false;
    this._currentBgKey = null;
    this._charSig = "";
    this._seenChapterOpenings.clear();
    [
      "#葵与星光旅人#",
      "#综艺嘉宾把芥末当护手霜#",
      "#流量明星机场背反背包#",
      "#某歌手直播忘关麦打呼噜#",
    ].forEach((t) => this.pushHot(t));
    this.state.wechat = [];
    this.state.wechatSynced = 0;
    this.state.wechatFlags = {};
    this.syncWeChatStory(true);
    this.run();
  }

  loadSave() {
    try {
      const raw = localStorage.getItem("kui_star_save_v2");
      if (!raw) return false;
      const data = JSON.parse(raw);
      this.state = { ...this.defaultState(), ...data.state };
      this.chapterIndex = data.chapterIndex ?? 0;
      this.beatIndex = data.beatIndex ?? 0;
      this.branchQueue = [];
      this.displayBeat = null;
      this.branchActive = false;
      this.clampProgress();
      if (this.chapterNumber() >= 3) {
        this.state.xz_identity_revealed = true;
      }
      return true;
    } catch {
      return false;
    }
  }

  save() {
    localStorage.setItem(
      "kui_star_save_v2",
      JSON.stringify({
        state: this.state,
        chapterIndex: this.chapterIndex,
        beatIndex: this.beatIndex,
      })
    );
  }

  pushHot(t) {
    this.state.hotTopics.unshift(t);
    if (this.state.hotTopics.length > 8) this.state.hotTopics.pop();
    this.renderHot();
  }

  wechatAvatarClass(from) {
    if (from === "薇薇") return "wechat-avatar--vv";
    if (from === "肖战") return "wechat-avatar--xz";
    if (from === "张艺兴") return "wechat-avatar--zyx";
    if (from === "龚俊") return "wechat-avatar--gj";
    if (from === "宋威龙") return "wechat-avatar--gj";
    return "";
  }

  pushChat(from, text, persist = true) {
    const msg = { from, text, at: Date.now() };
    this.state.wechat = this.state.wechat || [];
    const last = this.state.wechat[this.state.wechat.length - 1];
    if (last && last.from === from && last.text === text) return;
    this.state.wechat.push(msg);
    if (this.state.wechat.length > 48) this.state.wechat.shift();
    this.renderWeChat();
    if (persist) this.save();
  }

  syncWeChatStory(force = false) {
    const ch = this.chapterNumber();
    if (!force && this.state.wechatSynced >= ch) return;
    this.state.wechatFlags = this.state.wechatFlags || {};
    for (const block of StarlightEngine.WECHAT_TIMELINE) {
      if (block.chapter > ch) break;
      const flag = `ch_${block.chapter}`;
      if (this.state.wechatFlags[flag]) continue;
      if (block.chapter === 10 && (this.state.vv_gj < 45 || this.state.vv_friend < 40)) continue;
      block.msgs.forEach((m) => this.pushChat(m.from, m.text, false));
      this.state.wechatFlags[flag] = true;
    }
    if (this.state.vv_gj >= 55 && !this.state.wechatFlags?.vv_gj_hint) {
      this.pushChat("薇薇", "龚俊刚问我周末有没有空……我要不要答应？", false);
      this.state.wechatFlags.vv_gj_hint = true;
    }
    this.state.wechatSynced = ch;
    this.save();
  }

  renderWeChat() {
    const list = this.els.chatList;
    if (!list) return;
    const msgs = this.state.wechat || [];
    list.innerHTML = msgs
      .map((m) => {
        const me = m.from === "葵" || m.from === "我";
        const hideXz =
          m.from === "肖战" && this.chapterNumber() < 3 && !this.state.xz_identity_revealed;
        const shownFrom = hideXz ? "???" : m.from;
        const initial = (shownFrom || "?").slice(0, 1);
        const avCls = this.wechatAvatarClass(m.from);
        return `<div class="wechat-bubble-row ${me ? "wechat-bubble-row--me" : ""}">
          <span class="wechat-avatar ${avCls}">${initial}</span>
          <div class="wechat-bubble ${me ? "wechat-bubble--me" : "wechat-bubble--other"}">
            ${me ? "" : `<span class="wechat-bubble-name">${shownFrom}</span>`}
            ${m.text}
          </div>
        </div>`;
      })
      .join("");
    list.scrollTop = list.scrollHeight;
  }

  renderHot() {
    this.els.hotList.innerHTML = this.state.hotTopics
      .map((t, i) => `<li><em>${i + 1}</em>${t}</li>`)
      .join("");
  }

  renderStats() {
    const s = this.state;
    const rows = [
      ["金钱", `${s.money}万`, "机缘卡", `${s.chance_card}`],
      ["肖战", `${s.xz_love}/${s.xz_trust}`, "宋威龙", `${s.swl_love}`],
      ["张艺兴", `${s.zyx_love}`, "李昀锐", `${s.lyr_love}`],
      ["艺术", `${s.art_value}`, "舆论", `${s.public_opinion}`],
      ["薇薇", `${s.vv_friend}`, "牵线", `${s.vv_gj}`],
      ["误会", `${s.misunderstanding}`, "称号", s.titles.length ? s.titles.join("·") : "无"],
    ];
    this.els.statsPanel.innerHTML = rows
      .map((r) => `<div class="stat-line"><span>${r[0]} <b>${r[1]}</b></span><span>${r[2]} <b>${r[3]}</b></span></div>`)
      .join("");
  }

  setBackground(key) {
    if (!key || key === this._currentBgKey) return;
    const src = this.registry.webPath(key);
    if (!src) return;
    const img = this.els.bg;
    if (!img) return;
    const isFirst = !this._currentBgKey;
    this._currentBgKey = key;
    if (isFirst) {
      img.src = src;
      img.classList.remove("bg-fade");
      return;
    }
    img.classList.add("bg-fade");
    setTimeout(() => {
      img.src = src;
      img.classList.remove("bg-fade");
    }, 140);
  }

  chapterNumber() {
    return this.chapters?.[this.chapterIndex]?.chapter || this.state.chapter || 1;
  }

  syncXzIdentityFromBeat(beat) {
    const t = beat?.text || "";
    if (
      /摘下|摘掉|露出脸|真面目|我是肖战|原来是你|认出来|摘下口罩|原来叫肖战|原来他叫肖战|真的是肖战|真的是他|画展陌生人|顶流私服|卸了伪装|当普通观众|正式认识|没有口罩/.test(
        t
      )
    ) {
      this.state.xz_identity_revealed = true;
    }
    if (beat?.xz_reveal) {
      this.state.xz_identity_revealed = true;
    }
    if (this.chapterNumber() >= 3) {
      this.state.xz_identity_revealed = true;
    }
  }

  /** 是否使用口罩伪装立绘（含第2章闪回：已揭秘名字但仍显示当时口罩） */
  xzUseMaskedSprite(beat) {
    if (beat?.xz_flashback_masked) return true;
    this.syncXzIdentityFromBeat(beat);
    if (beat?.xz_reveal) return false;
    return !this.state.xz_identity_revealed && this.chapterNumber() < 3;
  }

  xzNeedsDisguise(beat) {
    return this.xzUseMaskedSprite(beat);
  }

  displaySpeakerName(speaker, beat) {
    if (!speaker) return "旁白";
    if (speaker === "肖战" && beat?.xz_flashback_masked) return "肖战";
    if (speaker === "肖战" && this.xzUseMaskedSprite(beat)) return "???";
    return speaker;
  }

  xzDisguiseAssetKey() {
    return this.registry.charAsset("肖战", "伪装1") || "char_肖战_伪装1";
  }

  /** 优先使用节拍里写好的 characters（奇遇/支线已配好双人站位） */
  charactersFromBeatData(beat) {
    const raw = beat?.characters || [];
    if (!raw.length) return null;
    const mapped = raw
      .filter((c) => c?.asset_key)
      .map((c) => ({
        asset_key: c.asset_key,
        layout: c.position || c.layout || "center",
      }));
    return mapped.length ? mapped : null;
  }

  /** 女主固定左侧；当前说话者在右侧；旁白/无对话则居中；立绘随台词情绪切换 */
  buildSceneCharacters(beat) {
    const preset = this.charactersFromBeatData(beat);
    if (preset) {
      return preset.map((c) => {
        const name = this.registry.charNameFromKey(c.asset_key);
        if (name === "肖战" && this.xzUseMaskedSprite(beat)) {
          return { ...c, asset_key: this.xzDisguiseAssetKey() };
        }
        return c;
      });
    }

    const HERO = "葵";
    const ch = this.chapterNumber();
    const raw = beat?.characters || [];
    const pickFromRaw = (name) => {
      const found = raw.find((c) => this.registry.charNameFromKey(c.asset_key) === name);
      return found?.asset_key || null;
    };
    const keyFor = (name) => {
      if (name === "肖战" && beat?.muscle_sprite) {
        return this.registry.charAsset("肖战", "肌肉") || "char_肖战_肌肉";
      }
      if (name === "肖战" && this.xzUseMaskedSprite(beat)) {
        return this.xzDisguiseAssetKey();
      }
      return (
        pickFromRaw(name) ||
        this.registry.assetKeyForSpeaker(name, beat, ch, this.state) ||
        this.registry.defaultAssetKey(name)
      );
    };
    const heroineKey = keyFor(HERO);

    if (beat?.type === "choice") {
      const raw = beat.characters || [];
      const npc = raw.find((c) => c.asset_key?.startsWith("npc_"));
      const hero = heroineKey || "char_葵_无语";
      if (npc?.asset_key) {
        return [
          { asset_key: hero, layout: "hero-left" },
          { asset_key: npc.asset_key, layout: "speaker-right" },
        ];
      }
      return [{ asset_key: hero, layout: "hero-left" }];
    }

    const speaker = beat?.speaker === "narrator" ? null : beat?.speaker || null;

    if (!speaker) {
      const key = raw[0]?.asset_key || heroineKey;
      if (!key) return [];
      return [{ asset_key: key, layout: "center" }];
    }

    if (speaker === HERO) {
      return [{ asset_key: heroineKey, layout: "hero-left" }];
    }

    let spKey = keyFor(speaker) || this.registry.npcAssetKey(speaker);
    if (!spKey) {
      const npc = raw.find((c) => c.asset_key?.startsWith("npc_"));
      if (npc) spKey = npc.asset_key;
    }
    const list = [{ asset_key: heroineKey, layout: "hero-left" }];
    if (spKey) list.push({ asset_key: spKey, layout: "speaker-right" });
    return list;
  }

  characterSpecSignature(spec) {
    if (!spec?.length) return "";
    return spec.map((c) => `${c.asset_key || ""}:${c.layout || "center"}`).join(";");
  }

  renderCharacters(charsOrBeat) {
    const stage = this.els.stage;
    if (!stage) return;

    const beat =
      charsOrBeat && !Array.isArray(charsOrBeat) && typeof charsOrBeat.type === "string"
        ? charsOrBeat
        : null;
    const spec = beat ? this.buildSceneCharacters(beat) : charsOrBeat;
    const sig = this.characterSpecSignature(spec || []);
    if (sig && sig === this._charSig) return;

    stage.querySelectorAll(".sprite-wrap").forEach((n) => {
      n.classList.add("sprite-exit");
      setTimeout(() => n.remove(), 280);
    });

    this._charSig = sig;
    const list = this.registry.resolveCharacters(spec || []);
    if (!list.length) {
      this._charSig = "";
      return;
    }

    list.forEach((c) => {
      if (!c.src) return;
      const wrap = document.createElement("div");
      wrap.className = `sprite-wrap layout-${c.layout} ${c.sizeClass || "size-default"}`;
      wrap.dataset.char = c.name || "";
      const glow = document.createElement("div");
      glow.className = "sprite-foot-glow";
      glow.setAttribute("aria-hidden", "true");
      glow.style.setProperty("--glow-color", this.registry.glowColorFor(c.name));
      const img = document.createElement("img");
      img.className = "sprite-img";
      img.alt = c.name || "";
      img.src = c.src;
      img.decoding = "async";
      wrap.appendChild(glow);
      wrap.appendChild(img);
      stage.appendChild(wrap);
      requestAnimationFrame(() => wrap.classList.add("sprite-enter"));
    });
  }

  canAdvanceDialogue() {
    const beat = this.activeBeat();
    if (!beat) return false;
    if (beat.type === "choice") return false;
    if (beat.type === "converge" || beat.type === "ending") return false;
    return true;
  }

  onDialogueClick() {
    const beat = this.activeBeat();
    if (beat?.type === "choice") {
      this.els.dialogueDock?.classList.add("need-choice");
      setTimeout(() => this.els.dialogueDock?.classList.remove("need-choice"), 600);
      const panel = document.getElementById("choicePanel");
      if (panel && !panel.classList.contains("is-visible")) {
        this.updateDialogueUiMode(beat);
        this.showChoices(beat);
      }
      return;
    }
    if (this.canAdvanceDialogue()) this.advance();
  }

  bindLayoutSync() {
    if (this._layoutSyncBound) return;
    this._layoutSyncBound = true;
    const run = () => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => this.syncPlayfieldMetrics());
      });
    };
    this._scheduleLayoutSync = run;
    const ui = this.els.gameUi;
    const dock = this.els.dialogueDock;
    const topBar = ui?.querySelector(".top-bar");
    if (typeof ResizeObserver !== "undefined") {
      this._layoutObserver = new ResizeObserver(run);
      if (topBar) this._layoutObserver.observe(topBar);
      if (dock) this._layoutObserver.observe(dock);
      if (this.els.choiceWrap) this._layoutObserver.observe(this.els.choiceWrap);
    }
    window.addEventListener("resize", run, { passive: true });
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", run, { passive: true });
    }
  }

  syncPlayfieldMetrics() {
    const ui = this.els.gameUi;
    if (!ui || ui.classList.contains("hidden")) return;
    const root = document.documentElement;
    const topBar = ui.querySelector(".top-bar");
    const dock = this.els.dialogueDock;
    if (topBar) {
      const th = Math.ceil(topBar.getBoundingClientRect().height);
      root.style.setProperty("--top-bar-h", `${th}px`);
    }
    if (dock) {
      const bh = Math.ceil(dock.getBoundingClientRect().height);
      root.style.setProperty("--bottom-stack-h", `${bh}px`);
      root.style.setProperty("--dock-reserve", `${bh}px`);
      const wrap = this.els.choiceWrap;
      const stage = this.els.stage;
      if (ui.classList.contains("has-choices") && wrap && stage) {
        const stageRect = stage.getBoundingClientRect();
        const wrapRect = wrap.getBoundingClientRect();
        const spriteFloor = Math.max(0, Math.ceil(wrapRect.top - stageRect.top));
        root.style.setProperty("--sprite-floor-h", `${spriteFloor}px`);
      } else {
        root.style.removeProperty("--sprite-floor-h");
      }
    }
  }

  updateDialogueUiMode(beat) {
    const box = this.els.dialogueBox;
    const dock = this.els.dialogueDock;
    const btn = document.getElementById("btnNext");
    if (!box || !dock) return;
    const isChoice = beat?.type === "choice";
    box.classList.toggle("dialogue-box--choice", isChoice);
    dock?.classList.toggle("dialogue-dock--choice", isChoice);
    const panel = document.getElementById("choicePanel");
    if (panel) {
      panel.classList.toggle("is-visible", isChoice);
      panel.setAttribute("aria-hidden", isChoice ? "false" : "true");
    }
    this.els.gameUi?.classList.toggle("has-choices", isChoice);
    if (!isChoice) {
      this.els.gameUi?.classList.remove("chapter-finale-choice");
      if (this.els.choicePanelLabel) {
        this.els.choicePanelLabel.textContent = "✦ 请点选上方选项";
      }
    }
    if (btn) btn.style.visibility = isChoice ? "hidden" : "visible";
    box.setAttribute("aria-label", isChoice ? "请先选择上方选项" : "点击继续对话");
    this._scheduleLayoutSync?.();
  }

  playChoiceFlash(theme = "gold") {
    const el = this.els.flashOverlay;
    el.className = `flash-overlay flash-${theme} active`;
    setTimeout(() => el.classList.remove("active"), 700);
  }

  isChanceCardChoice(beat) {
    if (beat?.requires_chance_card) return true;
    const q = beat?.question || "";
    return /机缘卡/.test(q);
  }

  /** 无机缘卡时不展示「机缘卡还剩」类抉择 */
  shouldSkipChanceCardChoice(beat) {
    return this.isChanceCardChoice(beat) && (this.state.chance_card || 0) <= 0;
  }

  /** 未达成前置分支标记时跳过整段节拍（如未买兔则跳过兑奖抉择、柜姐支线） */
  shouldSkipTaggedBeat(beat) {
    const req = beat?.requires_branch_tag;
    if (!req) return false;
    return !((this.state.branch_tags || {})[req] > 0);
  }

  choiceOptionsForBeat(beat) {
    const opts = beat?.options || [];
    let filtered = opts;
    if (this.isChanceCardChoice(beat)) {
      filtered = filtered.filter((o) => {
        const need = o.effects?.chance_card;
        return !(typeof need === "number" && need < 0) || this.state.chance_card > 0;
      });
    }
    const tags = this.state.branch_tags || {};
    filtered = filtered.filter((o) => {
      const req = o.effects?.requires_branch_tag;
      return !req || (tags[req] || 0) > 0;
    });
    return filtered.length ? filtered : opts;
  }

  showChoices(beat) {
    const wrap = this.els.choiceWrap;
    wrap.innerHTML = "";
    const labels = ["A", "B", "C", "D"];
    this.choiceOptionsForBeat(beat).forEach((opt, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-btn";
      btn.style.animationDelay = `${idx * 0.07}s`;
      const tag = labels[idx] || String(idx + 1);
      btn.innerHTML = `<span class="choice-tag">${tag}</span><span class="choice-text">${opt.text}</span>`;
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.pickChoice(beat, opt, btn);
      });
      wrap.appendChild(btn);
    });
    this._scheduleLayoutSync?.();
  }

  pickChoice(beat, opt, btn) {
    const need = opt.effects?.chance_card;
    if (typeof need === "number" && need < 0 && this.state.chance_card <= 0) {
      return this.toast("机缘卡不足");
    }
    Sfx.playChoiceClick();
    btn.classList.add("choice-picked");
    this.playChoiceFlash(["gold", "rose", "violet", "rain"][Math.floor(Math.random() * 4)]);
    this.applyEffects(this.effectsWithoutMoney(opt.effects));
    if (beat.id) this.state.branch_history.push(beat.id);
    this.branchQueue = (opt.branch || []).slice();
    this.branchActive = this.branchQueue.length > 0;
    this.els.choiceWrap.innerHTML = "";
    this.updateDialogueUiMode(null);
    this.els.gameUi?.classList.remove("chapter-finale-choice");
    setTimeout(() => this.advance(), 400);
  }

  zyxDanceEggCheck() {
    const s = this.state;
    if (s.zyx_dance_seen) return false;
    let p = 78;
    if (s.titles.includes("DEMO受害者") || s.zyx_love >= 22) p = 88;
    if (s.reject_demo_count >= 3) p = 32;
    return Math.random() * 100 < p;
  }

  renderBeat(beat) {
    if (!beat) return this.showEnding();
    this.syncWeChatStory();
    this.displayBeat = beat;
    const ch = this.currentChapter();
    if (!ch) {
      throw new Error("剧情章节数据异常，请刷新页面或通过本地服务器打开");
    }
    if (this.els.chapterNum) this.els.chapterNum.textContent = `第${ch.chapter}章`;
    if (this.els.chapterTitle) this.els.chapterTitle.textContent = ch.title;
    const total = ch.beats.length;
    const choiceIdx =
      beat.type === "choice"
        ? ch.beats.slice(0, this.beatIndex + 1).filter((b) => b.type === "choice").length
        : 0;
    const isFinale = beat.milestone === "chapter_finale" || choiceIdx === 6;
    if (this.els.beatProgress) {
      if (beat.type === "choice") {
        this.els.beatProgress.textContent = isFinale ? "章末抉择" : `关键选择 ${choiceIdx}/6`;
    } else if (beat.type === "converge") {
      this.els.beatProgress.textContent = "星回顾";
    } else if (this.branchActive) {
      this.els.beatProgress.textContent = "支线";
      } else {
        this.els.beatProgress.textContent = `节拍 ${this.beatIndex + 1}/${total}`;
      }
    }

    if (beat.background) this.setBackground(beat.background);
    if (beat.bgm && !this.isCoverOrEndingScreen()) this.playBgm(beat.bgm);
    if (beat.hot) this.pushHot(beat.hot);
    if (beat.hot_extra?.length) {
      beat.hot_extra.forEach((t) => this.pushHot(t));
    }

    if (this.shouldSkipTaggedBeat(beat)) {
      this.updateDialogueUiMode(null);
      this.advance();
      return;
    }

    if (beat.type === "choice") {
      if (this.shouldSkipChanceCardChoice(beat)) {
        this.updateDialogueUiMode(null);
        this.advance();
        return;
      }
      const isEncounter = beat.milestone === "encounter" || beat.encounter_npc || beat.host_speaker;
      if (this.els.speakerName) {
        if (isEncounter && beat.host_speaker) {
          this.els.speakerName.textContent = beat.host_speaker;
        } else {
          this.els.speakerName.textContent = isFinale ? "◆ 章末抉择" : "◆ 关键选择";
        }
      }
      if (this.els.dialogueText) {
        this.els.dialogueText.textContent = beat.question || "你的选择是？";
      }
      if (this.els.choicePanelLabel) {
        this.els.choicePanelLabel.textContent = isEncounter
          ? "✦ 奇遇 · 请点选你的回应"
          : isFinale
            ? "✦ 为本章落下你的选择"
            : "✦ 请点选上方选项";
      }
      if (this.els.beatProgress && isEncounter) {
        this.els.beatProgress.textContent = "✦ 奇遇";
      }
      this.renderCharacters(beat);
      this.showChoices(beat);
      this.updateDialogueUiMode(beat);
      this.els.gameUi?.classList.toggle("chapter-finale-choice", isFinale);
      return;
    }
    this.els.gameUi?.classList.remove("chapter-finale-choice");

    if (beat.type === "converge") {
      this.converge(beat.cycle);
      this.els.dialogueText.textContent = beat.text || "这一章的故事汇进了你的星图。";
      this.renderCharacters([]);
      setTimeout(() => this.advance(), 1200);
      return;
    }

    if (beat.type === "ending") {
      return this.showEnding();
    }

    const rawSpeaker = beat.speaker === "narrator" ? "" : beat.speaker || "葵";
    const speaker = this.displaySpeakerName(rawSpeaker, beat);
    if (this.els.speakerName) this.els.speakerName.textContent = speaker || "旁白";
    if (this.els.dialogueText) this.els.dialogueText.textContent = beat.text || "";
    if (beat.effects) this.applyEffects(beat.effects);
    this.renderCharacters(beat);
    this.updateDialogueUiMode(beat);

    if (beat.type === "demo_invite" || (beat.text && /DEMO|demo|编舞/.test(beat.text))) {
      this.pushChat("张艺兴", "新编舞 DEMO 发你了，有空点开看～");
      if (this.zyxDanceEggCheck()) {
        this.state.zyx_dance_seen = true;
        setTimeout(() => {
          this.renderCharacters([{ asset_key: "char_张艺兴_跳舞", layout: "center" }]);
          this.toast("✨ 彩蛋解锁：张艺兴跳舞");
          this.pushChat("张艺兴", "（视频）月光里这一跳，只给你看。");
        }, 700);
      }
    }
  }

  converge(cycle) {
    const s = this.state;
    let score = Math.floor(s.art_value / 10) + s.titles.length * 2;
    if (s.xz_trust >= 35) score += 3;
    this.toast(`星回顾 · 星光＋${score}`);
    if (s.money >= 30) this.checkMoneyPrompt();
  }

  advance() {
    if (this.branchQueue.length) {
      const b = this.branchQueue.shift();
      this.branchActive = true;
      this.renderBeat(b);
      this.save();
      return;
    }
    this.branchActive = false;
    this.beatIndex += 1;
    const ch = this.currentChapter();
    if (this.beatIndex >= ch.beats.length) {
      if (this.chapterIndex < this.chapters.length - 1) {
        const prevChapter = this.chapterIndex;
        this.chapterIndex += 1;
        this.beatIndex = 0;
        if (this.chapterNumber() >= 3) {
          this.state.xz_identity_revealed = true;
        }
        this.syncWeChatStory();
        const nextCh = this.chapters[this.chapterIndex];
        if (prevChapter === 0) {
          this._seenChapterOpenings.add(nextCh.chapter ?? 1);
          this.renderBeat(this.currentBeat());
        } else {
          this.showChapterOpening(nextCh);
        }
      } else {
        return this.showEnding();
      }
    }
    const beat = this.currentBeat();
    if (beat?.type === "ending") return this.showEnding();
    this.renderBeat(beat);
    this.save();
  }

  checkMoneyFateBeforeEnding() {
    const s = this.state;
    if (s.money >= 100 && s.chance_card_used === 0) {
      return new Promise((resolve) => {
        this.showModal(
          "有钱有缘",
          `存款 ${s.money} 万且未使用机缘卡。是否消耗全部金钱，将指定男星好感与信任拉满？`,
          [
            {
              text: "消耗金钱 · 肖战",
              action: () => {
                s.money = 0;
                s.xz_love = 100;
                s.xz_trust = 100;
                s.money_fate_used = true;
                resolve(true);
              },
            },
            {
              text: "消耗金钱 · 宋威龙",
              action: () => {
                s.money = 0;
                s.swl_love = 100;
                s.money_fate_used = true;
                resolve(true);
              },
            },
            { text: "不触发", action: () => resolve(false) },
          ]
        );
      });
    }
    return Promise.resolve(false);
  }

  resolveEnding() {
    const s = this.state;
    if (s.money_fate_used) return "与钱有缘，与命相逢";
    const byChoices = this.resolveEndingByChoiceRoute(s);
    if (byChoices) return byChoices;
    return "灯火两端，旧梦不言";
  }

  routeScore(s, route) {
    const tags = s.branch_tags || {};
    const picked = route.tags.reduce((sum, tag) => sum + (tags[tag] || 0), 0);
    const n = route.opportunities || route.tags.length || 1;
    const mean = n / 3;
    const sd = Math.sqrt((n * 2) / 9) || 1;
    return (picked - mean) / sd + (route.offset || 0);
  }

  resolveEndingByChoiceRoute(s) {
    let best = null;
    let bestScore = -Infinity;
    for (const route of Object.values(this.ENDING_ROUTES)) {
      const score = this.routeScore(s, route);
      if (score > bestScore) {
        best = route;
        bestScore = score;
      }
    }
    return best?.key || null;
  }

  endingEpilogue(key) {
    const s = this.state;
    const maps = {
      "星光落在展灯边": () =>
        "画展之后，葵与肖战把误会一件件说开。展馆灯沿的星光落在肩头，他们选择并肩走在聚光灯之外，把真心留给彼此。",
      "风从片场吹来": () =>
        "片场的风比热搜更真实。葵与宋威龙在一次次对戏与夜谈里靠近，肖战退成远方祝福，而薇薇仍是那个会半夜打来语音的闺蜜。",
      "听见月光在起舞": () =>
        "张艺兴在月光下起舞，葵在台下看懂了他的节奏。两人以艺术为桥梁慢慢走近，肖战把遗憾折进歌里，薇薇在一旁笑着起哄。",
      "画框之外，万物生长": () =>
        "葵没有停在谁的目光里。她办了自己的展，画笔与人生都长出新的枝桠；薇薇是并肩的闺蜜，肖战是礼貌而温暖的旧识。",
      "花开两岸，人间重逢": () =>
        "薇薇与龚俊在葵的牵线下重新认识彼此。葵守在闺蜜身边，看两岸的花在同一阵风里开花——人间重逢，比任何剧本都温柔。",
      "与钱有缘，与命相逢": () =>
        "机缘像一场豪赌，金钱换来得偿所愿的相遇。葵与心中所选终于同框，薇薇感叹「你这运气也太离谱」，却仍为好友真心高兴。",
      "展灯熄后，无人归来": () =>
        "展灯熄了，展厅空了。误会堆得太高，肖战没有归来，薇薇也渐行渐远。葵独自收拾画具，学会与沉默共处。",
      "灯火两端，旧梦不言": () =>
        "舆论的灯火太亮，旧梦只能不言。葵在名利场边缘保持清醒，薇薇偶尔来敲门，肖战与宋威龙都成了遥远的名字。",
      "最后一班地铁开向冬夜": () =>
        "冬夜的地铁呼啸而过。宋威龙陪葵坐了一程，肖战在下一站没有上车。薇薇发来「到家说一声」，是这座城市最后的暖。",
      "爱与梦想终将圆满": () =>
        "星光落在画框外，也落在你们肩上。葵与肖战牵手看展后的小聚，薇薇与龚俊在樱花下订下彼此的周末——爱与梦想，终于在同一座城市圆满。",
    };
    const fn = maps[key];
    return fn ? fn() : "旅程告一段落，故事留在你的选择里。";
  }

  mountEndingParticles(container, count = 36) {
    const layer = document.createElement("div");
    layer.className = "ending-particles";
    layer.setAttribute("aria-hidden", "true");
    for (let i = 0; i < count; i += 1) {
      const p = document.createElement("span");
      p.className = "ending-particle";
      p.style.left = `${6 + Math.random() * 88}%`;
      p.style.bottom = `${Math.random() * 42}%`;
      p.style.setProperty("--dur", `${2.8 + Math.random() * 3.2}s`);
      p.style.setProperty("--delay", `${Math.random() * 2.5}s`);
      layer.appendChild(p);
    }
    container.prepend(layer);
  }

  async showEnding() {
    await this.checkMoneyFateBeforeEnding();
    const key = this.resolveEnding();
    const cgSrc = this.registry.endingImageSrc(key);
    const epilogue = this.endingEpilogue(key);
    this.els.gameUi.classList.add("hidden");
    this.els.endingScreen.classList.remove("hidden");
    document.body.classList.add("ending-active");
    this.autoplayCoverBgm();
    const isHe = key === "爱与梦想终将圆满";
    this.els.endingScreen.innerHTML = `
      <div class="ending-wrap${isHe ? " ending-wrap--he" : ""}">
        <div class="ending-cg-frame">
          ${
            cgSrc
              ? `<img class="ending-cg" src="${cgSrc}" alt="《${key}》"/>`
              : `<div class="ending-cg-missing">结局画面暂未载入</div>`
          }
          <div class="ending-cg-shade" aria-hidden="true"></div>
        </div>
        <div class="ending-text-panel">
          <p class="ending-label">结局达成</p>
          <h2>《${key}》</h2>
          <p class="ending-epilogue">${epilogue}</p>
          <button type="button" class="choice-btn" id="btnRestart">再来一次</button>
        </div>
      </div>`;
    const panel = this.els.endingScreen.querySelector(".ending-text-panel");
    if (panel) this.mountEndingParticles(panel, isHe ? 48 : 36);
    document.getElementById("btnRestart").onclick = () => this.returnToCover();
    this.save();
  }

  returnToCover() {
    document.body.classList.remove("ending-active");
    this.els.endingScreen?.classList.add("hidden");
    this.els.gameUi?.classList.add("hidden");
    this.els.startScreen?.classList.remove("hidden");
    this.branchQueue = [];
    this.displayBeat = null;
    this.branchActive = false;
    this.autoplayCoverBgm();
  }

  useChanceCard(target) {
    const s = this.state;
    if (s.chance_card <= 0) return this.toast("机缘卡不足");
    s.chance_card -= 1;
    s.chance_card_used += 1;
    const map = {
      xz: { xz_love: 12, xz_trust: 10 },
      swl: { swl_love: 12 },
      zyx: { zyx_love: 12, art_value: 5 },
      lyr: { lyr_love: 12 },
      vv: { vv_friend: 12 },
      gj: { vv_gj: 15, vv_friend: 5 },
    };
    this.applyEffects(map[target] || map.xz);
    this.toast("机缘卡已使用");
    this.renderStats();
    this.save();
  }

  run() {
    try {
      if (!this.els.startScreen || !this.els.gameUi) {
        throw new Error("页面结构不完整，请确认使用最新 index.html");
      }
      this.clampProgress();
      this.els.startScreen.classList.add("hidden");
      this.els.gameUi.classList.remove("hidden");
      this.syncPlayfieldMetrics();
      this.renderStats();
      this.renderHot();
      this.renderWeChat();
      this.syncWeChatStory();
      const beat = this.currentBeat();
      this.renderBeat(beat);
      this.showChapterOpening(this.currentChapter());
      this._scheduleLayoutSync?.();
      this.save();
    } catch (err) {
      console.error(err);
      this.els.startScreen?.classList.remove("hidden");
      this.els.gameUi?.classList.add("hidden");
      throw err;
    }
  }

  showChapterOpening(chapter, opts = {}) {
    if (!chapter || !this.els.chapterCurtain) return;
    const force = !!opts.force;
    const key = chapter.chapter ?? this.chapterIndex;
    if (!force && this._seenChapterOpenings.has(key)) return;
    this._seenChapterOpenings.add(key);
    if (this.els.chapterCurtainNum) this.els.chapterCurtainNum.textContent = `第${chapter.chapter}章`;
    if (this.els.chapterCurtainTitle) {
      this.renderChapterCurtainTitle(chapter.title || "");
    }
    const curtain = this.els.chapterCurtain;
    const card = curtain.querySelector(".chapter-curtain-card");
    const titleLen = Array.from(chapter.title || "").length;
    card?.classList.toggle("chapter-curtain-card--tall", titleLen >= 7);
    this.populateChapterSand();
    clearTimeout(this._chapterOpeningTimer);
    curtain.classList.remove("hidden", "is-leaving");
    curtain.classList.add("is-active");
    this._chapterOpeningTimer = setTimeout(() => {
      curtain.classList.add("is-leaving");
      curtain.classList.remove("is-active");
      this._chapterOpeningTimer = setTimeout(() => {
        curtain.classList.add("hidden");
        curtain.classList.remove("is-leaving");
      }, 1500);
    }, 2700);
  }

  renderChapterCurtainTitle(title) {
    const el = this.els.chapterCurtainTitle;
    if (!el) return;
    el.dataset.title = title;
    const chars = Array.from(title);
    if (chars.length < 7) {
      el.textContent = title;
      return;
    }
    let split = Math.ceil(chars.length / 2);
    const yu = title.indexOf("与");
    if (yu >= 2 && yu < chars.length - 2) split = yu + 1;
    else if (chars.length === 7) split = 3;
    const first = chars.slice(0, split).join("");
    const second = chars.slice(split).join("");
    el.innerHTML = `<span class="chapter-curtain-title-line">${first}</span><span class="chapter-curtain-title-line">${second}</span>`;
  }

  populateChapterSand() {
    const layer = this.els.chapterCurtain?.querySelector(".chapter-curtain-sand");
    if (!layer) return;
    layer.innerHTML = "";
    const count = 56;
    for (let i = 0; i < count; i += 1) {
      const p = document.createElement("span");
      const fromText = i < 30;
      const side = Math.random();
      let left;
      let top;
      if (fromText) {
        left = 30 + Math.random() * 40;
        top = 33 + Math.random() * 28;
      } else if (side < 0.34) {
        left = 8 + Math.random() * 84;
        top = 11 + Math.random() * 12;
      } else if (side < 0.68) {
        left = 8 + Math.random() * 84;
        top = 72 + Math.random() * 12;
      } else {
        left = Math.random() < 0.5 ? 8 + Math.random() * 10 : 82 + Math.random() * 10;
        top = 20 + Math.random() * 58;
      }
      p.style.setProperty("--left", `${left.toFixed(1)}%`);
      p.style.setProperty("--top", `${top.toFixed(1)}%`);
      p.style.setProperty("--drift", `${(Math.random() * 18 - 9).toFixed(1)}px`);
      p.style.setProperty("--fall", `${(54 + Math.random() * 96).toFixed(1)}px`);
      p.style.setProperty("--delay", `${(Math.random() * 1.1).toFixed(2)}s`);
      p.style.setProperty("--size", `${(2.5 + Math.random() * 3.2).toFixed(1)}px`);
      layer.appendChild(p);
    }
  }

  openFatePanel() {
    const s = this.state;
    const canBuy = s.money >= 30;
    const buttons = [
      {
        text: canBuy
          ? `花费 30 万兑换 1 张（存款 ${s.money} 万）`
          : `花费 30 万兑换（当前 ${s.money} 万，不足）`,
        action: () => {
          if (!canBuy) {
            this.toast(`还差 ${30 - s.money} 万才能兑换`);
            return;
          }
          this.exchangeMoneyForChanceCard();
          this.openFatePanel();
        },
      },
    ];
    if (s.chance_card > 0) {
      buttons.push(
        { text: "肖战（好感+12 信任+10）", action: () => this.useChanceCard("xz") },
        { text: "宋威龙（好感+12）", action: () => this.useChanceCard("swl") },
        { text: "张艺兴（好感+12）", action: () => this.useChanceCard("zyx") },
        { text: "李昀锐（好感+12）", action: () => this.useChanceCard("lyr") },
        { text: "牵线薇薇（闺蜜+12 牵线+15）", action: () => this.useChanceCard("gj") }
      );
    } else {
      buttons.push({
        text: "（暂无机缘卡，可先兑换或等存款达标自动提示）",
        action: () => {},
      });
    }
    buttons.push({ text: "关闭", action: () => {} });
    this.showModal(
      `机缘卡 ×${s.chance_card}`,
      "可随时用 30 万兑换一张；每张卡对指定角色大幅提升好感。",
      buttons
    );
  }
}

window.StarlightEngine = StarlightEngine;
