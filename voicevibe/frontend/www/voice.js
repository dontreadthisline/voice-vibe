// ============================================================
// VoiceVibe Frontend — UI Only.  Zero audio logic here.
// All VAD/ASR runs in the Python backend.
//
// All panels are created dynamically via JS and mounted
// directly to document.body, completely independent of
// Shiny's DOM generation.
// ============================================================

(function () {
  "use strict";

  const qs = (sel) => document.querySelector(sel);
  const qsa = (sel) => document.querySelectorAll(sel);

  // —— SVG icons ——
  const ICONS = {
    fab: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
    mic: '<svg viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>',
    traffic: '<svg viewBox="0 0 24 24"><path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z"/></svg>',
    police: '<svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>',
    accident: '<svg viewBox="0 0 24 24"><path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.85 7h10.29l.76 2H6.09l.76-2zM19 13H5v-2h14v2zM7.5 16c-.83 0-1.5-.67-1.5-1.5S6.67 13 7.5 13s1.5.67 1.5 1.5S8.33 16 7.5 16zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>',
    danger: '<svg viewBox="0 0 24 24"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>',
    blocked: '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9C4.63 15.55 4 13.85 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1C19.37 8.45 20 10.15 20 12c0 4.42-3.58 8-8 8z"/></svg>',
    roadwork: '<svg viewBox="0 0 24 24"><path d="M12 2l-5.5 9h11z"/><circle cx="17.5" cy="17.5" r="4.5"/><path d="M3 13.5h8v8H3z"/></svg>',
  };

  const CATEGORIES = [
    { id: "traffic", label: "拥堵", cls: "cat-traffic" },
    { id: "police", label: "警察", cls: "cat-police" },
    { id: "accident", label: "事故", cls: "cat-accident" },
    { id: "danger", label: "危险", cls: "cat-danger" },
    { id: "blocked", label: "封路", cls: "cat-blocked" },
    { id: "roadwork", label: "修路", cls: "cat-roadwork" },
  ];

  // —— Build category grid HTML ——
  function categoriesHTML() {
    return CATEGORIES.map((c) => `
      <div class="vv-category ${c.cls}" data-vv-action="select-category" data-category="${c.id}">
        <div class="vv-category-icon">${ICONS[c.id]}</div>
        <span class="vv-category-label">${c.label}</span>
      </div>
    `).join("");
  }

  // —— Create all UI elements and mount to body ——
  function createUI() {
    // Prevent duplicate creation
    if (qs(".vv-fab")) return;

    // 1. FAB
    const fab = document.createElement("button");
    fab.className = "vv-fab";
    fab.setAttribute("data-vv-action", "open-panel");
    fab.innerHTML = ICONS.fab;
    document.body.appendChild(fab);

    // 2. Overlay
    const overlay = document.createElement("div");
    overlay.className = "vv-overlay";
    document.body.appendChild(overlay);

    // 3. Report Panel
    const panel = document.createElement("div");
    panel.className = "vv-panel";
    panel.innerHTML = `
      <div class="vv-panel-header">
        <span class="vv-panel-title">上报路况问题</span>
        <button class="vv-panel-close" data-vv-action="close-panel">×</button>
      </div>
      <div class="vv-voice-card" data-vv-action="open-voice">
        <div class="vv-voice-icon">${ICONS.mic}</div>
        <div class="vv-voice-info">
          <div class="vv-voice-title">智能语音上报</div>
          <div class="vv-voice-subtitle">直接语音描述，AI自动识别分类</div>
        </div>
        <span class="vv-voice-arrow">›</span>
      </div>
      <div class="vv-categories">${categoriesHTML()}</div>
      <div id="submit-section">
        <button class="vv-switch-btn" data-vv-action="submit-report" style="margin-top:20px;background:linear-gradient(135deg,#ff8c42,#ff6b35);color:white;border:none;">确认上报</button>
      </div>
    `;
    document.body.appendChild(panel);

    // 4. Voice Panel
    const voicePanel = document.createElement("div");
    voicePanel.className = "vv-voice-panel";
    voicePanel.innerHTML = `
      <div class="vv-voice-panel-header">
        <span class="vv-voice-panel-title">语音上报</span>
        <button class="vv-panel-close" data-vv-action="close-voice">×</button>
      </div>
      <div class="vv-voice-panel-body">
        <div class="vv-transcript" id="transcript-box">聆听中…</div>
        <div class="vv-waveform"></div>
        <div class="vv-status recording vv-recording-status">正在聆听…</div>
      </div>
      <div class="vv-voice-panel-footer">
        <button class="vv-switch-btn" data-vv-action="close-voice">切回点选优先 ›</button>
      </div>
    `;
    document.body.appendChild(voicePanel);
  }

  // —— Panel controls ——
  function openReportPanel() {
    qs(".vv-overlay")?.classList.add("active");
    qs(".vv-panel")?.classList.add("active");
  }

  function closeReportPanel() {
    qs(".vv-overlay")?.classList.remove("active");
    qs(".vv-panel")?.classList.remove("active");
  }

  function openVoicePanel() {
    closeReportPanel();
    qs(".vv-voice-panel")?.classList.add("active");

    if (window.Shiny && window.Shiny.setInputValue) {
      window.Shiny.setInputValue("vv_start_voice", { t: Date.now() }, { priority: "event" });
    }

    const statusEl = qs(".vv-recording-status");
    if (statusEl) {
      statusEl.textContent = "正在聆听…";
      statusEl.classList.add("recording");
    }
  }

  function closeVoicePanel() {
    qs(".vv-voice-panel")?.classList.remove("active");

    if (window.Shiny && window.Shiny.setInputValue) {
      window.Shiny.setInputValue("vv_stop_voice", { t: Date.now() }, { priority: "event" });
    }
  }

  // —— Event delegation (all clicks) ——
  document.addEventListener("click", function (e) {
    const target = e.target.closest("[data-vv-action]");
    if (!target) return;

    const action = target.dataset.vvAction;
    switch (action) {
      case "open-panel":
        openReportPanel();
        break;
      case "close-panel":
        closeReportPanel();
        break;
      case "open-voice":
        openVoicePanel();
        break;
      case "close-voice":
        closeVoicePanel();
        break;
      case "select-category": {
        const cat = target.dataset.category;
        if (window.Shiny && window.Shiny.setInputValue) {
          window.Shiny.setInputValue("selected_category", { category: cat, t: Date.now() });
        }
        qsa(".vv-category").forEach((el) => el.classList.remove("selected"));
        target.classList.add("selected");
        break;
      }
      case "submit-report":
        if (window.Shiny && window.Shiny.setInputValue) {
          window.Shiny.setInputValue("submit_report", { t: Date.now() });
        }
        break;
    }
  });

  // Click overlay to close
  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("vv-overlay")) {
      closeReportPanel();
      closeVoicePanel();
    }
  });

  // Keyboard
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (qs(".vv-voice-panel")?.classList.contains("active")) {
        closeVoicePanel();
      } else if (qs(".vv-panel")?.classList.contains("active")) {
        closeReportPanel();
      }
    }
  });

  // —— Shiny custom message handlers ——
  if (window.Shiny && window.Shiny.addCustomMessageHandler) {
    // Transcript updates
    Shiny.addCustomMessageHandler("vv_transcript", function (msg) {
      const el = qs("#transcript-box");
      if (el) el.textContent = msg.text || "聆听中…";
    });

    // Status updates
    Shiny.addCustomMessageHandler("vv_status", function (msg) {
      const el = qs(".vv-recording-status");
      if (!el) return;
      switch (msg.state) {
        case "listening":
          el.textContent = "正在聆听…";
          el.classList.add("recording");
          break;
        case "speaking":
          el.textContent = "识别中…";
          el.classList.add("recording");
          break;
        case "done":
          el.textContent = "识别完成";
          el.classList.remove("recording");
          break;
        case "timeout":
          el.textContent = "未检测到语音";
          el.classList.remove("recording");
          if (qs(".vv-voice-panel")?.classList.contains("active")) {
            setTimeout(closeVoicePanel, 1200);
          }
          break;
        case "error":
          el.textContent = "识别出错";
          el.classList.remove("recording");
          break;
      }
    });

    // Backend-triggered close
    Shiny.addCustomMessageHandler("vv_close_voice", function () {
      qs(".vv-voice-panel")?.classList.remove("active");
    });
  }

  // —— Auto-locate on map ready ——
  function autoLocate() {
    setTimeout(function () {
      const btn = qs(".maplibregl-ctrl-geolocate");
      if (btn) btn.click();
    }, 1500);
  }

  if (window.jQuery) {
    jQuery(document).on("shiny:value", autoLocate);
  }

  // —— Init ——
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createUI);
  } else {
    createUI();
  }
})();
