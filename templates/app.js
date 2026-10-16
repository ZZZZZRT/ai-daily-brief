/* 站点交互：工作流（横向节点 + 左右连接点 + 拖动 + 弹窗）；资讯源历史弹窗 */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ---------------- 弹窗 ---------------- */
  function ensureModal() {
    var m = document.getElementById("modal");
    if (m) return m;
    m = document.createElement("div");
    m.id = "modal";
    m.className = "modal";
    m.innerHTML =
      '<div class="modal-mask"></div>' +
      '<div class="modal-box" role="dialog" aria-modal="true">' +
      '<div class="modal-head"><h3 id="modalTitle"></h3>' +
      '<button class="modal-close" aria-label="关闭">×</button></div>' +
      '<div class="modal-body" id="modalBody"></div></div>';
    document.body.appendChild(m);
    m.querySelector(".modal-mask").addEventListener("click", closeModal);
    m.querySelector(".modal-close").addEventListener("click", closeModal);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModal(); });
    return m;
  }
  function openModal(title, html) {
    var m = ensureModal();
    m.querySelector("#modalTitle").textContent = title;
    m.querySelector("#modalBody").innerHTML = html;
    m.querySelector("#modalBody").scrollTop = 0;
    m.classList.add("open");
  }
  function closeModal() {
    var m = document.getElementById("modal");
    if (m) m.classList.remove("open");
  }

  /* ---------------- 工作流 ---------------- */
  function initFlow() {
    var canvas = document.getElementById("flowCanvas");
    var svg = document.getElementById("flowLinks");
    var nodes = window.WORKFLOW_NODES;
    if (!canvas || !svg || !nodes || !nodes.length) return;

    var NW = 186, GAP = 40, PAD = 26, MINH = 320;

    var els = nodes.map(function (n, i) {
      var el = document.createElement("div");
      el.className = "node" + (n.ai ? " node-ai" : "");
      el.style.width = NW + "px";
      el._i = i;
      el.innerHTML =
        '<div class="node-top">' +
          '<span class="node-dot">' + (i + 1) + "</span>" +
          '<span class="node-title">' + esc(n.title) + "</span>" +
          (n.ai ? '<span class="node-ai-badge">AI</span>' : "") +
        "</div>" +
        (n.short ? '<div class="node-sub">' + esc(n.short) + "</div>" : "") +
        (n.dos ? '<ul class="node-dos">' +
          n.dos.map(function (d) { return "<li>" + esc(d) + "</li>"; }).join("") +
          "</ul>" : "");
      canvas.appendChild(el);
      return el;
    });

    function layout() {
      var maxH = 0;
      els.forEach(function (el) { maxH = Math.max(maxH, el.offsetHeight); });
      var H = Math.max(MINH, maxH + 90);
      var totalW = nodes.length * NW + (nodes.length - 1) * GAP + PAD * 2;
      var wrapW = canvas.parentElement.clientWidth || 900;
      canvas.style.width = Math.max(totalW, wrapW) + "px";
      canvas.style.height = H + "px";
      els.forEach(function (el) {
        el.style.left = (PAD + el._i * (NW + GAP)) + "px";
        el.style.top = ((H - el.offsetHeight) / 2) + "px";
      });
    }

    function redraw() {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      svg.setAttribute("width", w);
      svg.setAttribute("height", h);
      svg.setAttribute("viewBox", "0 0 " + w + " " + h);
      var parts = ['<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" ' +
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">' +
        '<path d="M0,0 L10,5 L0,10 z" fill="#b7c6e6"/></marker></defs>'];
      var dots = [];
      for (var i = 0; i < els.length; i++) {
        var el = els[i];
        var cy = el.offsetTop + el.offsetHeight / 2;
        var lx = el.offsetLeft, rx = el.offsetLeft + el.offsetWidth;
        dots.push('<circle cx="' + lx + '" cy="' + cy + '" r="4"/>');
        dots.push('<circle cx="' + rx + '" cy="' + cy + '" r="4"/>');
        if (i < els.length - 1) {
          var nx2 = els[i + 1].offsetLeft;
          var ny2 = els[i + 1].offsetTop + els[i + 1].offsetHeight / 2;
          parts.push('<path class="link" marker-end="url(#arrow)" d="M' + rx + "," + cy +
            " L" + nx2 + "," + ny2 + '"/>');
        }
      }
      svg.innerHTML = parts.join("") + '<g class="dots">' + dots.join("") + "</g>";
    }

    els.forEach(function (el) {
      var sx, sy, ox, oy, moved = false, dragging = false;
      el.addEventListener("pointerdown", function (e) {
        if (e.target.closest("a")) return;
        dragging = true; moved = false;
        try { el.setPointerCapture(e.pointerId); } catch (err) {}
        sx = e.clientX; sy = e.clientY; ox = el.offsetLeft; oy = el.offsetTop;
        el.classList.add("dragging");
      });
      el.addEventListener("pointermove", function (e) {
        if (!dragging) return;
        var dx = e.clientX - sx, dy = e.clientY - sy;
        if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
        var nlx = Math.max(0, Math.min(ox + dx, canvas.clientWidth - el.offsetWidth));
        var nly = Math.max(0, Math.min(oy + dy, canvas.clientHeight - el.offsetHeight));
        el.style.left = nlx + "px";
        el.style.top = nly + "px";
        redraw();
      });
      el.addEventListener("pointerup", function () {
        if (!dragging) return;
        dragging = false; el.classList.remove("dragging");
        if (!moved) openNodeModal(nodes[el._i]);
      });
      el.addEventListener("pointercancel", function () {
        dragging = false; el.classList.remove("dragging");
      });
    });

    function openNodeModal(n) {
      var html = '<p class="modal-num">步骤 ' + n.idx + (n.ai ? " · AI 节点" : " · 非 AI") + "</p>";
      if (n.detail) html += "<p>" + esc(n.detail) + "</p>";
      if (n.dos) {
        html += '<p class="modal-num" style="margin-top:14px">AI 在这里做了：</p><ul class="modal-dos">' +
          n.dos.map(function (d) { return "<li>" + esc(d) + "</li>"; }).join("") + "</ul>";
      }
      openModal(n.title, html);
    }

    layout();
    redraw();
    window.addEventListener("resize", function () { layout(); redraw(); });
  }

  /* ---------------- 资讯源：点击行弹历史 ---------------- */
  function initSources() {
    var root = document.querySelector(".sources");
    if (!root) return;
    var cache = null;
    function getItems() {
      if (!cache) cache = fetch("data/items.json").then(function (r) {
        return r.ok ? r.json() : [];
      }).catch(function () { return []; });
      return cache;
    }
    root.addEventListener("click", function (e) {
      if (e.target.closest(".source-name")) return;
      var row = e.target.closest(".source-row");
      if (!row) return;
      e.preventDefault();
      var src = row.getAttribute("data-source");
      getItems().then(function (items) {
        var arr = (items || []).filter(function (x) { return x.source === src; });
        if (!arr.length) { openModal(src + " · 历史资讯", '<p class="modal-empty">暂无历史记录。</p>'); return; }
        var html = '<ul class="modal-list">' + arr.map(function (x) {
          var d = (x.ts || "").slice(0, 10);
          return '<li><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' +
            esc(x.title) + "</a><span class=\"modal-date\">" + d + "</span></li>";
        }).join("") + "</ul>";
        openModal(src + " · 历史资讯（" + arr.length + "）", html);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFlow();
    initSources();
  });
})();
