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

  var qs = function(sel) { return document.querySelector(sel); };
  var qsa = function(sel) { return document.querySelectorAll(sel); };

  // —— Test mode state ——
  var isTestMode = false;
  var lastFabClick = 0;

  // —— SVG icons ——
  var ICONS = {
    fab: '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    mic: '<svg viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>',
    traffic: '<svg viewBox="0 0 24 24"><path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z"/></svg>',
    police: '<svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>',
    accident: '<svg viewBox="0 0 24 24"><path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.85 7h10.29l.76 2H6.09l.76-2zM19 13H5v-2h14v2zM7.5 16c-.83 0-1.5-.67-1.5-1.5S6.67 13 7.5 13s1.5.67 1.5 1.5S8.33 16 7.5 16zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>',
    danger: '<svg viewBox="0 0 24 24"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>',
    blocked: '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9C4.63 15.55 4 13.85 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1C19.37 8.45 20 10.15 20 12c0 4.42-3.58 8-8 8z"/></svg>',
    roadwork: '<svg viewBox="0 0 24 24"><path d="M12 2l-5.5 9h11z"/><circle cx="17.5" cy="17.5" r="4.5"/><path d="M3 13.5h8v8H3z"/></svg>',
  };

  var CATEGORIES = [
    { id: "traffic", label: "拥堵", cls: "cat-traffic" },
    { id: "police", label: "警察", cls: "cat-police" },
    { id: "accident", label: "事故", cls: "cat-accident" },
    { id: "danger", label: "危险", cls: "cat-danger" },
    { id: "blocked", label: "封路", cls: "cat-blocked" },
    { id: "roadwork", label: "修路", cls: "cat-roadwork" },
  ];

  // —— Build category grid HTML ——
  function categoriesHTML() {
    return CATEGORIES.map(function(c) {
      return '<div class="vv-category ' + c.cls + '" data-vv-action="select-category" data-category="' + c.id + '">' +
        '<div class="vv-category-icon">' + ICONS[c.id] + '</div>' +
        '<span class="vv-category-label">' + c.label + '</span>' +
      '</div>';
    }).join("");
  }

  // —— Create all UI elements and mount to body ——
  function createUI() {
    // Prevent duplicate creation
    if (qs(".vv-fab")) return;

    // 1. FAB
    var fab = document.createElement("button");
    fab.className = "vv-fab";
    fab.setAttribute("data-vv-action", "open-panel");
    fab.innerHTML = ICONS.fab;
    document.body.appendChild(fab);

    // 2. Overlay
    var overlay = document.createElement("div");
    overlay.className = "vv-overlay";
    document.body.appendChild(overlay);

    // 3. Report Panel
    var panel = document.createElement("div");
    panel.className = "vv-panel";
    panel.innerHTML =
      '<div class="vv-panel-header">' +
        '<span class="vv-panel-title">上报路况问题</span>' +
        '<button class="vv-panel-close" data-vv-action="close-panel">×</button>' +
      '</div>' +
      '<div class="vv-voice-card" data-vv-action="open-voice">' +
        '<div class="vv-voice-icon">' + ICONS.mic + '</div>' +
        '<div class="vv-voice-info">' +
          '<div class="vv-voice-title">智能语音上报</div>' +
          '<div class="vv-voice-subtitle">直接语音描述，AI自动识别分类</div>' +
        '</div>' +
        '<span class="vv-voice-arrow">›</span>' +
      '</div>' +
      '<div class="vv-categories">' + categoriesHTML() + '</div>' +
      '<div id="submit-section">' +
        '<button class="vv-switch-btn" data-vv-action="submit-report" style="margin-top:20px;background:linear-gradient(135deg,#ff8c42,#ff6b35);color:white;border:none;">确认上报</button>' +
      '</div>';
    document.body.appendChild(panel);

    // 4. Voice Panel
    var voicePanel = document.createElement("div");
    voicePanel.className = "vv-voice-panel";
    voicePanel.innerHTML =
      '<div class="vv-voice-panel-header">' +
        '<span class="vv-voice-panel-title">语音上报</span>' +
        '<button class="vv-panel-close" data-vv-action="close-voice">×</button>' +
      '</div>' +
      '<div class="vv-voice-panel-body">' +
        '<div class="vv-waveform">' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
          '<div class="vv-wave-bar"></div>' +
        '</div>' +
        '<div class="vv-transcript" id="transcript-box"></div>' +
        '<div class="vv-qa-container" id="qa-container" style="display:none;">' +
          '<div class="vv-qa-section">' +
            '<div class="vv-qa-label">问题:</div>' +
            '<div class="vv-qa-text" id="llm-question"></div>' +
          '</div>' +
          '<div class="vv-qa-section">' +
            '<div class="vv-qa-label">回答:</div>' +
            '<div class="vv-qa-text" id="llm-answer"></div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="vv-voice-panel-footer">' +
        '<button class="vv-switch-btn" data-vv-action="close-voice">关闭</button>' +
      '</div>';
    document.body.appendChild(voicePanel);
  }

  // —— Panel controls ——
  function openReportPanel() {
    var overlay = qs(".vv-overlay");
    var panel = qs(".vv-panel");
    if (overlay) overlay.classList.add("active");
    if (panel) panel.classList.add("active");
  }

  function closeReportPanel() {
    var overlay = qs(".vv-overlay");
    var panel = qs(".vv-panel");
    if (overlay) overlay.classList.remove("active");
    if (panel) panel.classList.remove("active");
  }

  function openVoicePanel() {
    closeReportPanel();

    // Reset waveform state
    var waveform = qs(".vv-waveform");
    if (waveform) {
      waveform.classList.remove("animating");
      waveform.style.display = "";
    }

    // Clear transcript
    var transcriptEl = qs("#transcript-box");
    if (transcriptEl) transcriptEl.textContent = "";

    // Clear Q&A content
    var qaContainer = qs("#qa-container");
    var questionEl = qs("#llm-question");
    var answerEl = qs("#llm-answer");
    if (qaContainer) qaContainer.style.display = "none";
    if (questionEl) questionEl.textContent = "";
    if (answerEl) answerEl.textContent = "";

    var voicePanel = qs(".vv-voice-panel");
    if (voicePanel) voicePanel.classList.add("active");

    // Update title for test mode
    var titleEl = qs(".vv-voice-panel-title");
    if (titleEl) {
      if (isTestMode) {
        titleEl.textContent = "语音上报 (测试模式)";
        titleEl.style.color = "#f59e0b";
      } else {
        titleEl.textContent = "语音上报";
        titleEl.style.color = "";
      }
    }

    if (window.Shiny && window.Shiny.setInputValue) {
      if (isTestMode) {
        window.Shiny.setInputValue("vv_start_voice_test", { t: Date.now() }, { priority: "event" });
      } else {
        window.Shiny.setInputValue("vv_start_voice", { t: Date.now() }, { priority: "event" });
      }
    }
  }

  function closeVoicePanel() {
    var voicePanel = qs(".vv-voice-panel");
    if (voicePanel) voicePanel.classList.remove("active");

    // Reset test mode
    isTestMode = false;

    if (window.Shiny && window.Shiny.setInputValue) {
      window.Shiny.setInputValue("vv_stop_voice", { t: Date.now() }, { priority: "event" });
    }
  }

  // —— Event delegation (all clicks) ——
  document.addEventListener("click", function (e) {
    var target = e.target.closest("[data-vv-action]");
    if (!target) return;

    // —— Double-click FAB detection for test mode ——
    if (target.dataset.vvAction === "open-panel") {
      var now = Date.now();
      if (now - lastFabClick < 500) {
        // Double-click: trigger test mode
        e.preventDefault();
        e.stopPropagation();
        isTestMode = true;
        openVoicePanel();
        if (window.Shiny && window.Shiny.setInputValue) {
          window.Shiny.setInputValue("vv_start_voice_test", { t: now });
        }
        lastFabClick = 0;
        return;
      }
      lastFabClick = now;
    }

    var action = target.dataset.vvAction;
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
        var cat = target.dataset.category;
        if (window.Shiny && window.Shiny.setInputValue) {
          window.Shiny.setInputValue("selected_category", { category: cat, t: Date.now() });
        }
        var cats = qsa(".vv-category");
        for (var i = 0; i < cats.length; i++) {
          cats[i].classList.remove("selected");
        }
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
      var voicePanel = qs(".vv-voice-panel");
      var panel = qs(".vv-panel");
      if (voicePanel && voicePanel.classList.contains("active")) {
        closeVoicePanel();
      } else if (panel && panel.classList.contains("active")) {
        closeReportPanel();
      }
    }
  });

  // —— Shiny custom message handlers ——
  if (window.Shiny && window.Shiny.addCustomMessageHandler) {
    try {
      // Transcript updates
      Shiny.addCustomMessageHandler("vv_transcript", function (msg) {
        var el = qs("#transcript-box");
        if (el) el.textContent = msg.text || "";
      });

      // Status updates
      Shiny.addCustomMessageHandler("vv_status", function (msg) {
        if (msg.state === "timeout") {
          var vp = qs(".vv-voice-panel");
          if (vp && vp.classList.contains("active")) {
            setTimeout(closeVoicePanel, 1200);
          }
        }
      });

      // Backend-triggered close
      Shiny.addCustomMessageHandler("vv_close_voice", function () {
        var panel = qs(".vv-voice-panel");
        if (panel) panel.classList.remove("active");
      });

      // LLM streaming start
      Shiny.addCustomMessageHandler("vv_llm_start", function (msg) {
        var qaContainer = qs("#qa-container");
        var questionEl = qs("#llm-question");
        var answerEl = qs("#llm-answer");
        if (qaContainer) qaContainer.style.display = "";
        if (questionEl) questionEl.textContent = msg.question || "";
        if (answerEl) answerEl.textContent = "";
      });

      // LLM streaming chunk
      Shiny.addCustomMessageHandler("vv_llm_chunk", function (msg) {
        var answerEl = qs("#llm-answer");
        if (answerEl && msg.text) answerEl.textContent += msg.text;
      });

      // LLM streaming done
      Shiny.addCustomMessageHandler("vv_llm_done", function () {
        // Q&A remains visible, no further changes needed
      });

      // LLM error
      Shiny.addCustomMessageHandler("vv_llm_error", function (msg) {
        var qaContainer = qs("#qa-container");
        var answerEl = qs("#llm-answer");
        if (qaContainer) qaContainer.style.display = "";
        if (answerEl) answerEl.textContent = msg.text || "LLM请求出错";
      });
    } catch(e) {
      console.error("[VoiceVibe] Shiny handler registration failed:", e);
    }
  }

  // —— Auto-locate on map ready ——
  function autoLocate() {
    setTimeout(function () {
      var btn = qs(".maplibregl-ctrl-geolocate");
      if (btn) btn.click();
    }, 1500);
  }

  // Check if Shiny is already idle (event may have fired before this script ran)
  // If not idle yet, bind to the event. If already idle, trigger immediately.
  function setupAutoLocate() {
    if (!window.jQuery) return;

    // Check if shiny:idle has already fired by checking Shiny's internal state
    // Shiny sets shinyapp.$activeSubscriptions when busy, undefined when idle
    var alreadyIdle = window.Shiny && window.Shiny.shinyapp &&
                      !window.Shiny.shinyapp.$activeSubscriptions;

    if (alreadyIdle) {
      // Already idle - trigger immediately
      autoLocate();
    } else {
      // Not idle yet - bind to the event
      jQuery(document).on("shiny:idle", autoLocate);
    }
  }

  // Run setup after a small delay to ensure Shiny is initialized
  setTimeout(setupAutoLocate, 100);

  // —— Init ——
  function init() {
    // Ensure body exists before creating UI
    if (!document.body) {
      requestAnimationFrame(init);
      return;
    }
    createUI();
  }

  // Start initialization
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    requestAnimationFrame(init);
  }
})();
