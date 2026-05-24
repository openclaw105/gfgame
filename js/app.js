(async function bootstrap() {

  const btnStart = document.getElementById("btnStart");

  const btnContinue = document.getElementById("btnContinue");

  let engine = null;

  let ready = false;

  const isFileProtocol = location.protocol === "file:";



  function setLoading(loading, msg) {

    if (!btnStart) return;

    btnStart.disabled = loading;

    btnStart.textContent = loading ? msg || "加载中…" : "开始旅程";

  }



  function loadScript(src) {

    return new Promise((resolve, reject) => {

      const s = document.createElement("script");

      s.src = src;

      s.onload = () => resolve();

      s.onerror = () => reject(new Error(`无法加载 ${src}`));

      document.head.appendChild(s);

    });

  }



  async function ensureOfflineBundle() {

    if (!isFileProtocol || window.__KUI_STAR_OFFLINE__) return;

    await loadScript("js/offline-data.js");

  }



  async function ensureReady() {

    if (ready && engine) return engine;

    setLoading(true, "加载素材…");

    try {

      await ensureOfflineBundle();

    } catch (e) {

      setLoading(false);

      alert(

        "离线数据包缺失。\n请在游戏目录运行：\npython scripts/bundle_offline_data.py\n或双击 index.html 的同目录下需有 js/offline-data.js"

      );

      throw e;

    }

    const registry = new AssetRegistry();

    try {

      await registry.load("cursor_asset_manifest.json");

    } catch (e) {

      setLoading(false);

      if (isFileProtocol) {

        alert("无法加载素材配置。请确认 js/offline-data.js 存在。");

      } else {

        alert(

          "无法加载配置。可双击 index.html（离线），或运行「启动游戏.bat」后访问 http://127.0.0.1:8790/"

        );

      }

      console.error(e);

      throw e;

    }

    engine = new StarlightEngine(registry);

    try {

      await engine.init();

    } catch (e) {

      setLoading(false);

      alert(isFileProtocol ? "无法加载剧情数据包。" : "无法加载 data/chapters.json。");

      console.error(e);

      throw e;

    }

    window.game = engine;

    ready = true;

    setLoading(false);

    syncSoundMenuLabel(true);
    engine.playCoverBgm();

    return engine;

  }



  function reportStartError(e, fallback) {

    console.error(e);

    setLoading(false);

    alert(`${fallback}\n\n${e?.message || e}`);

  }



  btnStart?.addEventListener("click", async () => {

    try {

      Sfx.unlock();

      const g = await ensureReady();

      g.startNew();

    } catch (e) {

      reportStartError(e, "无法开始新游戏");

    }

  });



  btnContinue?.addEventListener("click", async () => {

    try {

      Sfx.unlock();

      const g = await ensureReady();

      if (g.loadSave()) g.run();

      else alert("暂无存档");

    } catch (e) {

      reportStartError(e, "无法读取存档（可尝试清除浏览器缓存后点「开始旅程」）");

    }

  });



  const gameMenuPanel = document.getElementById("gameMenuPanel");
  const menuBtnStats = document.getElementById("menuBtnStats");
  const menuBtnSound = document.getElementById("menuBtnSound");
  const btnStats = document.getElementById("btnStats");

  function syncSoundMenuLabel(on) {
    if (!menuBtnSound) return;
    const enabled = on !== undefined ? on : engine?.soundOn !== false;
    menuBtnSound.textContent = enabled ? "音乐：开" : "音乐：关";
    menuBtnSound.classList.toggle("is-off", !enabled);
  }

  function closeTopPanels(exceptId) {
    const ids = ["gameMenuPanel", "statsPanel", "hotPanel", "phonePanel"];
    ids.forEach((id) => {
      if (id === exceptId) return;
      const el = document.getElementById(id);
      el?.classList.remove("open");
    });
    if (exceptId !== "gameMenuPanel") {
      btnStats?.classList.remove("menu-open");
      btnStats?.setAttribute("aria-expanded", "false");
    }
  }

  btnStats?.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = !gameMenuPanel?.classList.contains("open");
    if (open) {
      closeTopPanels("gameMenuPanel");
      gameMenuPanel?.classList.add("open");
      btnStats?.classList.add("menu-open");
      btnStats?.setAttribute("aria-expanded", "true");
      syncSoundMenuLabel();
    } else {
      closeTopPanels(null);
    }
  });

  gameMenuPanel?.addEventListener("click", (e) => e.stopPropagation());

  menuBtnStats?.addEventListener("click", (e) => {
    e.stopPropagation();
    const panel = document.getElementById("statsPanel");
    const willOpen = !panel?.classList.contains("open");
    closeTopPanels(null);
    if (willOpen) {
      ensureReady().then((g) => {
        g.renderStats();
        panel?.classList.add("open");
        menuBtnStats?.classList.add("is-active");
      });
    } else {
      panel?.classList.remove("open");
      menuBtnStats?.classList.remove("is-active");
    }
  });

  menuBtnSound?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!engine) return;
    const on = engine.toggleSound();
    syncSoundMenuLabel(on);
    if (on && isCoverOrEndingVisible()) engine.playCoverBgm({ userGesture: true });
  });

  function toggleSidePanel(panelId, onOpen) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    const willOpen = !panel.classList.contains("open");
    closeTopPanels(willOpen ? panelId : null);
    if (willOpen) {
      ensureReady().then((g) => {
        onOpen?.(g);
        panel.classList.add("open");
      });
    } else {
      panel.classList.remove("open");
    }
  }

  document.getElementById("btnHot")?.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleSidePanel("hotPanel", (g) => g.renderHot());
  });

  document.getElementById("btnPhone")?.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleSidePanel("phonePanel", (g) => g.renderWeChat());
  });

  ["statsPanel", "hotPanel", "phonePanel"].forEach((id) => {
    document.getElementById(id)?.addEventListener("click", (e) => e.stopPropagation());
  });

  document.getElementById("gameUi")?.addEventListener("click", (e) => {
    if (e.target.closest(".top-bar, .side-panel, .game-menu-panel")) return;
    closeTopPanels(null);
    document.getElementById("statsPanel")?.classList.remove("open");
    menuBtnStats?.classList.remove("is-active");
  });

  document.getElementById("btnFate")?.addEventListener("click", async (e) => {
    e.stopPropagation();
    closeTopPanels(null);
    try {
      const g = await ensureReady();
      g.openFatePanel();
    } catch (_) {}
  });

  document.getElementById("btnNext")?.addEventListener("click", (e) => {

    e.stopPropagation();

    if (!engine) return;

    engine.onDialogueClick();

  });



  document.getElementById("dialogueBox")?.addEventListener("click", () => {

    if (!engine) return;

    engine.onDialogueClick();

  });



  document.getElementById("dialogueBox")?.addEventListener("keydown", (e) => {

    if (e.key === "Enter" || e.key === " ") {

      e.preventDefault();

      engine?.onDialogueClick();

    }

  });

  function isCoverOrEndingVisible() {
    const start = document.getElementById("startScreen");
    const ending = document.getElementById("endingScreen");
    const onCover = start && !start.classList.contains("hidden");
    const onEnding =
      (ending && !ending.classList.contains("hidden")) ||
      document.body.classList.contains("ending-active");
    return onCover || onEnding;
  }

  function onCoverPointer() {
    Sfx.unlock();
    if (!isCoverOrEndingVisible() || engine?.soundOn === false) return;
    engine.playCoverBgm({ userGesture: true });
  }

  document.getElementById("startScreen")?.addEventListener("pointerdown", onCoverPointer, {
    capture: true,
  });
  document.getElementById("endingScreen")?.addEventListener("pointerdown", onCoverPointer, {
    capture: true,
  });
  document.addEventListener("keydown", () => {
    Sfx.unlock();
    if (isCoverOrEndingVisible()) onCoverPointer();
  });

  function triggerTopBarBurst(el) {
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    el.classList.remove("top-bar-burst");
    void el.offsetWidth;
    el.classList.add("top-bar-burst");
    clearTimeout(el._topBarBurstT);
    el._topBarBurstT = setTimeout(() => el.classList.remove("top-bar-burst"), 620);
  }

  function bindTopBarBurstFx() {
    const ui = document.getElementById("gameUi");
    if (!ui || ui.dataset.topBarBurstBound) return;
    ui.dataset.topBarBurstBound = "1";
    ui.querySelectorAll(".icon-btn").forEach((btn) => {
      btn.addEventListener("pointerdown", (e) => {
        triggerTopBarBurst(btn);
      });
    });
    const chapterFrame = ui.querySelector(".chapter-header-frame");
    if (chapterFrame) {
      chapterFrame.addEventListener("pointerdown", (e) => {
        if (e.target.closest(".icon-btn")) return;
        triggerTopBarBurst(chapterFrame);
      });
    }
  }

  bindTopBarBurstFx();

  async function boot() {
    try {
      await ensureOfflineBundle();
      document.getElementById("coverBgmPrefetch")?.load?.();
    } catch (_) {}
    ensureReady().catch(() => setLoading(false));
  }
  boot();

})();

