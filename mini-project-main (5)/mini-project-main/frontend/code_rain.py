"""Full-page "Code Rain" background (Canvas2D) for the dashboard.

Falling binary code is drawn on a fixed canvas BEHIND the whole page (z-index -1). Page content sits on top, on a
slightly dark translucent panel so every table, button and warning stays readable. Purely decorative: it never touches
forecast values, never intercepts clicks (pointer-events: none) and does not run for people who ask for reduced motion
(they get one still frame).

How it works: Streamlit shows custom HTML inside an iframe, which cannot draw outside its own box. So the tiny iframe
below only injects the script and styles into the main page (same origin) and hides itself. The injected script
replaces any earlier copy of itself, so reruns never stack up animations.

Used from app.py:   import code_rain; code_rain.render()
"""
import json

# Look settings (the spec's "characters" render mode with the matrix rain, binary charset).
CONFIG = {
    "cellSize": 16,          # px per glyph cell on large screens (12 on phones)
    "charSet": "01",
    "tint": "#00ff66",       # glyph colour
    "bg": "#020a05",         # solid page background colour behind the rain
    "rainOpacity": 55,       # 0-100: overall strength of the rain (lower = calmer page)
    "trail": 16,             # length of each falling trail, in cells
    "animSpeed": 100,        # 100 = normal
    "animIntensity": 60,     # 0-100: strength of the flicker
    "scanLines": 28,         # 0-100
    "vignette": 38,          # 0-100
    "panelOpacity": 74,      # 0-100: darkness of the panel behind the page content (readability)
}

# Runs in the MAIN page. Never contains the closing script tag. Config is filled in as JSON.
_PAGE_JS = r"""
(function () {
  "use strict";
  var C = __CONFIG__;
  if (window.__codeRainStop) { try { window.__codeRainStop(); } catch (e) {} }
  var doc = document;
  ["code-rain-bg", "code-rain-fx", "code-rain-css"].forEach(function (id) { var o = doc.getElementById(id); if (o) o.remove(); });

  var css = doc.createElement("style"); css.id = "code-rain-css";
  css.textContent =
    "html,body{background:" + C.bg + " !important}" +
    ".stApp,[data-testid='stAppViewContainer'],[data-testid='stMain'],[data-testid='stHeader']{background:transparent !important}" +
    "[data-testid='stMainBlockContainer'],.block-container{background:rgba(2,10,5," + (C.panelOpacity / 100) + ");" +
    "border-radius:14px;padding:2rem 2.2rem !important;margin-top:1.2rem}" +
    "[data-testid='stSidebar']{background:rgba(5,22,12,0.92) !important}" +
    "#code-rain-bg,#code-rain-fx{position:fixed;left:0;top:0;width:100vw;height:100vh;pointer-events:none;z-index:-1}" +
    "#code-rain-fx{background:" +
      "repeating-linear-gradient(to bottom,rgba(0,0,0," + (C.scanLines / 100 * 0.6) + ") 0,rgba(0,0,0," + (C.scanLines / 100 * 0.6) + ") 1px,transparent 1px,transparent 3px)," +
      "radial-gradient(ellipse at center,rgba(0,0,0,0) 45%,rgba(0,0,0," + Math.min(1, C.vignette / 100 * 1.3) + ") 100%)}";
  doc.head.appendChild(css);

  var cv = doc.createElement("canvas"); cv.id = "code-rain-bg"; cv.setAttribute("aria-hidden", "true");
  var fx = doc.createElement("div"); fx.id = "code-rain-fx"; fx.setAttribute("aria-hidden", "true");
  doc.body.insertBefore(fx, doc.body.firstChild); doc.body.insertBefore(cv, doc.body.firstChild);
  var ctx = cv.getContext("2d");

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var W = 0, H = 0, dpr = 1, cs = C.cellSize, cols = 0, rows = 0, heads = null, speeds = null, glyph = null;
  var running = true, raf = 0, last = 0;

  function setup() {
    W = window.innerWidth; H = window.innerHeight; dpr = Math.min(2, window.devicePixelRatio || 1);
    cs = W < 600 ? Math.min(C.cellSize, 12) : C.cellSize;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    cols = Math.ceil(W / cs); rows = Math.ceil(H / cs);
    heads = new Float32Array(cols); speeds = new Float32Array(cols); glyph = new Uint8Array(cols * rows);
    for (var c = 0; c < cols; c++) { heads[c] = Math.random() * (rows + C.trail); speeds[c] = 4 + Math.random() * 9; }
    for (var i = 0; i < glyph.length; i++) glyph[i] = Math.random() < 0.5 ? 0 : 1;
    frame(performance.now(), true);
  }

  function frame(t, still) {
    var speed = C.animSpeed / 100, inten = C.animIntensity / 100, time = t / 1000, len = C.trail, base = C.rainOpacity / 100;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = Math.round(cs * 0.9) + "px 'Consolas','Courier New',monospace";
    for (var c = 0; c < cols; c++) {
      var head = still ? rows * (0.25 + 0.5 * ((c * 37) % 100) / 100) : (heads[c] + time * speeds[c] * speed) % (rows + len + 6);
      var h = Math.floor(head);
      for (var k = 0; k < len; k++) {
        var r = h - k; if (r < 0 || r >= rows) continue;
        var a = Math.pow(1 - k / len, 1.5) * base;
        if (!still) a *= 1 - inten * 0.5 * Math.random();            // flicker
        if (a < 0.03) continue;
        var idx = r * cols + c;
        if (!still && Math.random() < 0.03) glyph[idx] ^= 1;          // glyphs change as they fall
        ctx.fillStyle = k === 0 ? "rgba(220,255,230," + Math.min(1, a * 1.6) + ")" : C.tint;
        ctx.globalAlpha = k === 0 ? 1 : Math.min(1, a);
        ctx.fillText(C.charSet.charAt(glyph[idx]), c * cs + cs / 2, r * cs + cs / 2);
      }
    }
    ctx.globalAlpha = 1;
  }

  function loop(t) {
    if (!running) return;
    if (t - last > 1000 / 30) { last = t; frame(t, false); }         // ~30 fps keeps the page light
    raf = requestAnimationFrame(loop);
  }
  function onVis() { running = !doc.hidden; if (running && !reduce) raf = requestAnimationFrame(loop); }
  var rt = 0;
  function onResize() { clearTimeout(rt); rt = setTimeout(setup, 150); }

  window.addEventListener("resize", onResize);
  doc.addEventListener("visibilitychange", onVis);
  setup();
  if (!reduce) raf = requestAnimationFrame(loop);

  window.__codeRainStop = function () {                              // cleanup so a rerun never stacks animations
    running = false; cancelAnimationFrame(raf); clearTimeout(rt);
    window.removeEventListener("resize", onResize); doc.removeEventListener("visibilitychange", onVis);
    [cv, fx, css].forEach(function (n) { if (n && n.parentNode) n.parentNode.removeChild(n); });
  };
})();
"""

# Runs inside Streamlit's small iframe: hands the page script to the parent page, then hides its own container.
_LOADER = r"""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:transparent">
<script>
(function () {
  try {
    var code = __PAGE_JS__;
    var p = window.parent, s = p.document.createElement("script");
    s.textContent = code; p.document.head.appendChild(s); s.remove();
    var box = window.frameElement && window.frameElement.closest("[data-testid='stElementContainer']");
    if (box) { box.style.display = "none"; }
  } catch (e) { /* no access to the parent page: the dashboard simply has no animated background */ }
})();
</script></body></html>"""


def page_script(config=None):
    cfg = dict(CONFIG, **(config or {}))
    return _PAGE_JS.replace("__CONFIG__", json.dumps(cfg))


def build_html(config=None):
    """The loader iframe's HTML. The page script is embedded as a JSON string; '</' is escaped so it cannot close the tag."""
    literal = json.dumps(page_script(config)).replace("</", "<\\/")
    return _LOADER.replace("__PAGE_JS__", literal)


def render():
    """Call once near the top of app.py. Streamlit 1.67 deprecates components.v1.html in favour of st.iframe."""
    import streamlit as st
    html = build_html()
    if hasattr(st, "iframe"):
        st.iframe(html, height=1)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=1)
