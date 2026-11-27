"""Classic matrix-style banner for the top of the dashboard (Canvas2D, runs in the browser).

The title is drawn as real, crisp serif capitals (ivory with a soft green glow and a thin double frame), so every letter is easy to
read at any window width. A faint, sparse texture of green 0s and 1s with a few thin falling trails fills the dark background and
fades out around the title, so the letters are never crowded. The banner is always dark, so it looks the same on the cream page and
on the black page. Decorative only: it never shows forecast values.

Tune it in CONFIG: wording (title), texture (fill, rainDensity, charSet, cellSize), colours, vignette and height.
"""
import json

CONFIG = {
    "title": "BOT TRAFFIC FORECAST",
    "charSet": "01", "cellSize": 10,
    "fill": 26,            # % of background cells that show a faint digit
    "rainDensity": 10,     # % of columns that carry a thin falling trail
    "animSpeed": 100,
    "tint": "#00ff66", "bg": "#020a05", "textColor": "#E9FFF0",
    "vignette": 30,
    "height": 160,
}


def build_html(config=None):
    cfg = dict(CONFIG, **(config or {}))
    payload = json.dumps(cfg).replace("</", "<\\/")      # no config text can close the script tag
    return _TEMPLATE.replace("__CONFIG__", payload).replace("__HEIGHT__", str(int(cfg["height"])))


def render():
    """Streamlit 1.67 deprecates components.v1.html in favour of st.iframe; use whichever exists."""
    import streamlit as st
    html, height = build_html(), int(CONFIG["height"]) + 4
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=height)


_TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  html,body{margin:0;padding:0;background:transparent;overflow:hidden}
  #wrap{position:relative;width:100%;height:__HEIGHT__px;border-radius:8px;overflow:hidden;background:#020a05;
        box-shadow:0 0 0 1px rgba(0,255,102,0.30)}
  canvas{display:block;width:100%;height:100%}
</style></head>
<body><div id="wrap"><canvas id="c" role="img" aria-label="Bot Traffic Forecast"></canvas></div>
<script>
(function(){
"use strict";
var C = __CONFIG__;
var wrap = document.getElementById("wrap"), cv = document.getElementById("c"), ctx = cv.getContext("2d");
var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
var SERIF = "Georgia,'Times New Roman',Times,serif";
var W = 0, H = 0, dpr = 1, cs = C.cellSize, cols = 0, rows = 0, layout = null;
var glyph = null, base = null, plate = null, heads = null, speeds = null, rain = null;
var running = true, last = 0, timer = 0;
var TINT = (function () { var n = parseInt(String(C.tint).replace("#", ""), 16); return isNaN(n) ? [0, 255, 102] : [n >> 16 & 255, n >> 8 & 255, n & 255]; })();

function layoutTitle() {
  // Real text, spaced letter by letter. One line on wide screens, two lines on narrow ones; the size is measured so it always fits.
  var narrow = W < 560, lines = narrow ? ["BOT TRAFFIC", "FORECAST"] : [C.title];
  var fs = Math.min(H * (narrow ? 0.24 : 0.36), 64), sp = 0, widths = [], maxW = W * 0.86;
  function measure() {
    ctx.font = "700 " + fs + "px " + SERIF; sp = fs * 0.14; widths = [];
    for (var li = 0; li < lines.length; li++) {
      var w = 0; for (var i = 0; i < lines[li].length; i++) w += ctx.measureText(lines[li].charAt(i)).width + sp;
      widths.push(w - sp);
    }
  }
  measure();
  var widest = Math.max.apply(null, widths);
  if (widest > maxW) { fs *= maxW / widest; measure(); widest = Math.max.apply(null, widths); }
  var lh = fs * 1.25, y0 = H / 2 - lh * lines.length / 2 + lh / 2, out = { fs: fs, lines: [], cx: W / 2, cy: H / 2, hw: widest / 2, hh: lh * lines.length / 2 };
  for (var l = 0; l < lines.length; l++) {
    var chars = [], x = W / 2 - widths[l] / 2;
    for (var k = 0; k < lines[l].length; k++) {
      var ch = lines[l].charAt(k), cw = ctx.measureText(ch).width;
      chars.push({ ch: ch, x: x + cw / 2 }); x += cw + sp;
    }
    out.lines.push({ y: y0 + l * lh, chars: chars });
  }
  return out;
}

function buildGrid() {
  // Faint digits only on some cells, and none at all behind the title (an ellipse around it stays empty, then fades in).
  cols = Math.max(1, Math.floor(W / cs)); rows = Math.max(1, Math.floor(H / cs));
  var n = cols * rows, L = layout;
  glyph = new Uint8Array(n); base = new Float32Array(n); plate = new Float32Array(n);
  var rx = L.hw + cs * 4, ry = L.hh + cs * 2.5;
  for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++) {
    var i = r * cols + c, ex = (c * cs + cs / 2 - L.cx) / rx, ey = (r * cs + cs / 2 - L.cy) / ry, e = Math.sqrt(ex * ex + ey * ey);
    glyph[i] = Math.random() < 0.5 ? 0 : 1;
    base[i] = Math.random() < C.fill / 100 ? 0.08 + 0.08 * Math.random() : 0;
    plate[i] = e < 0.9 ? 0 : Math.min(1, (e - 0.9) / 0.4);
    if (c * cs < 18 || r * cs < 18 || (c + 1) * cs > W - 18 || (r + 1) * cs > H - 18) plate[i] = 0;      // keep the frame lines clean
  }
  heads = new Float32Array(cols); speeds = new Float32Array(cols); rain = new Uint8Array(cols);
  for (var q = 0; q < cols; q++) { heads[q] = Math.random() * (rows + 10); speeds[q] = 5 + Math.random() * 9; rain[q] = Math.random() < C.rainDensity / 100 ? 1 : 0; }
}

function resize() {
  var rect = wrap.getBoundingClientRect();
  W = Math.max(1, Math.round(rect.width)); H = Math.max(1, Math.round(rect.height));
  dpr = Math.min(2, window.devicePixelRatio || 1);
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  cs = Math.max(6, Math.min(C.cellSize, Math.round(W / 100)));
  layout = layoutTitle(); buildGrid(); frame(performance.now(), true);
}

function drawTexture(time, still) {
  var speed = C.animSpeed / 100, t = TINT;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.font = Math.round(cs * 0.9) + "px 'Consolas','Courier New',monospace";          // a digit is never bigger than its cell
  for (var c = 0; c < cols; c++) {
    var head = still ? rows * 0.6 : (heads[c] + time * speeds[c] * speed) % (rows + 10);
    for (var r = 0; r < rows; r++) {
      var i = r * cols + c, a = base[i], d = head - r, isHead = false;
      if (rain[c] && d >= 0 && d < 10) { a = Math.max(a, 0.10 + 0.40 * Math.pow(1 - d / 10, 1.6)); if (d < 1) { a = 0.7; isHead = true; } }
      a *= plate[i];
      if (a < 0.04) continue;
      if (!still && Math.random() < 0.002) glyph[i] ^= 1;
      ctx.fillStyle = isHead ? "rgba(200,255,220," + a + ")" : "rgba(" + t[0] + "," + t[1] + "," + t[2] + "," + a + ")";
      ctx.fillText(C.charSet.charAt(glyph[i]), c * cs + cs / 2, r * cs + cs / 2);
    }
  }
}

function drawTitle() {
  var L = layout;
  ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.lineJoin = "round";
  ctx.font = "700 " + L.fs + "px " + SERIF;
  ctx.shadowColor = "rgba(" + TINT[0] + "," + TINT[1] + "," + TINT[2] + ",0.55)"; ctx.shadowBlur = L.fs * 0.45;      // soft green glow
  ctx.fillStyle = C.textColor;
  var li, k, ln;
  for (li = 0; li < L.lines.length; li++) { ln = L.lines[li]; for (k = 0; k < ln.chars.length; k++) ctx.fillText(ln.chars[k].ch, ln.chars[k].x, ln.y); }
  ctx.shadowBlur = 0; ctx.shadowColor = "rgba(0,0,0,0)";
  ctx.strokeStyle = "rgba(0,30,12,0.85)"; ctx.lineWidth = Math.max(1, L.fs * 0.05);                                  // crisp dark edge
  for (li = 0; li < L.lines.length; li++) { ln = L.lines[li]; for (k = 0; k < ln.chars.length; k++) ctx.strokeText(ln.chars[k].ch, ln.chars[k].x, ln.y); }
  for (li = 0; li < L.lines.length; li++) { ln = L.lines[li]; for (k = 0; k < ln.chars.length; k++) ctx.fillText(ln.chars[k].ch, ln.chars[k].x, ln.y); }
}

function drawFrame() {                                                                                          // thin double rule
  var t = TINT;
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(" + t[0] + "," + t[1] + "," + t[2] + ",0.45)"; ctx.strokeRect(8.5, 8.5, W - 17, H - 17);
  ctx.strokeStyle = "rgba(" + t[0] + "," + t[1] + "," + t[2] + ",0.20)"; ctx.strokeRect(13.5, 13.5, W - 27, H - 27);
}

function frame(t, still) {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  drawTexture(t / 1000, still);
  if (C.vignette) {
    var vg = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.4, W / 2, H / 2, Math.max(W, H) * 0.75);
    vg.addColorStop(0, "rgba(0,0,0,0)"); vg.addColorStop(1, "rgba(0,0,0," + (C.vignette / 100) + ")");
    ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
  }
  drawTitle(); drawFrame();
}

function loop(t) {
  if (!running) return;
  if (t - last > 1000 / 30) { last = t; frame(t, false); }   // ~30 fps keeps the page light
  requestAnimationFrame(loop);
}
function relayout() { clearTimeout(timer); timer = setTimeout(resize, 120); }

resize();
if (!reduce) requestAnimationFrame(loop);                   // reduced-motion users get one still frame
if (window.ResizeObserver) new ResizeObserver(relayout).observe(wrap); else window.addEventListener("resize", relayout);
document.addEventListener("visibilitychange", function () {
  running = !document.hidden; if (running && !reduce) requestAnimationFrame(loop);
});
})();
</script></body></html>
"""
