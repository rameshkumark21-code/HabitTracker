import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import json, uuid

st.set_page_config(page_title="Habits", page_icon="🔥",
                   layout="centered", initial_sidebar_state="collapsed")

# ── DESIGN TOKENS ─────────────────────────────────────────────────────────────
C = {
    "bg":      "#111418", "surface": "#1c1f26", "s2": "#252930",
    "border":  "#2e3340", "text":    "#edf0f7", "muted": "#5c6680",
    "blue":    "#5b8dee", "green":   "#22d3a0", "red":   "#e84855",
    "amber":   "#f0a500", "streak":  "#f97316", "dim":   "rgba(91,141,238,0.10)",
}

# Category accent colours (drives icon circle bg + section label)
CAT_COLOR = {
    "Daily":                  C["blue"],
    "Nutrition & Movement":   C["green"],
    "Workout Days":           C["amber"],
    "Weekly":                 C["streak"],
}

SCOPES           = ["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "ClearSpend"
HABIT_HEADERS    = ["HabitID","Name","Icon","Category","Type",
                    "Target","TargetUnit","FreqType","WeekDay","Order","Active"]
LOG_HEADERS      = ["LogID","Date","HabitID","HabitName","Value"]
CATEGORIES       = ["Daily","Nutrition & Movement","Workout Days","Weekly"]

HABIT_SEEDS = [
    ["h01","500ml water on waking",   "💧","Daily",               "boolean","1",  "",      "daily","",  1,"TRUE"],
    ["h02","Morning mobility 15 min", "🤸","Daily",               "boolean","1",  "",      "daily","",  2,"TRUE"],
    ["h03","Protein-first breakfast", "🥚","Daily",               "boolean","1",  "",      "daily","",  3,"TRUE"],
    ["h04","Pre-sleep stretch",       "🌙","Daily",               "boolean","1",  "",      "daily","",  4,"TRUE"],
    ["h05","In bed by 12:30 AM",      "😴","Daily",               "boolean","1",  "",      "daily","",  5,"TRUE"],
    ["h06","1-Floor Rule (stairs)",   "🪜","Daily",               "boolean","1",  "",      "daily","",  6,"TRUE"],
    ["h07","50/5 Rule – breaks",      "⏱","Nutrition & Movement","numeric","5",  "breaks","daily","",  7,"TRUE"],
    ["h08","Protein intake",          "🥩","Nutrition & Movement","numeric","140","g",     "daily","",  8,"TRUE"],
    ["h09","Floors climbed",          "🗼","Nutrition & Movement","numeric","10", "floors","daily","",  9,"TRUE"],
    ["h10","Workout before 10 AM",    "🏋","Workout Days",        "boolean","1",  "",      "daily","", 10,"TRUE"],
    ["h11","Foam rolling done",       "🧹","Workout Days",        "boolean","1",  "",      "daily","", 11,"TRUE"],
    ["h12","Post-workout protein",    "🥤","Workout Days",        "boolean","1",  "",      "daily","", 12,"TRUE"],
    ["h13","Long walk 45-60 min",     "🚶","Weekly",              "boolean","1",  "",      "weekly","Sun",13,"TRUE"],
    ["h14","Flexibility / yoga",      "🧘","Weekly",              "boolean","1",  "",      "weekly","Sat",14,"TRUE"],
    ["h15","Weekly stair test",       "📊","Weekly",              "boolean","1",  "",      "weekly","Sun",15,"TRUE"],
]

# ═══════════════════════════════════════════════════════════════════════════════
#  DATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def iso_to_dmy(s): return datetime.strptime(s,"%Y-%m-%d").strftime("%d/%m/%Y")
def dmy_to_iso(s): return datetime.strptime(s,"%d/%m/%Y").strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════════════════════════════
#  SHEETS CONNECTION
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        json.loads(st.secrets["GOOGLE_CREDENTIALS"]), scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource
def get_ss():
    cl = get_client()
    try:    return cl.open(SPREADSHEET_NAME)
    except: return cl.create(SPREADSHEET_NAME)

def ensure_sheets():
    ss  = get_ss()
    ext = [ws.title for ws in ss.worksheets()]
    if "Habits" in ext:
        ws = ss.worksheet("Habits")
        if "Category" not in ws.row_values(1):
            ss.del_worksheet(ws); ext.remove("Habits")
    if "Habits" not in ext:
        ws = ss.add_worksheet("Habits", 200, len(HABIT_HEADERS))
        ws.append_row(HABIT_HEADERS)
        ws.format("1:1",{"textFormat":{"bold":True}})
        for s in HABIT_SEEDS: ws.append_row(s)
    if "HabitLogs" in ext:
        ws = ss.worksheet("HabitLogs")
        if "Value" not in ws.row_values(1):
            ss.del_worksheet(ws); ext.remove("HabitLogs")
    if "HabitLogs" not in ext:
        ws = ss.add_worksheet("HabitLogs", 10000, len(LOG_HEADERS))
        ws.append_row(LOG_HEADERS)
        ws.format("1:1",{"textFormat":{"bold":True}})

# ═══════════════════════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=20)
def load_habits():
    data = get_ss().worksheet("Habits").get_all_records()
    if not data: return pd.DataFrame(columns=HABIT_HEADERS)
    df = pd.DataFrame(data)
    df["Order"]  = pd.to_numeric(df["Order"],  errors="coerce").fillna(99).astype(int)
    df["Target"] = pd.to_numeric(df["Target"], errors="coerce").fillna(1)
    df["Active"] = df["Active"].astype(str).str.upper().isin(["TRUE","YES","1"])
    return df.sort_values("Order").reset_index(drop=True)

@st.cache_data(ttl=20)
def load_logs(days_back=90):
    data = get_ss().worksheet("HabitLogs").get_all_records()
    if not data: return pd.DataFrame(columns=LOG_HEADERS)
    df = pd.DataFrame(data)
    cutoff = (date.today()-timedelta(days=days_back)).isoformat()
    def keep(dmy):
        try:   return dmy_to_iso(str(dmy)) >= cutoff
        except: return False
    return df[df["Date"].apply(keep)].reset_index(drop=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  LOG CRUD
# ═══════════════════════════════════════════════════════════════════════════════
def _find_row(vals, hdrs, habit_id, date_dmy):
    try: dc,ic = hdrs.index("Date"),hdrs.index("HabitID")
    except: return None
    for i,row in enumerate(vals[1:],2):
        if len(row)>max(dc,ic) and row[dc]==date_dmy and row[ic]==habit_id:
            return i
    return None

def upsert_log(habit_id, habit_name, date_iso, value):
    date_dmy = iso_to_dmy(date_iso)
    ws       = get_ss().worksheet("HabitLogs")
    all_vals = ws.get_all_values()
    hdrs     = all_vals[0] if all_vals else LOG_HEADERS
    existing = _find_row(all_vals, hdrs, habit_id, date_dmy)
    if value is None:
        stored = None
    elif isinstance(value, bool):
        stored = "1" if value else None
    else:
        try:
            f = float(value)
            stored = None if (f==0 or pd.isna(f)) else str(f)
        except: stored = None
    if stored is None:
        if existing: ws.delete_rows(existing); st.cache_data.clear()
        return
    try:    vc = hdrs.index("Value")
    except: vc = 4
    if existing: ws.update_cell(existing, vc+1, stored)
    else:        ws.append_row([str(uuid.uuid4())[:8], date_dmy, habit_id, habit_name, stored])
    st.cache_data.clear()

# ═══════════════════════════════════════════════════════════════════════════════
#  HABIT CRUD
# ═══════════════════════════════════════════════════════════════════════════════
def toggle_active(habit_id, currently_active):
    ws   = get_ss().worksheet("Habits")
    vals = ws.get_all_values(); hdrs = vals[0]
    try: ic,ac = hdrs.index("HabitID"),hdrs.index("Active")
    except: return
    for i,row in enumerate(vals[1:],2):
        if len(row)>max(ic,ac) and row[ic]==habit_id:
            ws.update_cell(i, ac+1, "FALSE" if currently_active else "TRUE"); break
    st.cache_data.clear()

def delete_habit(habit_id):
    ws   = get_ss().worksheet("Habits")
    vals = ws.get_all_values(); hdrs = vals[0]
    try: ic = hdrs.index("HabitID")
    except: return
    for i,row in enumerate(vals[1:],2):
        if len(row)>ic and row[ic]==habit_id:
            ws.delete_rows(i); break
    st.cache_data.clear()

def swap_orders(id_a, ord_a, id_b, ord_b):
    ws   = get_ss().worksheet("Habits")
    vals = ws.get_all_values(); hdrs = vals[0]
    try: ic,oc = hdrs.index("HabitID"),hdrs.index("Order")
    except: return
    rows_found = {}
    for i,row in enumerate(vals[1:],2):
        if len(row)>max(ic,oc):
            if row[ic]==id_a: rows_found[id_a]=i
            if row[ic]==id_b: rows_found[id_b]=i
        if len(rows_found)==2: break
    if id_a in rows_found: ws.update_cell(rows_found[id_a], oc+1, ord_b)
    if id_b in rows_found: ws.update_cell(rows_found[id_b], oc+1, ord_a)
    st.cache_data.clear()

# ═══════════════════════════════════════════════════════════════════════════════
#  SCORE / STREAK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def _done_dates(habit_id, logs_df, h_type, target):
    if logs_df.empty: return set()
    rows = logs_df[logs_df["HabitID"].astype(str)==habit_id]
    out  = set()
    for _,r in rows.iterrows():
        try:
            iso = dmy_to_iso(str(r["Date"]))
            val = float(r["Value"])
            if (h_type=="boolean" and val>=1) or (h_type=="numeric" and val>=target):
                out.add(iso)
        except: pass
    return out

def streak(habit_id, logs_df, h_type, target):
    done = _done_dates(habit_id, logs_df, h_type, target)
    n,c  = 0, date.today()
    for _ in range(365):
        if c.isoformat() in done: n+=1; c-=timedelta(1)
        else: break
    return n

def get_log_val(habit_id, date_iso, logs_df, h_type):
    if logs_df.empty: return False if h_type=="boolean" else None
    dmy = iso_to_dmy(date_iso)
    row = logs_df[(logs_df["HabitID"].astype(str)==habit_id)&(logs_df["Date"].astype(str)==dmy)]
    if row.empty: return False if h_type=="boolean" else None
    try:
        v = float(row.iloc[0]["Value"])
        return (v>=1) if h_type=="boolean" else v
    except: return False if h_type=="boolean" else None

def today_done_total(habits_df, logs_df):
    today_dmy = iso_to_dmy(date.today().isoformat())
    active    = habits_df[habits_df["Active"]==True]
    if active.empty: return 0,0
    tl = logs_df[logs_df["Date"]==today_dmy] if not logs_df.empty else pd.DataFrame()
    done=0
    for _,h in active.iterrows():
        hid,ht,tgt = str(h["HabitID"]),str(h["Type"]),float(h["Target"])
        lg = tl[tl["HabitID"].astype(str)==hid] if not tl.empty else pd.DataFrame()
        if lg.empty: continue
        try:
            v=float(lg.iloc[0]["Value"])
            if (ht=="boolean" and v>=1) or (ht=="numeric" and v>=tgt): done+=1
        except: pass
    return done, len(active)

def cat_done_total(cat_habits, logs_df):
    today_dmy = iso_to_dmy(date.today().isoformat())
    tl = logs_df[logs_df["Date"]==today_dmy] if not logs_df.empty else pd.DataFrame()
    done=0
    for _,h in cat_habits.iterrows():
        hid,ht,tgt = str(h["HabitID"]),str(h["Type"]),float(h["Target"])
        lg = tl[tl["HabitID"].astype(str)==hid] if not tl.empty else pd.DataFrame()
        if lg.empty: continue
        try:
            v=float(lg.iloc[0]["Value"])
            if (ht=="boolean" and v>=1) or (ht=="numeric" and v>=tgt): done+=1
        except: pass
    return done, len(cat_habits)

def _same(a, b, h_type):
    if h_type=="boolean": return bool(a)==bool(b)
    an = a is None or (isinstance(a,float) and pd.isna(a))
    bn = b is None or (isinstance(b,float) and pd.isna(b))
    if an and bn: return True
    if an or bn:  return False
    try:    return abs(float(a)-float(b))<1e-9
    except: return False

# ═══════════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{{
    background:{C["bg"]} !important;color:{C["text"]};font-family:'DM Sans',sans-serif}}
[data-testid="stAppViewContainer"]>.main{{max-width:480px;margin:0 auto;padding:0 0 90px!important}}
.block-container{{padding:0 6px 90px!important;max-width:480px!important}}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="collapsedControl"],
[data-testid="stSidebar"],footer,#MainMenu{{display:none!important}}

/* ── page header ── */
.hdr{{padding:12px 6px 10px;border-bottom:1px solid {C["border"]};margin-bottom:6px}}
.hdr-date{{font-size:.58rem;font-weight:700;color:{C["muted"]};letter-spacing:1px;text-transform:uppercase}}
.hdr-greet{{font-size:1.15rem;font-weight:800;color:{C["text"]};margin:2px 0 8px}}
.pbar{{background:{C["s2"]};border-radius:100px;height:4px;overflow:hidden}}
.pbar-fill{{height:100%;border-radius:100px;transition:width .5s ease}}
.pbar-lbl{{display:flex;justify-content:space-between;font-size:.58rem;color:{C["muted"]};margin-top:3px}}

/* ── section divider ── */
.sdiv{{display:flex;align-items:center;gap:7px;margin:12px 0 4px;padding:0 2px}}
.sdiv-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.sdiv-txt{{font-size:.6rem;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;
    color:{C["muted"]};white-space:nowrap}}
.sdiv-line{{flex:1;height:1px;background:{C["border"]}}}
.sdiv-badge{{font-size:.6rem;font-weight:700;padding:1px 8px;border-radius:20px;
    background:{C["s2"]};white-space:nowrap;border:1px solid {C["border"]}}}

/* ── date header strip ── */
.date-hdr-row{{display:flex;align-items:center;padding:0 2px;margin-bottom:2px}}
.dhcell{{flex:1;text-align:center;min-width:0}}
.dhcell-name{{flex:3.5;text-align:left;padding-left:4px}}
.dhday{{font-size:.56rem;font-weight:700;letter-spacing:.6px;text-transform:uppercase}}
.dhnum{{font-size:.8rem;font-weight:800;line-height:1.1}}
.dhcell-today .dhday,.dhcell-today .dhnum{{color:{C["text"]}}}
.dhcell-past .dhday,.dhcell-past .dhnum{{color:{C["muted"]}}}

/* ── habit rows ── */
.habit-row-outer{{border-bottom:1px solid {C["border"]}22;padding:1px 0}}

/* icon circle */
.hicon-wrap{{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-size:.9rem;flex-shrink:0}}

/* name block */
.hname-txt{{font-size:.8rem;font-weight:600;color:{C["text"]};
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.2}}
.hname-sub{{font-size:.56rem;color:{C["muted"]};margin-top:1px;line-height:1}}

/* past-day cells */
.dc{{text-align:center;padding:6px 0;font-size:.78rem;font-weight:700;line-height:1}}
.dc-done{{color:{C["green"]}}}
.dc-miss{{color:{C["border"]}}}
.dc-num-ok{{font-size:.62rem;color:{C["green"]};line-height:1.15;text-align:center;padding:4px 0}}
.dc-num-lo{{font-size:.62rem;color:{C["amber"]};line-height:1.15;text-align:center;padding:4px 0}}
.dc-num-nil{{font-size:.78rem;color:{C["border"]};text-align:center;padding:6px 0;font-weight:700}}
.dc-unit{{font-size:.46rem;color:{C["muted"]};display:block;margin-top:1px}}

/* ── today toggle button ── */
.tog-wrap [data-testid="stButton"]>button{{
    background:transparent!important;border:1px solid {C["border"]}!important;
    border-radius:8px!important;font-size:.9rem!important;font-weight:800!important;
    padding:0!important;height:34px!important;width:100%!important;
    min-height:unset!important;color:{C["muted"]}!important;
    transition:all .15s!important;box-shadow:none!important}}
.tog-wrap [data-testid="stButton"]>button:hover{{
    border-color:{C["green"]}!important;color:{C["green"]}!important}}
.tog-done [data-testid="stButton"]>button{{
    background:rgba(34,211,160,0.12)!important;
    border-color:{C["green"]}!important;color:{C["green"]}!important}}

/* ── number input (numeric today) ── */
[data-testid="stNumberInput"]{{margin:0!important}}
[data-testid="stNumberInput"] input{{
    background:{C["s2"]}!important;border:1px solid {C["border"]}!important;
    border-radius:8px!important;color:{C["text"]}!important;
    font-family:'DM Sans',sans-serif!important;
    font-size:.78rem!important;font-weight:700!important;
    padding:5px 6px!important;text-align:center!important;
    height:34px!important;min-height:unset!important}}
[data-testid="stNumberInput"] [data-testid="stNumberInputStepUp"],
[data-testid="stNumberInput"] [data-testid="stNumberInputStepDown"]{{display:none!important}}

/* ── bottom progress strip ── */
.cs{{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;
    max-width:480px;z-index:999;background:{C["surface"]};
    border-top:1px solid {C["border"]};padding:8px 16px 18px;
    display:flex;align-items:center;gap:12px}}
.cs-pct{{font-family:'JetBrains Mono',monospace;font-size:1rem;font-weight:700;flex-shrink:0}}
.cs-bar{{flex:1;background:{C["s2"]};border-radius:100px;height:6px;overflow:hidden}}
.cs-fill{{height:100%;border-radius:100px;transition:width .4s ease}}
.cs-lbl{{font-size:.6rem;color:{C["muted"]};flex-shrink:0;font-family:'JetBrains Mono',monospace}}

/* ── nav + reload buttons ── */
div[data-key="nav_dd"]>div>div>div{{
    background:{C["dim"]}!important;border:1px solid {C["blue"]}!important;
    border-radius:9px!important;font-weight:800!important;font-size:.82rem!important}}
[data-testid="stButton"]>button{{
    background:transparent!important;border:none!important;color:{C["muted"]}!important;
    font-family:'DM Sans',sans-serif!important;font-size:.7rem!important;font-weight:700!important;
    padding:4px 8px!important;border-radius:7px!important;width:100%!important;
    transition:color .15s,background .15s!important;box-shadow:none!important}}
[data-testid="stButton"]>button:hover{{color:{C["blue"]}!important;background:{C["dim"]}!important}}
[data-testid="stFormSubmitButton"]>button{{
    background:{C["blue"]}!important;color:#fff!important;border-radius:9px!important;
    font-weight:800!important;font-size:.85rem!important;padding:9px 16px!important;
    box-shadow:0 2px 10px rgba(91,141,238,.3)!important}}

/* ── form inputs ── */
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input{{
    background:{C["s2"]}!important;border:1px solid {C["border"]}!important;
    border-radius:8px!important;color:{C["text"]}!important;font-family:'DM Sans',sans-serif!important}}
[data-testid="stSelectbox"]>div>div{{
    background:{C["s2"]}!important;border:1px solid {C["border"]}!important;
    border-radius:8px!important;color:{C["text"]}!important}}
[data-testid="stExpander"]{{
    background:{C["surface"]}!important;border:1px solid {C["border"]}!important;
    border-radius:10px!important;margin:4px 0!important}}
[data-testid="stExpander"] summary{{color:{C["text"]}!important;font-weight:700!important;font-size:.82rem!important}}
[data-testid="stAlert"]{{border-radius:9px!important;border:none!important}}
hr{{border-color:{C["border"]}!important;margin:8px 0!important}}
::-webkit-scrollbar{{width:3px;height:3px}}
::-webkit-scrollbar-thumb{{background:{C["border"]};border-radius:2px}}

/* ── manage reorder buttons ── */
.reo [data-testid="stButton"]>button{{
    background:{C["s2"]}!important;color:{C["muted"]}!important;
    border:1px solid {C["border"]}!important;border-radius:7px!important;
    font-size:.75rem!important;width:32px!important;height:32px!important;
    min-height:unset!important;padding:0!important}}
.reo [data-testid="stButton"]>button:hover{{
    border-color:{C["blue"]}!important;color:{C["blue"]}!important}}

/* column gap tightening */
[data-testid="stHorizontalBlock"]{{gap:4px!important}}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
def init_state():
    for k,v in {"nav":"today","setup_ok":False,"confirm_del":None,
                "log_date":date.today()}.items():
        if k not in st.session_state: st.session_state[k]=v

# ═══════════════════════════════════════════════════════════════════════════════
#  TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════
def render_top_bar():
    NAV = {"today":"Today","manage":"Manage"}
    c1,c2,_ = st.columns([4,1,1])
    with c1:
        cur    = NAV.get(st.session_state.nav,"Today")
        choice = st.selectbox("",list(NAV.values()),
                              index=list(NAV.values()).index(cur),
                              key="nav_dd",label_visibility="collapsed")
        ck = [k for k,v in NAV.items() if v==choice][0]
        if ck!=st.session_state.nav: st.session_state.nav=ck; st.rerun()
    with c2:
        if st.button("↺", key="reload"):
            st.cache_data.clear(); st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  DATE HEADER  (rendered once, stays aligned with all habit rows)
# ═══════════════════════════════════════════════════════════════════════════════
# Column proportion shared across header + every habit row
_COLS = [3.5, 0.85, 0.85, 0.85, 0.85, 1.15]

def render_date_header(log_date):
    """One sticky-style date header row above all habits."""
    dates = [log_date - timedelta(i) for i in range(4, -1, -1)]
    hcols = st.columns(_COLS)
    # col 0 empty (habit name area)
    hcols[0].markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    for i, d in enumerate(dates):
        is_active = (i == 4)
        css_cls = "dhcell-today" if is_active else "dhcell-past"
        hcols[i+1].markdown(
            f'<div class="dhcell {css_cls}" style="text-align:center">'
            f'<div class="dhday">{d.strftime("%a").upper()[:3]}</div>'
            f'<div class="dhnum">{d.day}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION RENDER  — list rows, no grid
# ═══════════════════════════════════════════════════════════════════════════════
def _past_day_cell(val, h_type, tgt, hunit):
    """Return HTML string for a read-only past-day cell."""
    if h_type == "boolean":
        if val is True:
            return '<div class="dc dc-done">✓</div>'
        return '<div class="dc dc-miss">✗</div>'
    else:
        if val is not None:
            try:
                fval = float(val)
                if fval > 0:
                    done = fval >= tgt
                    disp = int(fval) if fval == int(fval) else round(fval, 1)
                    cls  = "dc-num-ok" if done else "dc-num-lo"
                    return f'<div class="{cls}">{disp}<span class="dc-unit">{hunit}</span></div>'
            except: pass
        return '<div class="dc-num-nil">—</div>'


def render_section(cat, cat_habits, log_date_iso, logs_df, today):
    if cat_habits.empty: return

    log_date     = datetime.strptime(log_date_iso, "%Y-%m-%d").date()
    done_n,tot_n = cat_done_total(cat_habits, logs_df)
    dc           = C["green"] if (done_n==tot_n and tot_n>0) else C["muted"]
    accent       = CAT_COLOR.get(cat, C["blue"])

    # ── section divider ──
    st.markdown(f"""<div class="sdiv">
        <div class="sdiv-dot" style="background:{accent}"></div>
        <div class="sdiv-txt" style="color:{accent}">{cat}</div>
        <div class="sdiv-line"></div>
        <div class="sdiv-badge" style="color:{dc}">{done_n}/{tot_n}</div>
    </div>""", unsafe_allow_html=True)

    # 5 dates: oldest → log_date
    dates = [log_date - timedelta(i) for i in range(4, -1, -1)]

    # ── one row per habit ──
    for _, h in cat_habits.iterrows():
        hid    = str(h["HabitID"])
        hname  = str(h["Name"])
        icon   = str(h.get("Icon", "🎯"))
        h_type = str(h["Type"])
        tgt    = float(h["Target"])
        hunit  = str(h.get("TargetUnit", ""))
        s      = streak(hid, logs_df, h_type, tgt)

        # Values for the 5 display dates
        day_vals = [get_log_val(hid, d.isoformat(), logs_df, h_type) for d in dates]
        today_val = day_vals[-1]

        st.markdown('<div class="habit-row-outer">', unsafe_allow_html=True)
        rcols = st.columns(_COLS)

        # ── col 0: icon + name ──
        streak_html = (f'<span style="font-size:.55rem;color:{C["streak"]};'
                       f'font-weight:700;margin-left:3px">🔥{s}</span>') if s > 0 else ""
        subtext = f'{int(tgt)}{hunit} target' if h_type == "numeric" else ""
        sub_html = (f'<div class="hname-sub">{subtext}</div>') if subtext else ""

        rcols[0].markdown(f"""
            <div style="display:flex;align-items:center;gap:7px;padding:5px 2px">
                <div class="hicon-wrap" style="background:{accent}18">{icon}</div>
                <div style="overflow:hidden;min-width:0">
                    <div class="hname-txt">{hname}{streak_html}</div>
                    {sub_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ── cols 1-4: past 4 days (read-only HTML) ──
        for i in range(4):
            rcols[i+1].markdown(
                _past_day_cell(day_vals[i], h_type, tgt, hunit),
                unsafe_allow_html=True
            )

        # ── col 5: today — interactive ──
        with rcols[5]:
            if h_type == "boolean":
                done = today_val is True
                wrap_cls = "tog-wrap tog-done" if done else "tog-wrap"
                lbl = "✓" if done else "○"
                st.markdown(f'<div class="{wrap_cls}">', unsafe_allow_html=True)
                if st.button(lbl, key=f"tog_{hid}_{log_date_iso}",
                             use_container_width=True):
                    upsert_log(hid, hname, log_date_iso, not done)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                curr = float(today_val) if today_val is not None else 0.0
                new_num = st.number_input(
                    "", value=curr, min_value=0.0, step=1.0, format="%g",
                    key=f"num_{hid}_{log_date_iso}",
                    label_visibility="collapsed"
                )
                if not _same(new_num, curr, "numeric"):
                    upsert_log(hid, hname, log_date_iso,
                               new_num if new_num > 0 else None)
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — TODAY
# ═══════════════════════════════════════════════════════════════════════════════
def screen_today():
    habits_df = load_habits()
    logs_df   = load_logs(90)
    active    = habits_df[habits_df["Active"]==True].copy()
    today     = date.today()

    log_date     = st.session_state.log_date
    log_date_iso = log_date.isoformat()
    is_today     = (log_date == today)

    # Header
    hour  = datetime.now().hour
    greet = "Morning 🌤" if hour<12 else "Afternoon ☀️" if hour<17 else "Evening 🌙"
    dn,tn = today_done_total(active, logs_df)
    pct   = round(dn/tn*100) if tn>0 else 0
    pc    = C["green"] if pct==100 else C["blue"] if pct>=50 else C["amber"]

    date_line = log_date.strftime("%d %b") if not is_today else today.strftime("%A, %d %B %Y")
    title_lbl = f"Good {greet}" if is_today else log_date.strftime("%d %b %Y")

    st.markdown(f"""<div class="hdr">
        <div class="hdr-date">{date_line.upper()}</div>
        <div class="hdr-greet">{title_lbl}</div>
        <div class="pbar"><div class="pbar-fill" style="width:{pct}%;background:{pc}"></div></div>
        <div class="pbar-lbl"><span>Today's progress</span>
            <span style="color:{pc};font-weight:700">{dn}/{tn}</span></div>
    </div>""", unsafe_allow_html=True)

    if active.empty:
        st.info("No active habits. Go to Manage to get started."); return

    # Date picker
    with st.expander("📅 Log for a different date", expanded=not is_today):
        picked = st.date_input("Date", value=log_date, max_value=today,
                               label_visibility="collapsed", key="date_pick")
        if picked != log_date:
            st.session_state.log_date = picked; st.rerun()
        if not is_today:
            st.markdown(f'<span style="font-size:.68rem;color:{C["amber"]}">Logging: '
                        f'{log_date.strftime("%d %b %Y")}</span>', unsafe_allow_html=True)
            if st.button("↩ Back to today", key="back_today"):
                st.session_state.log_date = today; st.rerun()

    # Date header (one per page)
    render_date_header(log_date)

    # Category sections
    for cat in CATEGORIES:
        ch = active[active["Category"]==cat].reset_index(drop=True)
        render_section(cat, ch, log_date_iso, logs_df, today)

    # Fixed bottom strip
    lbl = "All done! 🎉" if (tn>0 and dn==tn) else f"{pct}%"
    st.markdown(f"""<div class="cs">
        <div class="cs-pct" style="color:{pc}">{lbl}</div>
        <div class="cs-bar"><div class="cs-fill" style="width:{pct}%;background:{pc}"></div></div>
        <div class="cs-lbl">{dn}/{tn}</div>
    </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — MANAGE
# ═══════════════════════════════════════════════════════════════════════════════
def screen_manage():
    habits_df = load_habits()
    st.markdown(f'<div style="font-size:1.05rem;font-weight:900;padding:10px 4px 6px">'
                f'Manage Habits</div>', unsafe_allow_html=True)

    with st.expander("➕ Add New Habit", expanded=habits_df.empty):
        with st.form("add_form", clear_on_submit=True):
            c1,c2 = st.columns([3,1])
            with c1: new_name = st.text_input("Name *", placeholder="e.g. Cold shower")
            with c2: new_icon = st.text_input("Icon", value="🎯")
            c3,c4 = st.columns(2)
            with c3: new_cat  = st.selectbox("Category", CATEGORIES)
            with c4: new_type = st.selectbox("Type", ["boolean","numeric"])
            c5,c6 = st.columns(2)
            with c5: new_tgt  = st.number_input("Target", value=1, min_value=0, step=1)
            with c6: new_unit = st.text_input("Unit", placeholder="g, reps…")
            if st.form_submit_button("Add Habit", type="primary", use_container_width=True):
                if new_name.strip():
                    next_ord = int(habits_df["Order"].max())+1 if not habits_df.empty else 1
                    get_ss().worksheet("Habits").append_row([
                        str(uuid.uuid4())[:6], new_name.strip(),
                        new_icon.strip() or "🎯", new_cat, new_type,
                        str(new_tgt), new_unit.strip(), "daily","", next_ord,"TRUE",
                    ])
                    st.cache_data.clear(); st.success(f"Added: {new_name}"); st.rerun()
                else: st.error("Enter a habit name.")

    if habits_df.empty: return

    for cat in CATEGORIES:
        cat_h = habits_df[
            (habits_df["Category"]==cat) & (habits_df["Active"]==True)
        ].reset_index(drop=True)
        if cat_h.empty: continue

        accent = CAT_COLOR.get(cat, C["blue"])
        st.markdown(f"""<div class="sdiv" style="margin-top:14px">
            <div class="sdiv-dot" style="background:{accent}"></div>
            <div class="sdiv-txt" style="color:{accent}">{cat}</div>
            <div class="sdiv-line"></div>
        </div>""", unsafe_allow_html=True)

        for idx,habit in cat_h.iterrows():
            hid   = str(habit["HabitID"])
            hname = str(habit["Name"])
            htype = str(habit["Type"])
            htgt  = str(int(habit["Target"])) if htype=="numeric" else ""
            hunit = str(habit.get("TargetUnit",""))
            hord  = int(habit["Order"])
            info  = f"{htype}  ·  target: {htgt}{hunit}" if htype=="numeric" else htype

            st.markdown(f"""<div style="background:{C['s2']};border:1px solid {C['border']};
                border-radius:9px;padding:7px 12px;margin:2px 0;
                display:flex;align-items:center;gap:8px">
                <div style="flex:1;min-width:0">
                    <div style="font-size:.82rem;font-weight:700;white-space:nowrap;
                         overflow:hidden;text-overflow:ellipsis">{hname}</div>
                    <div style="font-size:.58rem;color:{C['muted']}">{info}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            bu,bd,bp,bdel,bsp = st.columns([1,1,1,1,3])
            with bu:
                st.markdown('<div class="reo">', unsafe_allow_html=True)
                if st.button("↑", key=f"up_{hid}", disabled=(idx==0)):
                    prev = cat_h.iloc[idx-1]
                    swap_orders(hid, hord, str(prev["HabitID"]), int(prev["Order"]))
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with bd:
                st.markdown('<div class="reo">', unsafe_allow_html=True)
                if st.button("↓", key=f"dn_{hid}", disabled=(idx==len(cat_h)-1)):
                    nxt = cat_h.iloc[idx+1]
                    swap_orders(hid, hord, str(nxt["HabitID"]), int(nxt["Order"]))
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with bp:
                if st.button("⏸", key=f"pause_{hid}"):
                    toggle_active(hid, True); st.rerun()
            with bdel:
                if st.session_state.confirm_del==hid:
                    if st.button("✓ Del?", key=f"cd_{hid}"):
                        delete_habit(hid); st.session_state.confirm_del=None; st.rerun()
                else:
                    if st.button("🗑", key=f"del_{hid}"):
                        st.session_state.confirm_del=hid; st.rerun()
            with bsp:
                if st.session_state.confirm_del==hid:
                    st.markdown(f'<span style="font-size:.6rem;color:{C["red"]}">Deletes all logs</span>',
                                unsafe_allow_html=True)

    # Paused
    inactive = habits_df[habits_df["Active"]==False].reset_index(drop=True)
    if not inactive.empty:
        st.markdown("---")
        st.markdown(f'<div class="sdiv-txt" style="margin:6px 0 4px;color:{C["muted"]}">Paused</div>',
                    unsafe_allow_html=True)
        for _,habit in inactive.iterrows():
            hid   = str(habit["HabitID"])
            hname = str(habit["Name"])
            ci,cb = st.columns([5,1])
            with ci:
                st.markdown(f'<div style="padding:5px 4px;opacity:.4;font-size:.8rem;'
                            f'border-bottom:1px solid {C["border"]}">{hname}</div>',
                            unsafe_allow_html=True)
            with cb:
                if st.button("▶", key=f"res_{hid}"):
                    toggle_active(hid, False); st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  SETUP & MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def run_setup():
    if not st.session_state.setup_ok:
        with st.spinner("Setting up…"):
            try:
                ensure_sheets()
                st.session_state.setup_ok = True
            except Exception as ex:
                st.error(f"Setup failed: {ex}")
                st.stop()

def main():
    init_state(); inject_css(); run_setup(); render_top_bar()
    if   st.session_state.nav=="today":  screen_today()
    elif st.session_state.nav=="manage": screen_manage()

if __name__=="__main__": main()
