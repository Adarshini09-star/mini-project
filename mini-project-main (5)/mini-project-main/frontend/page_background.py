"""Full-page "BOT TRAFFIC FORECAST" background with moving code rain and a cream / black switch.

The title is drawn as huge SVG text (BOT / TRAFFIC / FORECAST) on a fixed layer behind the whole page, so it is crisp and
readable at any screen size. Falling binary code (Canvas2D) moves over the WHOLE background and lights up brighter where it
passes through the title letters. Page content sits on a translucent panel on top of both. It is decorative only: it never
shows forecast values and never blocks clicks (pointer-events: none).

Light/black switch: Streamlit cannot change its theme from Python, but it remembers the chosen theme in the browser.
render(switch_to=...) writes that choice and reloads the page once, so tables and inputs change colour together with the
background. The two palettes live in .streamlit/config.toml ([theme.light] cream, [theme.dark] black).

Streamlit shows custom HTML in an iframe that cannot draw outside its own box, so the small iframe below only hands a
script to the main page (same origin) and hides itself. The script replaces any earlier copy, so reruns never stack up.

Used from app.py:   import page_background as PB; PB.render(dark=..., switch_to=...)
"""
import json

TITLE_LINES = ["BOT", "TRAFFIC", "FORECAST"]

PALETTES = {
    "light": {"bg": "#FAF6EC", "ink": "#3F6B3A", "inkOpacity": 0.34, "panel": "250,246,236", "panelOpacity": 0.38,
              "rain": "#2F6B35", "head": "#123D18"},
    "dark": {"bg": "#000000", "ink": "#3DDC84", "inkOpacity": 0.50, "panel": "0,0,0", "panelOpacity": 0.38,
             "rain": "#00FF66", "head": "#DCFFE6"},
}

# Falling code: binary glyphs, cell size in px (12 on phones), trail length in cells, strength 0-100, flicker 0-100.
RAIN = {"cellSize": 16, "charSet": "01", "trail": 20, "rainOpacity": 80, "animSpeed": 100, "animIntensity": 60}

# Runs in the MAIN page. Config is filled in as JSON.
_PAGE_JS = r"""
(function () {
  "use strict";
  var C = __CONFIG__, doc = document, P = C.palette;
  if (window.__pageBgStop) { try { window.__pageBgStop(); } catch (e) {} }
  ["page-bg-layer", "page-bg-rain", "page-bg-css"].forEach(function (id) { var o = doc.getElementById(id); if (o) o.remove(); });

  var css = doc.createElement("style"); css.id = "page-bg-css";
  css.textContent =
    "html,body{background:" + P.bg + " !important}" +
    ".stApp,[data-testid='stAppViewContainer'],[data-testid='stMain'],[data-testid='stHeader']{background:transparent !important}" +
    "[data-testid='stMainBlockContainer'],.block-container{background:rgba(" + P.panel + "," + P.panelOpacity + ");" +
    "border-radius:14px;padding:2rem 2.2rem !important;margin-top:1.2rem}" +
    "#page-bg-layer{position:fixed;top:0;height:100vh;pointer-events:none;z-index:-1;overflow:hidden}" +
    "#page-bg-layer svg{width:100%;height:100%;display:block}" +
    "#page-bg-rain{position:fixed;left:0;top:0;width:100vw;height:100vh;pointer-events:none;z-index:-1}";
  doc.head.appendChild(css);

  var ns = "http://www.w3.org/2000/svg", FONT = "'Segoe UI','Helvetica Neue',Arial,sans-serif";
  var layer = doc.createElement("div"); layer.id = "page-bg-layer"; layer.setAttribute("aria-hidden", "true");
  var svg = doc.createElementNS(ns, "svg"); layer.appendChild(svg);
  var cv = doc.createElement("canvas"); cv.id = "page-bg-rain"; cv.setAttribute("aria-hidden", "true");
  doc.body.insertBefore(layer, doc.body.firstChild); doc.body.insertBefore(cv, layer.nextSibling);   // rain paints above the title
  var ctx = cv.getContext("2d"), meas = doc.createElement("canvas").getContext("2d");

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var running = true, raf = 0, last = 0, timer = 0;
  var vw = 0, vh = 0, dpr = 1, cs = C.cellSize, cols = 0, rows = 0, heads = null, speeds = null, glyph = null, inL = null;

  // Title geometry: as big as fits inside the MAIN area (the sidebar would hide part of it), letters undistorted.
  function geom() {
    var main = doc.querySelector("[data-testid='stMain']"), r = main ? main.getBoundingClientRect() : { left: 0, width: window.innerWidth };
    var W = Math.max(200, r.width), H = window.innerHeight, n = C.lines.length;
    meas.font = "900 100px " + FONT;
    var widest = 1; C.lines.forEach(function (l) { widest = Math.max(widest, meas.measureText(l).width); });
    var f = Math.min(W * 0.96 / widest * 100, H / (n * 0.95)), lh = f * 0.95, capH = f * 0.72;
    return { left: r.left, W: W, H: H, f: f, lh: lh, capH: capH, y0: (H - lh * n) / 2 };
  }
  function baseline(g, i) { return g.y0 + g.lh * i + g.lh / 2 + g.capH / 2; }

  function drawTitle(g) {
    layer.style.left = g.left + "px"; layer.style.width = g.W + "px";
    svg.setAttribute("viewBox", "0 0 " + g.W + " " + g.H);
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    C.lines.forEach(function (line, i) {
      var t = doc.createElementNS(ns, "text");
      t.setAttribute("x", String(g.W / 2)); t.setAttribute("y", String(baseline(g, i)));
      t.setAttribute("text-anchor", "middle"); t.setAttribute("font-size", String(g.f)); t.setAttribute("font-weight", "900");
      t.setAttribute("font-family", FONT); t.setAttribute("fill", P.ink); t.setAttribute("fill-opacity", String(P.inkOpacity));
      t.textContent = line; svg.appendChild(t);
    });
  }

  // Which rain cells sit inside the title letters (they light up brighter when rain passes through).
  function buildMask(g) {
    var mc = doc.createElement("canvas"); mc.width = vw; mc.height = vh;
    var m = mc.getContext("2d", { willReadFrequently: true });
    m.fillStyle = "#fff"; m.textAlign = "center"; m.textBaseline = "alphabetic"; m.font = "900 " + g.f + "px " + FONT;
    C.lines.forEach(function (line, i) { m.fillText(line, g.left + g.W / 2, baseline(g, i)); });
    var d = m.getImageData(0, 0, vw, vh).data;
    inL = new Uint8Array(cols * rows);
    for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++) {
      var x = Math.min(vw - 1, Math.floor(c * cs + cs / 2)), y = Math.min(vh - 1, Math.floor(r * cs + cs / 2));
      inL[r * cols + c] = d[(y * vw + x) * 4 + 3] > 128 ? 1 : 0;
    }
  }

  function setup() {
    vw = window.innerWidth; vh = window.innerHeight; dpr = Math.min(2, window.devicePixelRatio || 1);
    cs = vw < 600 ? Math.min(C.cellSize, 12) : C.cellSize;
    cv.width = Math.round(vw * dpr); cv.height = Math.round(vh * dpr);
    cols = Math.ceil(vw / cs); rows = Math.ceil(vh / cs);
    heads = new Float32Array(cols * 2); speeds = new Float32Array(cols); glyph = new Uint8Array(cols * rows);
    for (var c = 0; c < cols; c++) { heads[c] = Math.random() * (rows + C.trail); heads[cols + c] = heads[c] + (rows + C.trail) / 2; speeds[c] = 4 + Math.random() * 9; }
    for (var i = 0; i < glyph.length; i++) glyph[i] = Math.random() < 0.5 ? 0 : 1;
    var g = geom(); drawTitle(g); buildMask(g);
    frame(performance.now(), true);
  }

  function frame(t, still) {
    var speed = C.animSpeed / 100, inten = C.animIntensity / 100, time = t / 1000, len = C.trail, base = C.rainOpacity / 100;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, vw, vh);
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.font = Math.round(cs * 0.9) + "px 'Consolas','Courier New',monospace";
    for (var c = 0; c < cols; c++) for (var drop = 0; drop < 2; drop++) {        // two staggered drops per column = denser rain
      var head = still ? rows * (0.2 + 0.6 * (((c + drop * 53) * 37) % 100) / 100) : (heads[drop * cols + c] + time * speeds[c] * speed) % (rows + len + 6);
      var h = Math.floor(head);
      for (var k = 0; k < len; k++) {
        var r = h - k; if (r < 0 || r >= rows) continue;
        var idx = r * cols + c, a = Math.pow(1 - k / len, 1.5) * base;
        if (!still) a *= 1 - inten * 0.5 * Math.random();                 // flicker
        if (inL[idx]) a = Math.min(1, a * 2.4 + 0.1);                     // lights up inside the title letters
        if (a < 0.03) continue;
        if (!still && Math.random() < 0.03) glyph[idx] ^= 1;               // glyphs change as they fall
        ctx.globalAlpha = Math.min(1, a);
        ctx.fillStyle = k === 0 ? P.head : P.rain;
        ctx.fillText(C.charSet.charAt(glyph[idx]), c * cs + cs / 2, r * cs + cs / 2);
      }
    }
    ctx.globalAlpha = 0.22; ctx.fillStyle = P.rain;                       // faint binary fills the letters between drops
    for (var q = 0; q < inL.length; q++) if (inL[q]) ctx.fillText(C.charSet.charAt(glyph[q]), (q % cols) * cs + cs / 2, Math.floor(q / cols) * cs + cs / 2);
    ctx.globalAlpha = 1;
  }

  function loop(t) {
    if (!running) return;
    if (t - last > 1000 / 30) { last = t; frame(t, false); }               // ~30 fps keeps the page light
    raf = requestAnimationFrame(loop);
  }
  function onVis() { running = !doc.hidden; if (running && !reduce) raf = requestAnimationFrame(loop); }
  function relayout() { clearTimeout(timer); timer = setTimeout(setup, 120); }

  setup();
  if (!reduce) raf = requestAnimationFrame(loop);                          // reduced-motion users get one still frame
  var main0 = doc.querySelector("[data-testid='stMain']"), ro = null;
  if (window.ResizeObserver && main0) { ro = new ResizeObserver(relayout); ro.observe(main0); }
  window.addEventListener("resize", relayout); doc.addEventListener("visibilitychange", onVis);

  window.__pageBgStop = function () {                                      // cleanup so a rerun never stacks animations
    running = false; cancelAnimationFrame(raf); clearTimeout(timer); if (ro) ro.disconnect();
    window.removeEventListener("resize", relayout); doc.removeEventListener("visibilitychange", onVis);
  };

  // Theme switch: Streamlit remembers its theme in localStorage; set it once and reload so widgets change colour too.
  if (C.switchTo) {
    try {
      var key = "stActiveTheme-" + window.location.pathname + "-v2", want = C.switchTo === "dark" ? "Dark" : "Light";
      if (window.localStorage.getItem(key) !== JSON.stringify(want)) {
        window.localStorage.setItem(key, JSON.stringify(want));
        window.location.reload();
      }
    } catch (e) { /* storage blocked: the background still changes, only the widgets keep the old colours */ }
  }
})();
"""

_LOADER = r"""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:transparent">
<script>
(function () {
  try {
    var code = __PAGE_JS__;
    var p = window.parent, s = p.document.createElement("script");
    s.textContent = code; p.document.head.appendChild(s); s.remove();
    var box = window.frameElement && window.frameElement.closest("[data-testid='stElementContainer']");
    if (box) { box.style.display = "none"; }
  } catch (e) { /* no access to the main page: the dashboard simply has a plain background */ }
})();
</script></body></html>"""


def page_script(dark=False, switch_to=None, lines=None):
    cfg = dict(RAIN, palette=PALETTES["dark" if dark else "light"], lines=list(lines or TITLE_LINES),
               switchTo=switch_to if switch_to in ("light", "dark") else None)
    return _PAGE_JS.replace("__CONFIG__", json.dumps(cfg))


def build_html(dark=False, switch_to=None, lines=None):
    """Loader iframe HTML. The page script is embedded as a JSON string; '</' is escaped so it cannot close the tag."""
    literal = json.dumps(page_script(dark, switch_to, lines)).replace("</", "<\\/")
    return _LOADER.replace("__PAGE_JS__", literal)


def render(dark=False, switch_to=None):
    """Streamlit 1.67 deprecates components.v1.html in favour of st.iframe; use whichever exists."""
    import streamlit as st
    html = build_html(dark, switch_to)
    if hasattr(st, "iframe"):
        st.iframe(html, height=1)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=1)
