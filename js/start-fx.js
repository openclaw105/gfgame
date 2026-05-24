/**
 * 封面：环境金粉 + 粒子流星（最多 3 条、分散、透视远近）
 */
(function () {
  let meteorTimer = null;
  const activeMeteors = [];
  const MAX_METEORS = 3;
  const MIN_SPAWN_DIST = 24;
  /** 整体体量缩放（<1 更小） */
  const SIZE_MUL = 0.58;
  /** 划过轨迹长度倍数 */
  const PATH_MUL = 6;
  /** 运动速度倍数（>1 更快） */
  const SPEED_MUL = 2;

  const METEOR_ANGLE_BASE = 135;
  const METEOR_ANGLE_JITTER = 16;

  /** 分散出生区（右上及中上区域） */
  const SPAWN_ZONES = [
    { mx: [10, 32], my: [2, 14] },
    { mx: [78, 96], my: [2, 12] },
    { mx: [42, 58], my: [4, 18] },
    { mx: [18, 40], my: [14, 30] },
    { mx: [68, 90], my: [12, 28] },
    { mx: [48, 72], my: [22, 38] },
    { mx: [30, 52], my: [6, 22] },
    { mx: [58, 82], my: [18, 34] },
  ];

  function particleCount() {
    const w = window.innerWidth || 390;
    return w < 400 ? 28 : 40;
  }

  function isStartVisible() {
    const screen = document.getElementById("startScreen");
    return screen && !screen.classList.contains("hidden");
  }

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function mountParticles(container) {
    if (!container) return;
    container.innerHTML = "";
    const n = particleCount();
    for (let i = 0; i < n; i += 1) {
      const p = document.createElement("span");
      p.className = "start-particle";
      p.style.left = `${4 + Math.random() * 92}%`;
      p.style.top = `${8 + Math.random() * 78}%`;
      p.style.setProperty("--dur", `${2.5 + Math.random() * 4}s`);
      p.style.setProperty("--delay", `${Math.random() * 3}s`);
      p.style.setProperty("--size", `${2 + Math.random() * 3}px`);
      container.appendChild(p);
    }
  }

  function tooClose(mxPct, myPct, existing) {
    for (const m of existing) {
      const dx = mxPct - m.mxPct;
      const dy = myPct - m.myPct;
      if (Math.hypot(dx, dy) < MIN_SPAWN_DIST) return true;
    }
    return false;
  }

  function pickDepth(existing) {
    const buckets = existing.map((m) => Math.round(m.depth * 4));
    for (let i = 0; i < 16; i += 1) {
      const d = 0.28 + Math.random() * 0.72;
      const b = Math.round(d * 4);
      if (!buckets.includes(b)) return d;
    }
    return 0.28 + Math.random() * 0.72;
  }

  function pickSpawnPoint(existing, depth) {
    const zones = SPAWN_ZONES.slice().sort(() => Math.random() - 0.5);
    const myCap = depth < 0.45 ? 20 : depth > 0.72 ? 42 : 32;

    for (const z of zones) {
      if (z.my[0] > myCap) continue;
      for (let t = 0; t < 10; t += 1) {
        const mxPct = z.mx[0] + Math.random() * (z.mx[1] - z.mx[0]);
        const myPct = z.my[0] + Math.random() * (Math.min(z.my[1], myCap) - z.my[0]);
        if (!tooClose(mxPct, myPct, existing)) {
          return { mx: `${mxPct}%`, my: `${myPct}%`, mxPct, myPct };
        }
      }
    }

    const mxPct = 12 + Math.random() * 82;
    const myPct = 2 + Math.random() * myCap;
    return { mx: `${mxPct}%`, my: `${myPct}%`, mxPct, myPct };
  }

  function fadeAlpha(progress, peak) {
    let a = peak;
    if (progress < 0.05) a *= progress / 0.05;
    if (progress > 0.78) a *= (1 - progress) / 0.22;
    return a;
  }

  function twinkle(now, pt) {
    const wave = Math.sin(now * pt.twinkleSpeed + pt.phase);
    const wave2 = Math.sin(now * pt.twinkleSpeed * 2.3 + pt.phase * 1.7);
    return 0.55 + 0.45 * Math.max(wave, wave2 * 0.85);
  }

  function buildDot(variant, kind, ox, oy, size, peak, sx, sy, angle) {
    const el = document.createElement("span");
    const cls = ["start-meteor-dot", `start-meteor-dot--${kind}`];
    if (variant === "spark") cls.push("start-meteor-dot--spark");
    if (variant === "grain") cls.push("start-meteor-dot--grain");
    if (variant === "micro") cls.push("start-meteor-dot--micro");
    el.className = cls.join(" ");
    if (variant === "grain") {
      const gw = size * (2.2 + Math.random() * 2.5);
      const gh = Math.max(1, size * (0.28 + Math.random() * 0.22));
      el.style.setProperty("--grain-w", `${gw}px`);
      el.style.setProperty("--grain-h", `${gh}px`);
    } else {
      el.style.width = `${size}px`;
      el.style.height = `${size}px`;
      el.style.marginLeft = `${-size / 2}px`;
      el.style.marginTop = `${-size / 2}px`;
    }
    return {
      el,
      variant,
      ox,
      oy,
      size,
      peak,
      sx,
      sy,
      angle,
      phase: Math.random() * Math.PI * 2,
      twinkleSpeed: 0.008 + Math.random() * 0.014,
    };
  }

  function makeMeteorTicker(meteor) {
    return function frame(now) {
      if (!meteor.burst.isConnected || !isStartVisible()) {
        meteor.dispose();
        return;
      }
      const progress = Math.min(1, (now - meteor.t0) / 1000 / meteor.dur);
      const headX = meteor.dx * progress;
      const headY = meteor.dy * progress;
      const scatter = progress * (0.28 + meteor.depth * 0.22);

      if (meteor.streakEl) {
        const sa = fadeAlpha(progress, 0.55 + meteor.depth * 0.4);
        meteor.streakEl.style.transform = `translate3d(${headX}px,${headY}px,0) rotate(${meteor.angle}deg)`;
        meteor.streakEl.style.opacity = String(sa * (0.85 + 0.15 * Math.sin(now * 0.01)));
      }

      for (const pt of meteor.particles) {
        const x = headX + pt.ox + pt.sx * scatter;
        const y = headY + pt.oy + pt.sy * scatter;
        let alpha = fadeAlpha(progress, pt.peak);
        if (pt.variant === "spark" || pt.kind === "head") {
          alpha *= twinkle(now, pt);
        } else if (pt.kind === "tail") {
          alpha *= 0.75 + 0.25 * twinkle(now, pt);
        }
        const rot = pt.variant === "grain" ? ` rotate(${pt.angle}deg)` : "";
        const pulse = pt.variant === "spark" ? 0.85 + 0.35 * twinkle(now, pt) : 1;
        const pScale = meteor.sizeScale * pulse;
        pt.el.style.transform = `translate3d(${x}px,${y}px,0)${rot} scale(${pScale})`;
        pt.el.style.opacity = String(Math.min(1, alpha));
        if (pt.variant === "spark" || pt.kind === "head") {
          pt.el.style.filter = `brightness(${0.85 + meteor.depth * 0.35 + 0.45 * twinkle(now, pt)})`;
        }
      }

      if (progress >= 1) {
        meteor.dispose();
        return;
      }
      meteor.raf = requestAnimationFrame(frame);
    };
  }

  function createMeteorState(burst, particles, streakEl, meta) {
    const meteor = {
      burst,
      particles,
      streakEl,
      angle: meta.angle,
      dx: meta.dx,
      dy: meta.dy,
      dur: meta.dur,
      depth: meta.depth,
      sizeScale: meta.sizeScale,
      mxPct: meta.mxPct,
      myPct: meta.myPct,
      t0: 0,
      raf: 0,
      dispose() {
        cancelAnimationFrame(this.raf);
        this.burst.remove();
        const i = activeMeteors.indexOf(this);
        if (i >= 0) activeMeteors.splice(i, 1);
      },
    };
    return meteor;
  }

  function spawnParticleMeteor(container) {
    if (!container || !isStartVisible() || prefersReducedMotion()) return;
    if (activeMeteors.length >= MAX_METEORS) return;

    const depth = pickDepth(activeMeteors);
    const spawn = pickSpawnPoint(activeMeteors, depth);
    const pScale = (0.34 + depth * 0.42) * SIZE_MUL;
    const sizeScale = 0.5 + depth * 0.45;
    const bright = 0.38 + depth * 0.62;

    const angle = METEOR_ANGLE_BASE + (Math.random() - 0.5) * METEOR_ANGLE_JITTER;
    const rad = (angle * Math.PI) / 180;
    const travelBase =
      55 +
      Math.random() * (window.innerWidth < 420 ? 70 : 130) +
      Math.random() * (window.innerHeight < 700 ? 30 : 70);
    const travel = travelBase * (0.42 + depth * 0.52) * SIZE_MUL * PATH_MUL;
    const dx = Math.cos(rad) * travel;
    const dy = Math.sin(rad) * travel;
    const dur = (((1.25 + Math.random() * 1) / (0.5 + depth * 0.55)) * PATH_MUL) / SPEED_MUL;
    const tailLen = (28 + Math.random() * 62) * (0.4 + depth * 0.55) * SIZE_MUL * 2.8;

    const burst = document.createElement("span");
    burst.className = "start-meteor-burst";
    if (depth < 0.42) burst.classList.add("start-meteor-burst--far");
    else if (depth > 0.72) burst.classList.add("start-meteor-burst--near");
    burst.style.left = spawn.mx;
    burst.style.top = spawn.my;
    burst.style.zIndex = String(2 + Math.round(depth * 8));

    const streakEl = document.createElement("span");
    streakEl.className = "start-meteor-streak";
    streakEl.style.width = `${tailLen}px`;
    streakEl.style.height = `${(0.7 + depth * 1.8) * SIZE_MUL}px`;
    streakEl.style.opacity = String(0.45 + depth * 0.5);
    burst.appendChild(streakEl);

    const particles = [];
    const ux = dx / travel;
    const uy = dy / travel;
    const perpX = -uy;
    const perpY = ux;
    const density = 0.32 + depth * 0.68;

    const tailAlong = () => {
      const t = Math.pow(Math.random(), 1.65);
      return tailLen * 0.02 + t * tailLen * 0.98;
    };

    const addBatch = (baseCount, variant, kind, sizeMin, sizeMax, peakMin, peakMax, spreadMul) => {
      const count = Math.max(1, Math.round(baseCount * density));
      for (let i = 0; i < count; i += 1) {
        const along = kind === "head" ? Math.random() * tailLen * 0.12 : tailAlong();
        const ox = -ux * along;
        const oy = -uy * along;
        const spread = (1 - along / tailLen) * spreadMul * pScale * (0.55 + Math.random() * 0.75);
        const sx = perpX * (Math.random() - 0.5) * spread;
        const sy = perpY * (Math.random() - 0.5) * spread;
        const size = (sizeMin + Math.random() * (sizeMax - sizeMin)) * pScale;
        const peak = (peakMin + Math.random() * (peakMax - peakMin)) * bright;
        const pt = buildDot(variant, kind, ox, oy, size, peak, sx, sy, angle);
        burst.appendChild(pt.el);
        particles.push(pt);
      }
    };

    addBatch(4, "orb", "head", 2.2, 4.8, 0.9, 1, 6);
    addBatch(4, "spark", "head", 2, 4.2, 0.8, 1, 7);
    addBatch(18, "orb", "tail", 0.9, 2.8, 0.45, 0.95, 10);
    addBatch(9, "spark", "tail", 1.4, 3.5, 0.5, 0.92, 9);
    addBatch(8, "grain", "tail", 1, 2.6, 0.35, 0.82, 7);
    addBatch(14, "micro", "tail", 0.5, 1.6, 0.25, 0.72, 11);

    container.appendChild(burst);
    const meteor = createMeteorState(burst, particles, streakEl, {
      angle,
      dx,
      dy,
      dur,
      depth,
      sizeScale,
      mxPct: spawn.mxPct,
      myPct: spawn.myPct,
    });
    activeMeteors.push(meteor);

    const frame = makeMeteorTicker(meteor);
    requestAnimationFrame((t0) => {
      meteor.t0 = t0;
      meteor.raf = requestAnimationFrame(frame);
    });
  }

  function scheduleMeteors(container) {
    if (!container || prefersReducedMotion()) return;

    const tick = () => {
      if (!isStartVisible()) {
        meteorTimer = null;
        return;
      }
      if (activeMeteors.length < MAX_METEORS) {
        spawnParticleMeteor(container);
      }
      meteorTimer = window.setTimeout(tick, 1400 + Math.random() * 3200);
    };

    window.setTimeout(() => {
      if (activeMeteors.length < MAX_METEORS) spawnParticleMeteor(container);
      tick();
    }, 400 + Math.random() * 500);
  }

  function stopMeteors() {
    if (meteorTimer) {
      window.clearTimeout(meteorTimer);
      meteorTimer = null;
    }
    while (activeMeteors.length) {
      activeMeteors[0].dispose();
    }
  }

  function initStartFx() {
    mountParticles(document.getElementById("startParticles"));
    scheduleMeteors(document.getElementById("startMeteors"));

    const screen = document.getElementById("startScreen");
    if (screen && typeof MutationObserver !== "undefined") {
      const obs = new MutationObserver(() => {
        if (!isStartVisible()) stopMeteors();
      });
      obs.observe(screen, { attributes: true, attributeFilter: ["class"] });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initStartFx);
  } else {
    initStartFx();
  }
})();
