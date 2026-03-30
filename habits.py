import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import json, uuid

st.set_page_config(page_title="Habits", page_icon="🔥",
                   layout="centered", initial_sidebar_state="collapsed")

# ── DESIGN TOKENS  (notebook / paper light theme) ─────────────────────────────
C = {
    "bg":      "#F5F3EE",
    "surface": "#FFFFFF",
    "s2":      "#EFEDE7",
    "border":  "#DDD9D0",
    "text":    "#1C1916",
    "muted":   "#A09890",
    "blue":    "#2563EB",
    "green":   "#16A34A",
    "red":     "#DC2626",
    "amber":   "#D97706",
    "streak":  "#EA580C",
    "dim":     "rgba(37,99,235,0.08)",
}

CAT_COLOR = {
    "Daily":                "#2563EB",
    "Nutrition & Movement": "#16A34A",
    "Workout Days":         "#D97706",
    "Weekly":               "#EA580C",
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
    ["h07","50/5 Rule - breaks",      "⏱","Nutrition & Movement","numeric","5",  "brks",  "daily","",  7,"TRUE"],
    ["h08","Protein intake",          "🥩","Nutrition & Movement","numeric","140","g",     "daily","",  8,"TRUE"],
    ["h09","Floors climbed",          "🗼","Nutrition & Movement","numeric","10", "fl",    "daily","",  9,"TRUE"],
    ["h10","Workout before 10 AM",    "🏋","Workout Days",        "boolean","1",  "",      "daily","", 10,"TRUE"],
    ["h11","Foam rolling done",       "🧹","Workout Days",        "boolean","1",  "",      "daily","", 11,"TRUE"],
    ["h12","Post-workout protein",    "🥤","Workout Days",        "boolean","1",  "",      "daily","", 12,"TRUE"],
    ["h13","Long walk 45-60 min",     "🚶","Weekly",              "boolean","1",  "",      "weekly","Sun",13,"TRUE"],
    ["h14","Flexibility / yoga",      "🧘","Weekly",              "boolean","1",  "",      "weekly","Sat",14,"TRUE"],
    ["h15","Weekly stair test",       "📊","Weekly",              "boolean","1",  "",      "weekly","Sun",15,"TRUE"],
]

_COLS = [3.2, 0.8, 0.8, 0.8, 0.8, 1.1]

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
#  CSS — light notebook, ultra-compact
# ═══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

html,body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"]{{
    background:{C["bg"]}!important;
    color:{C["text"]};
    font-family:'DM Sans',sans-serif}}

[data-testid="stAppViewContainer"]>.main{{
    max-width:480px;margin:0 auto;padding:0 0 76px!important}}
.block-container{{padding:0 6px 76px!important;max-width:480px!important}}

[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="collapsedControl"],[data-testid="stSidebar"],
footer,#MainMenu{{display:none!important}}

/* ── nuke all Streamlit vertical gaps ────────────────────────────────────── */
[data-testid="stVerticalBlock"]>div{{gap:0!important}}
[data-testid="stVerticalBlockSeparator"]{{display:none!important}}
[data-testid="element-container"]{{padding:0!important;margin:0!important}}
[data-testid="stHorizontalBlock"]{{
    gap:2px!important;align-items:center!important;
    padding:0!important;margin:0!important}}

/* ── page header ─────────────────────────────────────────────────────────── */
.hdr{{padding:10px 4px 8px;border-bottom:2px solid {C["border"]};margin-bottom:2px}}
.hdr-date{{font-size:.55rem;font-weight:700;color:{C["muted"]};
    letter-spacing:1.2px;text-transform:uppercase}}
.hdr-greet{{font-size:1.08rem;font-weight:800;color:{C["text"]};margin:1px 0 6px}}
.pbar{{background:{C["s2"]};border-radius:100px;height:3px;overflow:hidden}}
.pbar-fill{{height:100%;border-radius:100px;transition:width .5s ease}}
.pbar-lbl{{display:flex;justify-content:space-between;
    font-size:.56rem;color:{C["muted"]};margin-top:2px}}

/* ── section divider ─────────────────────────────────────────────────────── */
.sdiv{{display:flex;align-items:center;gap:5px;
    margin:8px 0 0;padding:3px 2px;
    border-bottom:1px solid {C["border"]}}}
.sdiv-dot{{width:5px;height:5px;border-radius:50%;flex-shrink:0}}
.sdiv-txt{{font-size:.52rem;font-weight:800;letter-spacing:1.3px;
    text-transform:uppercase;white-space:nowrap}}
.sdiv-line{{flex:1}}
.sdiv-badge{{font-size:.52rem;font-weight:700;padding:1px 6px;
    border-radius:20px;background:{C["s2"]};white-space:nowrap;
    border:1px solid {C["border"]}}}

/* ── date header cells ───────────────────────────────────────────────────── */
.dhcell{{text-align:center;padding:2px 0}}
.dhday{{font-size:.48rem;font-weight:700;letter-spacing:.5px;
    text-transform:uppercase;color:{C["muted"]}}}
.dhnum{{font-size:.75rem;font-weight:800;line-height:1.1;color:{C["muted"]}}}
.dhcell-today .dhday,.dhcell-today .dhnum{{color:{C["text"]}}}

/* ── row separator line ──────────────────────────────────────────────────── */
.row-sep{{height:1px;background:{C["border"]}66;margin:0 2px}}

/* ── habit name column ───────────────────────────────────────────────────── */
.hname-wrap{{display:flex;align-items:center;gap:5px;padding:3px 0}}
.hicon{{font-size:.82rem;line-height:1;flex-shrink:0;width:20px;text-align:center}}
.hname-txt{{font-size:.76rem;font-weight:600;color:{C["text"]};
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.3}}
.hname-sub{{font-size:.5rem;color:{C["muted"]};line-height:1}}
.hstreak{{font-size:.48rem;font-weight:700;vertical-align:middle;margin-left:3px}}

/* ── past day cells ──────────────────────────────────────────────────────── */
.dc{{text-align:center;font-size:.75rem;font-weight:700;
    line-height:1;padding:2px 0}}
.dc-done{{color:{C["green"]}}}
.dc-miss{{color:{C["border"]}}}
.dc-num{{text-align:center;font-size:.58rem;font-weight:700;
    line-height:1.3;padding:2px 0}}
.dc-ok{{color:{C["green"]}}}
.dc-lo{{color:{C["amber"]}}}
.dc-nil{{color:{C["border"]};font-size:.72rem}}
.dc-unit{{font-size:.42rem;color:{C["muted"]};display:block}}

/* ── today toggle button (global base) ──────────────────────────────────── */
[data-testid="stButton"]>button{{
    background:transparent!important;border:1.5px solid {C["border"]}!important;
    border-radius:6px!important;color:{C["muted"]}!important;
    font-family:'DM Sans',sans-serif!important;
    font-size:.86rem!important;font-weight:700!important;
    padding:0!important;height:26px!important;width:100%!important;
    min-height:unset!important;line-height:1!important;
    transition:all .15s!important;box-shadow:none!important}}
[data-testid="stButton"]>button:hover{{
    border-color:{C["blue"]}!important;color:{C["blue"]}!important;
    background:{C["dim"]}!important}}

/* ── today number input ──────────────────────────────────────────────────── */
[data-testid="stNumberInput"]{{margin:0!important}}
[data-testid="stNumberInput"] input{{
    background:{C["surface"]}!important;
    border:1.5px solid {C["border"]}!important;
    border-radius:6px!important;color:{C["text"]}!important;
    font-family:'DM Sans',sans-serif!important;
    font-size:.72rem!important;font-weight:700!important;
    padding:2px 4px!important;text-align:center!important;
    height:26px!important;min-height:unset!important}}
[data-testid="stNumberInput"] [data-testid="stNumberInputStepUp"],
[data-testid="stNumberInput"] [data-testid="stNumberInputStepDown"]{{
    display:none!important}}

/* ── nav selectbox ───────────────────────────────────────────────────────── */
div[data-key="nav_dd"]>div>div>div{{
    background:{C["surface"]}!important;
    border:1px solid {C["border"]}!important;
    border-radius:8px!important;font-weight:800!important;
    font-size:.82rem!important;color:{C["text"]}!important}}

/* ── form submit ─────────────────────────────────────────────────────────── */
[data-testid="stFormSubmitButton"]>button{{
    background:{C["blue"]}!important;color:#fff!important;
    border:none!important;border-radius:8px!important;
    font-weight:800!important;font-size:.82rem!important;
    padding:8px 14px!important;
    box-shadow:0 2px 8px rgba(37,99,235,.2)!important}}

/* ── form inputs ─────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input{{
    background:{C["surface"]}!important;
    border:1px solid {C["border"]}!important;
    border-radius:7px!important;color:{C["text"]}!important;
    font-family:'DM Sans',sans-serif!important}}
[data-testid="stSelectbox"]>div>div{{
    background:{C["surface"]}!important;
    border:1px solid {C["border"]}!important;
    border-radius:7px!important;color:{C["text"]}!important}}
[data-testid="stExpander"]{{
    background:{C["surface"]}!important;
    border:1px solid {C["border"]}!important;
    border-radius:8px!important;margin:3px 0!important}}
[data-testid="stExpander"] summary{{
    color:{C["text"]}!important;font-weight:700!important;font-size:.78rem!important}}
[data-testid="stAlert"]{{border-radius:8px!important;border:none!important}}
hr{{border-color:{C["border"]}!important;margin:5px 0!important}}
::-webkit-scrollbar{{width:2px;height:2px}}
::-webkit-scrollbar-thumb{{background:{C["border"]};border-radius:2px}}

/* ── fixed bottom strip ──────────────────────────────────────────────────── */
.cs{{position:fixed;bottom:0;left:50%;transform:translateX(-50%);
    width:100%;max-width:480px;z-index:999;
    background:{C["surface"]};border-top:1px solid {C["border"]};
    padding:7px 16px 16px;display:flex;align-items:center;gap:10px}}
.cs-pct{{font-family:'JetBrains Mono',monospace;
    font-size:.9rem;font-weight:700;flex-shrink:0}}
.cs-bar{{flex:1;background:{C["s2"]};border-radius:100px;height:5px;overflow:hidden}}
.cs-fill{{height:100%;border-radius:100px;transition:width .4s ease}}
.cs-lbl{{font-size:.58rem;color:{C["muted"]};flex-shrink:0;
    font-family:'JetBrains Mono',monospace}}

/* ── manage reorder buttons ──────────────────────────────────────────────── */
.reo [data-testid="stButton"]>button{{
    background:{C["s2"]}!important;color:{C["muted"]}!important;
    border:1px solid {C["border"]}!important;border-radius:6px!important;
    font-size:.7rem!important;width:26px!important;height:26px!important;
    min-height:unset!important;padding:0!important}}
.reo [data-testid="stButton"]>button:hover{{
    border-color:{C["blue"]}!important;color:{C["blue"]}!important}}
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
#  DATE HEADER ROW
# ═══════════════════════════════════════════════════════════════════════════════
def render_date_header(log_date):
    dates = [log_date - timedelta(i) for i in range(4, -1, -1)]
    hcols = st.columns(_COLS, gap="small")
    hcols[0].markdown('<div style="height:22px"></div>', unsafe_allow_html=True)
    for i, d in enumerate(dates):
        cls = "dhcell-today" if i==4 else ""
        hcols[i+1].markdown(
            f'<div class="dhcell {cls}">'
            f'<div class="dhday">{d.strftime("%a")[:3].upper()}</div>'
            f'<div class="dhnum">{d.day}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════════════════════════════
#  PAST DAY CELL HTML  (self-contained — no open/close across calls)
# ═══════════════════════════════════════════════════════════════════════════════
def _past_cell(val, h_type, tgt, hunit):
    if h_type == "boolean":
        return ('<div class="dc dc-done">✓</div>' if val is True
                else '<div class="dc dc-miss">✗</div>')
    if val is not None:
        try:
            fval = float(val)
            if fval > 0:
                disp = int(fval) if fval==int(fval) else round(fval,1)
                cls  = "dc-ok" if fval>=tgt else "dc-lo"
                return (f'<div class="dc-num {cls}">{disp}'
                        f'<span class="dc-unit">{hunit}</span></div>')
        except: pass
    return '<div class="dc dc-nil">—</div>'

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION RENDER  — NO wrapping div open/close across st calls
# ═══════════════════════════════════════════════════════════════════════════════
def render_section(cat, cat_habits, log_date_iso, logs_df, today):
    if cat_habits.empty: return

    log_date     = datetime.strptime(log_date_iso, "%Y-%m-%d").date()
    done_n,tot_n = cat_done_total(cat_habits, logs_df)
    dc           = C["green"] if (done_n==tot_n and tot_n>0) else C["muted"]
    accent       = CAT_COLOR.get(cat, C["blue"])

    st.markdown(f"""<div class="sdiv">
        <div class="sdiv-dot" style="background:{accent}"></div>
        <div class="sdiv-txt" style="color:{accent}">{cat}</div>
        <div class="sdiv-line"></div>
        <div class="sdiv-badge" style="color:{dc}">{done_n}/{tot_n}</div>
    </div>""", unsafe_allow_html=True)

    dates = [log_date - timedelta(i) for i in range(4, -1, -1)]

    for _, h in cat_habits.iterrows():
        hid    = str(h["HabitID"])
        hname  = str(h["Name"])
        icon   = str(h.get("Icon","🎯"))
        h_type = str(h["Type"])
        tgt    = float(h["Target"])
        hunit  = str(h.get("TargetUnit",""))
        s      = streak(hid, logs_df, h_type, tgt)

        day_vals  = [get_log_val(hid, d.isoformat(), logs_df, h_type) for d in dates]
        today_val = day_vals[-1]
        done      = (today_val is True)

        # Per-button done-state style: inject a <style> keyed to the button key.
        # This avoids the wrapper-div bug entirely — no open/close div across calls.
        btn_key = f"tog_{hid}_{log_date_iso}"
        if h_type == "boolean":
            bc = C["green"] if done else C["muted"]
            bb = C["green"] if done else C["border"]
            bg = "rgba(22,163,74,0.09)" if done else "transparent"
            # Target via aria-label which Streamlit sets from button label
            # More reliably: target button inside the column via its unique key
            # Streamlit 1.x puts data-key on the surrounding div's parent stButton container
            st.markdown(f"""<style>
[data-testid="stButton"][data-key="{btn_key}"]>button,
div[data-key="{btn_key}"] button{{
    color:{bc}!important;
    background:{bg}!important;
    border:1.5px solid {bb}!important}}
</style>""", unsafe_allow_html=True)

        # ── Build name HTML (fully self-contained) ──
        streak_span = (f'<span class="hstreak" style="color:{C["streak"]}">🔥{s}</span>'
                       if s>0 else "")
        sub_html    = (f'<div class="hname-sub">{int(tgt)}{hunit} target</div>'
                       if h_type=="numeric" else "")

        # ── ROW using st.columns — no wrapping st.markdown div ──
        rcols = st.columns(_COLS, gap="small")

        rcols[0].markdown(
            f'<div class="hname-wrap">'
            f'<span class="hicon">{icon}</span>'
            f'<div style="min-width:0;overflow:hidden">'
            f'<div class="hname-txt">{hname}{streak_span}</div>'
            f'{sub_html}'
            f'</div></div>',
            unsafe_allow_html=True
        )

        for i in range(4):
            rcols[i+1].markdown(
                _past_cell(day_vals[i], h_type, tgt, hunit),
                unsafe_allow_html=True
            )

        with rcols[5]:
            if h_type == "boolean":
                lbl = "✓" if done else "○"
                if st.button(lbl, key=btn_key, use_container_width=True):
                    upsert_log(hid, hname, log_date_iso, not done)
                    st.rerun()
            else:
                curr    = float(today_val) if today_val is not None else 0.0
                new_num = st.number_input(
                    "", value=curr, min_value=0.0, step=1.0, format="%g",
                    key=f"num_{hid}_{log_date_iso}",
                    label_visibility="collapsed"
                )
                if not _same(new_num, curr, "numeric"):
                    upsert_log(hid, hname, log_date_iso,
                               new_num if new_num>0 else None)
                    st.rerun()

        # separator line as its own self-contained markdown block
        st.markdown(
            f'<div class="row-sep"></div>',
            unsafe_allow_html=True
        )

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
    is_today     = (log_date==today)

    hour  = datetime.now().hour
    greet = "Morning 🌤" if hour<12 else "Afternoon ☀️" if hour<17 else "Evening 🌙"
    dn,tn = today_done_total(active, logs_df)
    pct   = round(dn/tn*100) if tn>0 else 0
    pc    = C["green"] if pct==100 else C["blue"] if pct>=50 else C["amber"]

    date_line = (today.strftime("%A, %d %B %Y") if is_today
                 else log_date.strftime("%d %B %Y"))
    title_lbl = f"Good {greet}" if is_today else log_date.strftime("%d %b %Y")

    st.markdown(f"""<div class="hdr">
        <div class="hdr-date">{date_line.upper()}</div>
        <div class="hdr-greet">{title_lbl}</div>
        <div class="pbar">
            <div class="pbar-fill" style="width:{pct}%;background:{pc}"></div>
        </div>
        <div class="pbar-lbl">
            <span>Today's progress</span>
            <span style="color:{pc};font-weight:700">{dn}/{tn}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    if active.empty:
        st.info("No active habits. Go to Manage to get started."); return

    with st.expander("📅 Log for a different date", expanded=not is_today):
        picked = st.date_input("Date", value=log_date, max_value=today,
                               label_visibility="collapsed", key="date_pick")
        if picked != log_date:
            st.session_state.log_date = picked; st.rerun()
        if not is_today:
            st.markdown(
                f'<span style="font-size:.63rem;color:{C["amber"]}">Logging: '
                f'{log_date.strftime("%d %b %Y")}</span>',
                unsafe_allow_html=True
            )
            if st.button("↩ Back to today", key="back_today"):
                st.session_state.log_date = today; st.rerun()

    render_date_header(log_date)

    for cat in CATEGORIES:
        ch = active[active["Category"]==cat].reset_index(drop=True)
        render_section(cat, ch, log_date_iso, logs_df, today)

    lbl = "All done! 🎉" if (tn>0 and dn==tn) else f"{pct}%"
    st.markdown(f"""<div class="cs">
        <div class="cs-pct" style="color:{pc}">{lbl}</div>
        <div class="cs-bar">
            <div class="cs-fill" style="width:{pct}%;background:{pc}"></div>
        </div>
        <div class="cs-lbl">{dn}/{tn}</div>
    </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — MANAGE
# ═══════════════════════════════════════════════════════════════════════════════
def screen_manage():
    habits_df = load_habits()
    st.markdown(
        f'<div style="font-size:1rem;font-weight:900;padding:10px 4px 6px;'
        f'color:{C["text"]}">Manage Habits</div>',
        unsafe_allow_html=True
    )

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
        st.markdown(f"""<div class="sdiv" style="margin-top:10px">
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
            info  = f"{htype}  ·  {htgt}{hunit}" if htype=="numeric" else htype

            st.markdown(
                f'<div style="background:{C["surface"]};'
                f'border:1px solid {C["border"]};border-radius:7px;'
                f'padding:5px 10px;margin:2px 0">'
                f'<div style="font-size:.76rem;font-weight:700">{hname}</div>'
                f'<div style="font-size:.52rem;color:{C["muted"]}">{info}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

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
                        delete_habit(hid)
                        st.session_state.confirm_del=None; st.rerun()
                else:
                    if st.button("🗑", key=f"del_{hid}"):
                        st.session_state.confirm_del=hid; st.rerun()
            with bsp:
                if st.session_state.confirm_del==hid:
                    st.markdown(
                        f'<span style="font-size:.56rem;color:{C["red"]}">Deletes all logs</span>',
                        unsafe_allow_html=True
                    )

    inactive = habits_df[habits_df["Active"]==False].reset_index(drop=True)
    if not inactive.empty:
        st.markdown("---")
        st.markdown(
            f'<div style="font-size:.55rem;font-weight:800;letter-spacing:1px;'
            f'text-transform:uppercase;color:{C["muted"]};margin:4px 0 2px">Paused</div>',
            unsafe_allow_html=True
        )
        for _,habit in inactive.iterrows():
            hid   = str(habit["HabitID"])
            hname = str(habit["Name"])
            ci,cb = st.columns([5,1])
            with ci:
                st.markdown(
                    f'<div style="padding:4px;opacity:.4;font-size:.74rem;'
                    f'border-bottom:1px solid {C["border"]}">{hname}</div>',
                    unsafe_allow_html=True
                )
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
