"""Cream / black page switch.

Streamlit cannot change its theme from Python, but it remembers the chosen theme in the browser. render(switch_to=...)
writes that choice and reloads the page once, so the background, tables and inputs all change together. Both palettes
live in .streamlit/config.toml ([theme.light] cream, [theme.dark] black).

Streamlit shows custom HTML in an iframe, so this tiny iframe hands a script to the main page (same origin) and hides itself.

Used from app.py:   import theme_switch as TS; TS.render(switch_to=...)
"""
import json

_PAGE_JS = r"""
(function () {
  try {
    var want = __WANT__, key = "stActiveTheme-" + window.location.pathname + "-v2";
    if (window.localStorage.getItem(key) !== JSON.stringify(want)) {
      window.localStorage.setItem(key, JSON.stringify(want));
      window.location.reload();
    }
  } catch (e) { /* storage blocked: the theme just stays as it is */ }
})();
"""

_LOADER = r"""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:transparent">
<script>
(function () {
  try {
    var code = __PAGE_JS__;
    var p = window.parent, s = p.document.createElement("script");
    s.textContent = code; p.document.head.appendChild(s); s.remove();
  } catch (e) { /* no access to the main page */ }
  try {
    var box = window.frameElement && window.frameElement.closest("[data-testid='stElementContainer']");
    if (box) { box.style.display = "none"; }
  } catch (e) {}
})();
</script></body></html>"""


def page_script(switch_to):
    """The script for the main page, or None when there is nothing to switch."""
    if switch_to not in ("light", "dark"):
        return None
    return _PAGE_JS.replace("__WANT__", json.dumps("Dark" if switch_to == "dark" else "Light"))


def build_html(switch_to):
    js = page_script(switch_to)
    if js is None:
        return None
    return _LOADER.replace("__PAGE_JS__", json.dumps(js).replace("</", "<\\/"))


def render(switch_to=None):
    """Does nothing unless the person just flipped the switch."""
    html = build_html(switch_to)
    if html is None:
        return
    import streamlit as st
    if hasattr(st, "iframe"):
        st.iframe(html, height=1)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=1)
