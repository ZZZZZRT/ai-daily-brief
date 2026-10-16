/* 站点交互：工作流可拖动节点 + 弹窗；资讯源历史弹窗 */
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

  /* ---------------- 工作流：可拖动节点 + 连线 ---------------- */
  function initFlow() {
    var canvas = document.getElementById("flowCanvas");
    var svg = document.getElementById("flowLinks");
    var nodes = window.WORKFLOW_NODES;
    if (!canvas || !svg || !nodes || !nodes.length) return;

    var NW = 208, NH = 86, GX = 46, GY = 54;
    var W = canvas.clientWidth || 900;
    var cols = W < 560 ? 1 : (W < 1000 ? 2 : 3);
    var rows = Math.ceil(nodes.length / cols);
    var totalW = cols * NW + (cols - 1) * GX;
    var startX = Math.max(6, Math.round((W - totalW) / 2));
    canvas.style.height = (rows * NH + (rows - 1) * GY + 24) + "px";

    var els = nodes.map(function (n, i) {
      var r = Math.floor(i / cols), c = i % cols;
      var el = document.createElement("div");
      el.className = "node";
      el.style.left = (startX + c * (NW + GX)) + "px";
      el.style.top = (12 + r * (NH + GY)) + "px";
      el.innerHTML = '<span class="node-dot">' + (i + 1) + "</span>" +
        '<div class="node-text"><div class="node-title">' + esc(n.title) + "</div>" +
        '<div class="node-sub">' + esc(n.short) + "</div></div>";
      el._idx = i;
      canvas.appendChild(el);
      return el;
    });

    function redraw() {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      svg.setAttribute("width", w);
      svg.setAttribute("height", h);
      svg.setAttribute("viewBox", "0 0 " + w + " " + h);
      var parts = [];
      for (var i = 0; i < els.length - 1; i++) {
        var a = els[i], b = els[i + 1];
        var ax = a.offsetLeft + a.offsetWidth / 2, ay = a.offsetTop + a.offsetHeight;
        var bx = b.offsetLeft + b.offsetWidth / 2, by = b.offsetTop;
        var d = "M" + ax + "," + ay + " C" + ax + "," + (ay + 30) + " " +
                bx + "," + (by - 30) + " " + bx + "," + by;
        parts.push('<path class="link" marker-end="url(#arrow)" d="' + d + '" />');
      }
      svg.innerHTML = '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" ' +
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">' +
        '<path d="M0,0 L10,5 L0,10 z" fill="#b7c6e6"/></marker></defs>' + parts.join("");
    }

    els.forEach(function (el) {
      var sx, sy, ox, oy, moved = false, dragging = false;
      el.addEventListener("pointerdown", function (e) {
        dragging = true; moved = false;
        try { el.setPointerCapture(e.pointerId); } catch (err) {}
        sx = e.clientX; sy = e.clientY; ox = el.offsetLeft; oy = el.offsetTop;
        el.classList.add("dragging");
      });
      el.addEventListener("pointermove", function (e) {
        if (!dragging) return;
        var dx = e.clientX - sx, dy = e.clientY - sy;
        if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
        el.style.left = Math.max(0, ox + dx) + "px";
        el.style.top = Math.max(0, oy + dy) + "px";
        redraw();
      });
      el.addEventListener("pointerup", function () {
        if (!dragging) return;
        dragging = false; el.classList.remove("dragging");
        if (!moved) openNodeModal(nodes[el._idx]);
      });
      el.addEventListener("pointercancel", function () {
        dragging = false; el.classList.remove("dragging");
      });
    });

    function openNodeModal(n) {
      openModal(n.title, '<p class="modal-num">步骤 ' + (n.idx) + "</p><p>" + esc(n.detail) + "</p>");
    }

    redraw();
    window.addEventListener("resize", redraw);
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
      if (e.target.closest(".source-name")) return; // 点标题 -> 跳外链
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
