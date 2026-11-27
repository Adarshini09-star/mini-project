"""Page-flow check for app.py. Streamlit is replaced by a recording stand-in, so this checks the page LOGIC (what is shown, when,
and that nothing crashes), not how it looks. Run from the frontend/ folder:   python tests/app_flow_check.py
Needs ../predict_lstm.py and ../docs/API_CONTRACT.md (it uses the same stand-in backend as the unit tests)."""
import sys, types, threading, runpy
from pathlib import Path
FRONT=Path(__file__).resolve().parents[1]; B=str(FRONT.parent)
sys.path[:0]=[str(FRONT), str(FRONT/"tests"), B]
import pandas as pd, numpy as np
import test_api_client as T, validation as V

class Ctx:
    def __enter__(self): return self
    def __exit__(self,*a): return False
def make_st(cfg, state, log):
    st=types.ModuleType("streamlit"); st.session_state=state
    class Col(Ctx):
        def metric(self,l,v,**k): log.append(("metric",l,v,k))
    class SB:
        def toggle(self,l,value=False,key=None,**k): return state.get("black_mode",False) if key=="black_mode" else cfg.get("demo",False)
        def text_input(self,l,value="",**k): return cfg.get("url") or value
        def caption(self,t): log.append(("sb_caption",t))
    st.sidebar=SB(); st.set_page_config=lambda **k:None
    for n in ("title","caption","warning","error","subheader","write","json","divider","info","success","dataframe","bar_chart","line_chart"):
        setattr(st,n,(lambda n:lambda *a,**k:log.append((n,a[0] if a else None,k)))(n))
    st.markdown=lambda t,**k: log.append(("markdown",t,k))
    st.tabs=lambda labels: [Ctx() for _ in labels]
    st.context=types.SimpleNamespace(theme=types.SimpleNamespace(type=cfg.get("theme","light")))   # used by the cream / black switch
    st.iframe=lambda html,**k: log.append(("iframe",html,k))                                       # banner and theme switch draw through this
    st.metric=lambda l,v,**k: log.append(("metric",l,v,k))
    st.table=lambda d,**k: log.append(("table",d,k))
    st.columns=lambda n:[Col() for _ in range(n if isinstance(n,int) else len(n))]
    st.container=lambda: Ctx(); st.spinner=lambda *a,**k:(log.append(("spinner",a[0] if a else None)) or Ctx()); st.expander=lambda *a,**k:Ctx()
    st.radio=lambda l,opts,**k: opts[1] if cfg.get("csv") is not None else opts[0]
    st.selectbox=lambda l,opts,**k: cfg.get("preset", list(opts)[0])
    st.text_input=lambda l,value="",**k: cfg.get("start", value) if l.startswith("Time label") else (cfg.get("url") or value)
    def data_editor(df,**k):
        d=df.copy()
        for (r,c),v in cfg.get("edits",{}).items(): d.iloc[r,d.columns.get_loc(c)]=v
        return d
    st.data_editor=data_editor
    class Up:
        def __init__(s,b): s.b=b
        def getvalue(s): return s.b
    st.file_uploader=lambda *a,**k: Up(cfg["csv"]) if cfg.get("csv") is not None else None
    def button(label,disabled=False,**k):
        log.append(("button",label,disabled)); return label in cfg.get("clicks",()) and not disabled
    st.button=button
    return st
def run(cfg,state=None):
    log=[]; state=state if state is not None else {}
    sys.modules["streamlit"]=make_st(cfg,state,log)
    runpy.run_path(str(FRONT/"app.py"),run_name="__main__"); return log,state
errs=lambda L:[x[1] for x in L if x[0]=="error"]
cards=lambda L:[x[1] for x in L if x[0]=="markdown" and "Forecast (t+1 min)" in x[1]]
gauges=lambda L:[x[1] for x in L if x[0]=="markdown" and "Model Disagreement:" in x[1] and "percentage points" in x[1] and "<div" in x[1]]
GET={"clicks":["Get forecast"]}
infos=lambda L:[x[1] for x in L if x[0]=="info"]
warns=lambda L:[x[1] for x in L if x[0]=="warning"]

print("1 demo: placeholders are labelled everywhere")
L,_=run(dict(GET,demo=True))
c=cards(L); assert len(c)==1 and c[0].count("[MOCK]")==2 and "0.00 %" in c[0] and "LOW" in c[0]
assert any("DEMO MODE" in e for e in errs(L))
assert any("Not shown for placeholder values" in x[1] for x in L if x[0]=="caption")
assert not any(x[0]=="write" and x[1].startswith("• Over the last") for x in L)         # no explanation text for placeholders
assert any("Low-state recall is about 0%" in i for i in infos(L))                         # Low notice under the card
assert any("MODEL NOT LOADED" in w for w in warns(L)) and any(x[0]=="warning" and x[2].get("icon")=="⚠️" for x in L)
assert gauges(L) and any(x[0]=="bar_chart" for x in L) and any(x[0]=="line_chart" for x in L)

srv=T.QuietServer(("127.0.0.1",0),T.Stub); threading.Thread(target=srv.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{srv.server_address[1]}"; T.Stub.mode="normal"; T.Stub.delay=0
print("2 stand-in backend (real validator): real-looking result, explanations, no MOCK tag")
L,state=run(dict(GET,url=url))
c=cards(L); assert len(c)==1 and "[MOCK]" not in c[0] and "19.12 %" in c[0] and "model status: PROVISIONAL" in c[0]
assert not any("DEMO MODE" in e or "SIMULATION" in e for e in errs(L))
lines=[x[1] for x in L if x[0]=="write" and x[1].startswith("• ")][:3]; assert "Over the last 5 minutes" in lines[0] and "3.0% to 4.0%" in lines[0] and "19.1%" in lines[1] and "agree closely" in lines[2], lines
assert any("Model Disagreement" in g for g in gauges(L))
print("   ", lines[1])
print("3 stale notice; details still use the window that was sent")
L,_=run(dict(preset="Busy traffic (example)",url=url),state)
assert any("earlier input values" in i for i in infos(L)) and len(cards(L))==1
w=[x[1] for x in L if x[0]=="write"]; assert any("3.0% to 4.0%" in t for t in w) and not any("45.0% to 56.0%" in t for t in w), w[:3]   # explains the window that was SENT, not the table now on screen
print("4 backend in MOCK mode: banner + tags, no explanation")
T.Stub.mode="mock"; L,_=run(dict(GET,url=url))
assert any("SIMULATION MODE ACTIVE" in e for e in errs(L)) and cards(L)[0].count("[MOCK]")==2
print("5 error: no card, no details, error shown")
T.Stub.mode="http500_json"; L,_=run(dict(GET,url=url))
assert not cards(L) and any("Backend service encountered an error" in e for e in errs(L)) and not gauges(L)
print("6 unreachable"); L,_=run(dict(GET,url="http://127.0.0.1:9")); assert not cards(L) and any("Cannot reach the backend" in e for e in errs(L))
print("7 invalid input: button disabled, nothing sent")
L,_=run(dict(GET,demo=True,edits={(0,"Total_Flows"):-4})); assert ("button","Get forecast",True) in L and not cards(L)
print("8 no forecast yet"); L,_=run(dict(demo=True)); assert not cards(L) and any("No forecast yet" in x[1] for x in L if x[0]=="caption")
print("9 CSV flow still works"); hdr="Timestamp,"+",".join(V.FEATURES)
rows=[f"2018-02-03 09:{i:02d}:00,{10+i},100,50,40,3000,2000,900" for i in range(6)]
T.Stub.mode="normal"; L,_=run(dict(GET,url=url,csv=(hdr+"\n"+"\n".join(rows)+"\n").encode())); assert len(cards(L))==1 and not errs(L)
print("10 markup handed to Streamlit is single-line")
for x in L:
    if x[0]=="markdown" and "<div" in x[1]: assert "\n" not in x[1] and x[2].get("unsafe_allow_html") is True
print("11 analytics tab: real numbers from the input, nothing before data exists")
L,_=run(dict(preset="Busy traffic (example)",demo=True))
m={x[1]:x[2] for x in L if x[0]=="metric"}
assert m["Bot share"]=="56.0 %" and m["Observed state (newest minute)"]=="High" and m["Total flows"]=="3,000", m
assert m["Average duration (bot flows)"]=="60,000.0" and m["Forward packets (bot flows)"]=="2,500"
assert any(x[0]=="metric" and len(x)>3 and x[1]=="Bot share" and x[3].get("delta")=="+4.0 pts" and x[3].get("delta_color")=="off" for x in L)   # 56 - 52
assert sum(1 for x in L if x[0]=="line_chart")==5 and any("Observed state is not" in str(x[1]) or "not a model prediction" in str(x[1]) for x in L if x[0]=="caption")
assert any(x[0]=="metric" and len(x)>3 and x[1]=="Total flows" and x[3].get("delta") is None for x in L)      # 3000 -> 3000: no arrow
assert any(x[0]=="metric" and len(x)>3 and x[1]=="Forward packets (bot flows)" and x[3].get("delta") is None for x in L)
L,_=run(dict(demo=True,start="tomorrow-ish")); assert any("No traffic data yet" in x[1] for x in L if x[0]=="info") and not any(x[0]=="metric" and x[1]=="Bot share" for x in L)
print("12 analytics fall back to the last forecast window when the input is invalid")
L,st2=run(dict(GET,demo=True)); L,_=run(dict(demo=True,start="tomorrow-ish"),st2)
assert any("current input is not valid" in str(x[1]) for x in L if x[0]=="caption") and any(x[0]=="metric" and x[1]=="Bot share" and x[2]=="4.0 %" for x in L)
print("13 About tab content is rendered")
sub=[x[1] for x in L if x[0]=="subheader"]; assert {"What this dashboard does","How the forecast is made","How to read the screen","What it does not do","The 7 input features","Limitations"} <= set(sub), sub
assert any(x[0]=="markdown" and x[1].startswith("| Column name |") and x[1].count("\n")==8 for x in L)      # the 7-feature table
assert any(x[0]=="caption" and x[1].startswith("Seed 42:") for x in run(dict(GET,demo=True))[0])                  # seed numbers under the chart
print("14 loading indicators and every warning shown")
L,_=run(dict(GET,demo=True)); assert ("spinner","Waiting for the forecast...") in L
L,_=run(dict(clicks=["Check backend connection"],demo=True)); assert ("spinner","Contacting the backend...") in L
T.Stub.mode="normal"; L,_=run(dict(GET,url=url))
shown=warns(L); missing=[w for w in T.SUCCESS_DOC["warnings"] if w not in shown]; assert not missing, missing
print("15 banner is drawn once; the theme switch does nothing by default")
L,st3=run(dict(demo=True)); fr=[x[1] for x in L if x[0]=="iframe"]
assert len(fr)==1 and "<canvas" in fr[0] and "C.subtitle" not in fr[0] and st3["black_mode"] is False, fr
print("16 theme switch: the chosen theme is written once, and the page still works")
L,st4=run(dict(GET,demo=True),{"theme_switch":"dark"}); fr=[x[1] for x in L if x[0]=="iframe"]
assert len(fr)==2 and "<canvas" in fr[0] and "stActiveTheme" in fr[1] and "Dark" in fr[1] and "theme_switch" not in st4 and len(cards(L))==1
L,st5=run(dict(demo=True,theme="dark")); assert st5["black_mode"] is True and len([x for x in L if x[0]=="iframe"])==1
print("17 changing Demo mode or the backend address makes an earlier forecast count as out of date")
L,st6=run(dict(GET,url="http://127.0.0.1:9"))                                    # a failed request without Demo mode
assert any("Cannot reach the backend" in e for e in errs(L)) and not any("earlier input values" in i for i in infos(L))
L,_=run(dict(demo=True),st6); assert any("earlier input values or settings" in i for i in infos(L))
L,_=run(dict(url=url),st6); assert any("earlier input values or settings" in i for i in infos(L))
print("18 every line chart is drawn with one distinct colour per series")
L,_=run(dict(GET,demo=True)); charts=[x for x in L if x[0]=="line_chart"]
assert len(charts)==6 and all(len(x[2]["color"])==len(x[1].columns) and len(set(x[2]["color"]))==len(x[2]["color"]) for x in charts), [x[2] for x in charts]
print("SMOKE OK"); srv.shutdown()
