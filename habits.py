import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import json, uuid, calendar
import plotly.graph_objects as go

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HabitTracker",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── DESIGN TOKENS — same palette as ClearSpend ────────────────────────────────
C = {
    "bg":          "#0d1117",
    "surface":     "#161b22",
    "surface2":    "#1c2333",
    "border":      "#30363d",
    "primary":     "#7c6df8",
    "primary_dim": "rgba(124,109,248,0.12)",
    "income":      "#00c896",
    "expense":     "#ff4f6d",
    "warning":     "#f0a500",
    "info":        "#58a6ff",
    "text":        "#e6edf3",
    "muted":       "#8b949e",
    "success":     "#3fb950",
    "streak":      "#f97316",
}

# ── GOOGLE SHEETS ──────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_NAME = "ClearSpend"   # same workbook as ClearSpend

# Habits sheet — master habit definitions
HABIT_HEADERS = ["HabitID", "Name", "Icon", "Order", "CreatedDate", "Active"]

# HabitLogs sheet — one row per completed check-in (only completed are stored)
LOG_HEADERS   = ["LogID", "Date", "HabitID", "HabitName"]
# Absence of a log entry for a past date = missed
# Absence of a log entry for today       = pending


# ═══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS CONNECTION
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource
def get_ss():
    client = get_client()
    try:
        return client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        ss = client.create(SPREADSHEET_NAME)
        return ss

def ensure_habit_sheets():
    """Auto-create Habits and HabitLogs tabs if they don't exist. Safe on existing data."""
    ss = get_ss()
    existing = [ws.title for ws in ss.worksheets()]

    if "Habits" not in existing:
        ws = ss.add_worksheet(title="Habits", rows=500, cols=len(HABIT_HEADERS))
        ws.append_row(HABIT_HEADERS)
        ws.format("1:1", {"textFormat": {"bold": True}})

    if "HabitLogs" not in existing:
        ws = ss.add_worksheet(title="HabitLogs", rows=5000, cols=len(LOG_HEADERS))
        ws.append_row(LOG_HEADERS)
        ws.format("1:1", {"textFormat": {"bold": True}})


# ═══════════════════════════════════════════════════════════════════════════════
#  CRUD — HABITS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=15)
def load_habits() -> pd.DataFrame:
    ss = get_ss()
    data = ss.worksheet("Habits").get_all_records()
    if not data:
        return pd.DataFrame(columns=HABIT_HEADERS)
    df = pd.DataFrame(data)
    df["Order"]  = pd.to_numeric(df["Order"], errors="coerce").fillna(99).astype(int)
    df["Active"] = df["Active"].astype(str).str.upper().isin(["TRUE", "YES", "1"])
    return df.sort_values("Order").reset_index(drop=True)

@st.cache_data(ttl=15)
def load_logs(days_back: int = 25) -> pd.DataFrame:
    ss = get_ss()
    data = ss.worksheet("HabitLogs").get_all_records()
    if not data:
        return pd.DataFrame(columns=LOG_HEADERS)
    df = pd.DataFrame(data)
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    df = df[df["Date"] >= cutoff]
    return df.reset_index(drop=True)

def write_log(habit_id: str, habit_name: str, log_date: str):
    """Write a completed log entry. Idempotent — checks for duplicate first."""
    ss = get_ss()
    ws = ss.worksheet("HabitLogs")
    # Check for existing entry
    all_data = ws.get_all_records()
    for row in all_data:
        if str(row.get("Date", "")) == log_date and str(row.get("HabitID", "")) == habit_id:
            return  # Already exists
    ws.append_row([
        str(uuid.uuid4())[:8],
        log_date,
        habit_id,
        habit_name,
    ])
    st.cache_data.clear()

def delete_log(habit_id: str, log_date: str):
    """Remove a completed log entry (un-check a habit)."""
    ss = get_ss()
    ws = ss.worksheet("HabitLogs")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    date_col = hdrs.index("Date") if "Date" in hdrs else 1
    id_col   = hdrs.index("HabitID") if "HabitID" in hdrs else 2
    for i, row in enumerate(all_vals[1:], start=2):
        if len(row) > max(date_col, id_col):
            if row[date_col] == log_date and row[id_col] == habit_id:
                ws.delete_rows(i)
                st.cache_data.clear()
                return

def write_habit(name: str, icon: str, order: int):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    ws.append_row([
        str(uuid.uuid4())[:8],
        name.strip(),
        icon.strip() or "🎯",
        order,
        date.today().isoformat(),
        "TRUE",
    ])
    st.cache_data.clear()

def update_habit_order(habit_id: str, new_order: int):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col  = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    ord_col = hdrs.index("Order")   if "Order"   in hdrs else 3
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == habit_id:
            ws.update_cell(i, ord_col + 1, new_order)
            break
    st.cache_data.clear()

def toggle_habit_active(habit_id: str, current_active: bool):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col  = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    act_col = hdrs.index("Active")  if "Active"  in hdrs else 5
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == habit_id:
            ws.update_cell(i, act_col + 1, "FALSE" if current_active else "TRUE")
            break
    st.cache_data.clear()

def delete_habit(habit_id: str):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == habit_id:
            ws.delete_rows(i)
            break
    st.cache_data.clear()

def swap_habit_orders(id_a: str, order_a: int, id_b: str, order_b: int):
    """Swap order values of two habits (for ↑ ↓ reorder)."""
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col  = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    ord_col = hdrs.index("Order")   if "Order"   in hdrs else 3
    rows_to_update = {}
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == id_a:
            rows_to_update[id_a] = i
        if row[id_col] == id_b:
            rows_to_update[id_b] = i
        if len(rows_to_update) == 2:
            break
    if id_a in rows_to_update:
        ws.update_cell(rows_to_update[id_a], ord_col + 1, order_b)
    if id_b in rows_to_update:
        ws.update_cell(rows_to_update[id_b], ord_col + 1, order_a)
    st.cache_data.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def compute_daily_score(
    target_date: date,
    active_habits: pd.DataFrame,
    logs_df: pd.DataFrame,
) -> float | None:
    """
    Score for a given date.
    Denominator = active habits whose CreatedDate <= target_date.
    Numerator   = completed log entries for that date (in logs_df).
    Returns None if no applicable habits existed on that date.
    """
    date_str = target_date.isoformat()

    # Habits that existed on this date
    applicable = active_habits[active_habits["CreatedDate"] <= date_str]
    total = len(applicable)
    if total == 0:
        return None

    if logs_df.empty:
        # No logs at all — today = 0 pending, past = 0 (all missed)
        return 0.0

    day_logs = logs_df[logs_df["Date"] == date_str]
    completed_ids = set(day_logs["HabitID"].astype(str).tolist())
    applicable_ids = set(applicable["HabitID"].astype(str).tolist())

    done = len(completed_ids & applicable_ids)
    return round(done / total * 100, 1)


def compute_21day_scores(
    active_habits: pd.DataFrame,
    logs_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: Date, Score
    for the last 21 days. Score = None if no habits existed.
    """
    today = date.today()
    rows = []
    for i in range(20, -1, -1):
        d = today - timedelta(days=i)
        score = compute_daily_score(d, active_habits, logs_df)
        rows.append({"Date": d, "Score": score})
    return pd.DataFrame(rows)


def compute_habit_streak(habit_id: str, logs_df: pd.DataFrame) -> int:
    """
    Consecutive days ending today where this habit was completed.
    """
    today = date.today()
    if logs_df.empty:
        return 0
    completed_dates = set(
        logs_df[logs_df["HabitID"].astype(str) == habit_id]["Date"].tolist()
    )
    streak = 0
    # Start from today going backwards
    check = today
    while True:
        if check.isoformat() in completed_dates:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


def compute_overall_streak(active_habits: pd.DataFrame, logs_df: pd.DataFrame) -> int:
    """
    Consecutive days ending today (or yesterday if today not yet complete)
    where score was 100%.
    """
    today = date.today()
    streak = 0
    check = today
    for _ in range(365):  # cap search at 1 year
        score = compute_daily_score(check, active_habits, logs_df)
        if score is None:
            break
        if score == 100.0:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


def get_today_status(active_habits: pd.DataFrame, logs_df: pd.DataFrame):
    """
    Returns: completed_count, total_count, completed_ids (set of HabitID strings)
    """
    today_str = date.today().isoformat()
    if logs_df.empty:
        return 0, len(active_habits), set()

    today_logs    = logs_df[logs_df["Date"] == today_str]
    completed_ids = set(today_logs["HabitID"].astype(str).tolist())
    total         = len(active_habits)
    done          = len(completed_ids & set(active_habits["HabitID"].astype(str).tolist()))
    return done, total, completed_ids


# ═══════════════════════════════════════════════════════════════════════════════
#  CSS — mobile-first, dark theme, same tokens as ClearSpend
# ═══════════════════════════════════════════════════════════════════════════════

def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

*, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background:{C["bg"]} !important;
    color:{C["text"]};
    font-family:'Nunito', sans-serif;
}}

[data-testid="stAppViewContainer"] > .main {{
    max-width:480px; margin:0 auto; padding:0 0 80px 0 !important;
}}
.block-container {{
    padding:0 12px 80px !important; max-width:480px !important;
}}

[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="collapsedControl"],
[data-testid="stSidebar"],
footer, #MainMenu {{ display:none !important; }}

/* ── CARDS ── */
.card {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    border-radius:16px; padding:16px; margin:8px 0;
}}
.card-sm {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    border-radius:12px; padding:12px 14px; margin:4px 0;
}}

/* ── TYPOGRAPHY ── */
.page-title {{
    font-size:1.5rem; font-weight:900; color:{C["text"]}; padding:16px 4px 4px;
}}
.section-label {{
    font-size:.65rem; font-weight:800; letter-spacing:1.5px;
    text-transform:uppercase; color:{C["muted"]}; margin:16px 0 8px 2px;
}}
.hero-num {{
    font-family:'JetBrains Mono',monospace; font-size:2.4rem;
    font-weight:700; color:{C["primary"]}; line-height:1;
}}
.mono {{ font-family:'JetBrains Mono',monospace; font-weight:600; }}

/* ── PROGRESS BAR ── */
.bar-wrap {{
    background:{C["surface2"]}; border-radius:100px;
    height:8px; overflow:hidden; margin:6px 0;
}}
.bar-fill {{
    height:100%; border-radius:100px; transition:width .5s ease;
}}

/* ── HABIT ROW ── */
.habit-row {{
    display:flex; align-items:center; gap:12px;
    padding:12px 14px;
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px; margin:4px 0;
    transition: border-color .2s;
}}
.habit-row.done {{
    border-color:{C["income"]}33;
    background: linear-gradient(90deg, {C["surface"]} 0%, rgba(0,200,150,0.04) 100%);
}}
.habit-icon {{
    width:42px; height:42px; border-radius:12px;
    background:{C["surface2"]};
    display:flex; align-items:center; justify-content:center;
    font-size:1.2rem; flex-shrink:0;
}}
.habit-icon.done-icon {{
    background:rgba(0,200,150,0.15);
}}

/* ── STREAK BADGE ── */
.streak-badge {{
    background:rgba(249,115,22,0.15); color:#f97316;
    font-size:.62rem; font-weight:800; letter-spacing:.5px;
    padding:2px 7px; border-radius:20px; text-transform:uppercase;
    white-space:nowrap;
}}
.pending-badge {{
    background:{C["surface2"]}; color:{C["muted"]};
    font-size:.62rem; font-weight:700;
    padding:2px 7px; border-radius:20px;
    white-space:nowrap;
}}
.missed-badge {{
    background:rgba(255,79,109,0.12); color:{C["expense"]};
    font-size:.62rem; font-weight:800;
    padding:2px 7px; border-radius:20px;
    white-space:nowrap;
}}

/* ── ALL BUTTONS RESET ── */
[data-testid="stButton"] > button {{
    background:transparent !important;
    border:none !important; color:{C["muted"]} !important;
    font-family:'Nunito',sans-serif !important;
    font-size:.68rem !important; font-weight:700 !important;
    padding:4px 6px !important; border-radius:10px !important;
    width:100% !important; line-height:1.4 !important;
    white-space:nowrap !important; box-shadow:none !important;
    transition:color .2s, background .2s !important;
}}
[data-testid="stButton"] > button:hover {{
    color:{C["primary"]} !important;
    background:{C["primary_dim"]} !important;
}}

/* ── NAV ACTIVE ── */
.nav-on [data-testid="stButton"] > button {{
    color:{C["primary"]} !important;
    background:{C["primary_dim"]} !important;
}}

/* ── TOGGLE BUTTON — done ── */
.toggle-done [data-testid="stButton"] > button {{
    background:rgba(0,200,150,0.18) !important;
    color:{C["income"]} !important;
    border:1px solid {C["income"]} !important;
    border-radius:50% !important;
    width:40px !important; height:40px !important;
    font-size:1.1rem !important; padding:0 !important;
    min-height:unset !important;
}}

/* ── TOGGLE BUTTON — pending ── */
.toggle-pending [data-testid="stButton"] > button {{
    background:{C["surface2"]} !important;
    color:{C["muted"]} !important;
    border:1.5px solid {C["border"]} !important;
    border-radius:50% !important;
    width:40px !important; height:40px !important;
    font-size:1.1rem !important; padding:0 !important;
    min-height:unset !important;
}}
.toggle-pending [data-testid="stButton"] > button:hover {{
    border-color:{C["income"]} !important;
    color:{C["income"]} !important;
    background:rgba(0,200,150,0.08) !important;
}}

/* ── PRIMARY ACTION ── */
[data-testid="stFormSubmitButton"] > button,
[data-testid="stButton"] > button[kind="primary"] {{
    background:{C["primary"]} !important;
    color:white !important; border-radius:12px !important;
    font-size:.9rem !important; font-weight:800 !important;
    padding:10px 16px !important;
    box-shadow:0 3px 12px rgba(124,109,248,.4) !important;
}}

/* ── REORDER BUTTONS ── */
.reorder-btn [data-testid="stButton"] > button {{
    background:{C["surface2"]} !important;
    color:{C["muted"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:8px !important;
    font-size:.8rem !important;
    padding:2px 6px !important;
    width:32px !important; height:32px !important;
    min-height:unset !important;
}}
.reorder-btn [data-testid="stButton"] > button:hover {{
    border-color:{C["primary"]} !important;
    color:{C["primary"]} !important;
}}

/* ── DELETE BUTTON ── */
.del-btn [data-testid="stButton"] > button {{
    background:rgba(255,79,109,.1) !important;
    color:{C["expense"]} !important;
    border:1px solid rgba(255,79,109,.3) !important;
    border-radius:8px !important;
    font-size:.72rem !important;
    padding:3px 8px !important;
    width:auto !important;
}}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {{
    background:{C["surface2"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:10px !important;
    color:{C["text"]} !important;
    font-family:'Nunito',sans-serif !important;
    font-size:.9rem !important;
}}
[data-testid="stSelectbox"] > div > div {{
    background:{C["surface2"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:10px !important;
    color:{C["text"]} !important;
}}

/* ── EXPANDER ── */
[data-testid="stExpander"] {{
    background:{C["surface"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:12px !important;
}}
[data-testid="stExpander"] summary {{
    color:{C["text"]} !important; font-weight:700 !important;
}}

/* ── ALERTS ── */
[data-testid="stAlert"] {{ border-radius:12px !important; border:none !important; }}

/* ── DIVIDER ── */
hr {{ border-color:{C["border"]} !important; margin:14px 0 !important; }}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {{ width:3px; }}
::-webkit-scrollbar-thumb {{ background:{C["border"]}; border-radius:2px; }}

/* ── TOP NAV DROPDOWN ── */
div[data-key="habit_nav_dd"] > div > div > div {{
    background:rgba(124,109,248,0.12) !important;
    border:1px solid #7c6df8 !important;
    border-radius:10px !important;
    font-weight:800 !important; font-size:.82rem !important;
}}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "habit_nav":    "today",
        "setup_ok":     False,
        "confirm_del":  None,   # habit_id pending delete confirmation
        "add_success":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════════════
#  TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_top_bar():
    NAV = {"today": "🔥 Today", "manage": "⚙️ Manage"}
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        current = NAV.get(st.session_state.habit_nav, "🔥 Today")
        choice  = st.selectbox("", list(NAV.values()),
                               index=list(NAV.values()).index(current),
                               key="habit_nav_dd", label_visibility="collapsed")
        chosen_key = [k for k, v in NAV.items() if v == choice][0]
        if chosen_key != st.session_state.habit_nav:
            st.session_state.habit_nav = chosen_key; st.rerun()
    with c2:
        if st.button("🔄", key="habit_reload", help="Refresh"):
            st.cache_data.clear(); st.rerun()
    with c3:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — TODAY
# ═══════════════════════════════════════════════════════════════════════════════

def screen_today():
    habits_df = load_habits()
    logs_df   = load_logs(days_back=25)
    active    = habits_df[habits_df["Active"] == True].copy()
    today     = date.today()
    today_str = today.isoformat()

    # ── HEADER ──────────────────────────────────────────────────────────────
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    dow  = today.strftime("%A")
    dstr = today.strftime("%d %B %Y")

    st.markdown(f"""
    <div style="padding:14px 4px 4px">
        <div style="color:{C['muted']};font-size:.8rem;font-weight:600">{dow}, {dstr}</div>
        <div style="font-size:1.5rem;font-weight:900;color:{C['text']}">{greeting} 🔥</div>
    </div>""", unsafe_allow_html=True)

    if active.empty:
        st.markdown(f"""
        <div class="card" style="text-align:center;padding:48px 20px">
            <div style="font-size:3rem">🌱</div>
            <div style="font-weight:800;font-size:1.1rem;margin:12px 0">No habits yet</div>
            <div style="color:{C['muted']};font-size:.85rem">
                Go to ⚙️ Manage to add your first habit
            </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── TODAY STATUS ────────────────────────────────────────────────────────
    done_count, total_count, completed_ids = get_today_status(active, logs_df)
    today_score = round(done_count / total_count * 100) if total_count > 0 else 0
    bar_color   = C["income"] if today_score == 100 else C["primary"] if today_score >= 50 else C["warning"]
    overall_streak = compute_overall_streak(active, logs_df)

    # ── SCORE + STREAK CARDS ────────────────────────────────────────────────
    cs1, cs2 = st.columns(2)
    with cs1:
        st.markdown(f"""
        <div class="card" style="background:linear-gradient(135deg,{C['surface']},{C['surface2']});text-align:center;padding:18px 10px">
            <div style="color:{C['muted']};font-size:.62rem;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:8px">Today's Score</div>
            <div class="hero-num" style="font-size:2.2rem;color:{bar_color}">{today_score}%</div>
            <div style="margin-top:10px">
                <div class="bar-wrap" style="height:6px">
                    <div class="bar-fill" style="width:{today_score}%;background:{bar_color}"></div>
                </div>
            </div>
            <div style="color:{C['muted']};font-size:.7rem;margin-top:6px">{done_count}/{total_count} done</div>
        </div>""", unsafe_allow_html=True)
    with cs2:
        st.markdown(f"""
        <div class="card" style="text-align:center;padding:18px 10px">
            <div style="color:{C['muted']};font-size:.62rem;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:8px">Perfect Days</div>
            <div style="font-size:2rem">{'🔥' if overall_streak > 0 else '💤'}</div>
            <div class="mono" style="font-size:1.4rem;color:{C['streak'] if overall_streak > 0 else C['muted']};margin-top:4px">{overall_streak}</div>
            <div style="color:{C['muted']};font-size:.7rem;margin-top:6px">day streak</div>
        </div>""", unsafe_allow_html=True)

    # ── 21-DAY CHART ────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">21-Day Score Trend</div>', unsafe_allow_html=True)
    scores_df = compute_21day_scores(active, logs_df)
    valid     = scores_df.dropna(subset=["Score"])

    if valid.empty:
        st.markdown(f"""
        <div class="card-sm" style="text-align:center;padding:24px;color:{C['muted']};font-size:.85rem">
            Complete habits to see your trend
        </div>""", unsafe_allow_html=True)
    else:
        # Build chart
        x_dates  = valid["Date"].astype(str).tolist()
        y_scores = valid["Score"].tolist()

        # Colour each point individually
        point_colors = []
        for s in y_scores:
            if s == 100:
                point_colors.append(C["income"])
            elif s >= 70:
                point_colors.append(C["primary"])
            elif s >= 40:
                point_colors.append(C["warning"])
            else:
                point_colors.append(C["expense"])

        # Today's point highlighted
        today_str_short = today_str
        today_idx = [i for i, d in enumerate(x_dates) if d == today_str_short]

        fig = go.Figure()

        # Fill area
        fig.add_trace(go.Scatter(
            x=x_dates, y=y_scores,
            mode="lines",
            line=dict(color=C["primary"], width=2.5),
            fill="tozeroy",
            fillcolor="rgba(124,109,248,0.08)",
            hovertemplate="%{x}<br>Score: %{y:.0f}%<extra></extra>",
        ))

        # Coloured dots
        fig.add_trace(go.Scatter(
            x=x_dates, y=y_scores,
            mode="markers",
            marker=dict(
                color=point_colors,
                size=[10 if i in today_idx else 6 for i in range(len(x_dates))],
                line=dict(color=C["bg"], width=1.5),
            ),
            hovertemplate="%{x}<br>Score: %{y:.0f}%<extra></extra>",
        ))

        # 100% reference line
        fig.add_hline(y=100, line_dash="dot", line_color=C["income"],
                      line_width=1, opacity=0.3)

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=C["text"],
            showlegend=False,
            height=200,
            margin=dict(l=4, r=4, t=10, b=4),
            xaxis=dict(
                gridcolor=C["border"], tickfont=dict(color=C["muted"], size=8),
                showgrid=False,
                # Show only first and last date labels
                tickmode="array",
                tickvals=[x_dates[0], x_dates[len(x_dates)//2], x_dates[-1]],
                ticktext=[
                    pd.Timestamp(x_dates[0]).strftime("%d %b"),
                    pd.Timestamp(x_dates[len(x_dates)//2]).strftime("%d %b"),
                    "Today",
                ],
            ),
            yaxis=dict(
                gridcolor=C["border"],
                tickfont=dict(color=C["muted"], size=8),
                range=[-5, 110],
                ticksuffix="%",
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── TODAY'S HABITS ───────────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">Today\'s Habits</div>', unsafe_allow_html=True)

    # Celebration message
    if total_count > 0 and done_count == total_count:
        st.markdown(f"""
        <div style="background:rgba(0,200,150,.1);border:1px solid rgba(0,200,150,.3);
             border-radius:12px;padding:12px 16px;margin-bottom:10px;text-align:center">
            <span style="font-size:1.3rem">🎉</span>
            <span style="font-weight:800;color:{C['income']};margin-left:8px">All habits done! Amazing day.</span>
        </div>""", unsafe_allow_html=True)

    # Render each habit
    for _, habit in active.iterrows():
        h_id     = str(habit["HabitID"])
        h_name   = str(habit["Name"])
        h_icon   = str(habit["Icon"]) or "🎯"
        is_done  = h_id in completed_ids
        streak   = compute_habit_streak(h_id, logs_df)

        # Row styling
        row_cls  = "habit-row done" if is_done else "habit-row"
        icon_cls = "habit-icon done-icon" if is_done else "habit-icon"

        col_main, col_toggle = st.columns([5, 1])
        with col_main:
            streak_html = ""
            if streak > 0:
                streak_html = f'<span class="streak-badge">🔥 {streak}d</span>'
            elif not is_done:
                streak_html = f'<span class="pending-badge">pending</span>'
            else:
                streak_html = f'<span class="streak-badge">🔥 1d</span>'

            name_color  = C["income"] if is_done else C["text"]
            name_style  = "text-decoration:line-through;opacity:0.6" if is_done else ""

            st.markdown(f"""
            <div class="{row_cls}">
                <div class="{icon_cls}">{h_icon}</div>
                <div style="flex:1;min-width:0">
                    <div style="font-weight:700;font-size:.88rem;color:{name_color};{name_style};
                         white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{h_name}</div>
                    <div style="margin-top:3px">{streak_html}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        with col_toggle:
            if is_done:
                st.markdown('<div class="toggle-done">', unsafe_allow_html=True)
                if st.button("✓", key=f"tog_{h_id}_{today_str}", help="Mark incomplete"):
                    delete_log(h_id, today_str)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="toggle-pending">', unsafe_allow_html=True)
                if st.button("○", key=f"tog_{h_id}_{today_str}", help="Mark complete"):
                    write_log(h_id, h_name, today_str)
                    st.toast(f"✓ {h_name}", icon="🎯")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ── PAST MISSED (last 3 days reminder) ───────────────────────────────────
    missed_any = False
    past_rows  = []
    for i in range(1, 4):
        past_date = today - timedelta(days=i)
        past_str  = past_date.isoformat()
        applicable = active[active["CreatedDate"] <= past_str]
        if applicable.empty:
            continue
        past_logs  = logs_df[logs_df["Date"] == past_str]["HabitID"].astype(str).tolist() if not logs_df.empty else []
        missed_habits = applicable[~applicable["HabitID"].astype(str).isin(past_logs)]
        if not missed_habits.empty:
            missed_any = True
            for _, mh in missed_habits.iterrows():
                past_rows.append({
                    "date": past_date.strftime("%d %b"),
                    "icon": mh["Icon"],
                    "name": mh["Name"],
                })

    if missed_any and past_rows:
        st.markdown(f'<div class="section-label">Missed Recently</div>', unsafe_allow_html=True)
        for r in past_rows[:5]:  # show max 5
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:6px 4px;
                 border-bottom:1px solid {C['surface2']}">
                <span style="font-size:.9rem">{r['icon']}</span>
                <span style="flex:1;font-size:.8rem;color:{C['muted']}">{r['name']}</span>
                <span class="missed-badge">✗ {r['date']}</span>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — MANAGE
# ═══════════════════════════════════════════════════════════════════════════════

def screen_manage():
    habits_df = load_habits()

    st.markdown('<div class="page-title">Manage Habits ⚙️</div>', unsafe_allow_html=True)

    # ── ADD NEW HABIT ────────────────────────────────────────────────────────
    with st.expander("➕  Add New Habit", expanded=habits_df.empty):
        st.markdown(f"<div style='color:{C['muted']};font-size:.8rem;margin-bottom:10px'>"
                    f"Habits are shown in Order number — set Order 1 for first thing in your morning.</div>",
                    unsafe_allow_html=True)

        with st.form("add_habit_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                new_name = st.text_input("Habit Name *",
                                          placeholder="e.g. Drink a bottle of water")
            with c2:
                new_icon = st.text_input("Icon", value="🎯",
                                          placeholder="🎯")

            # Auto-compute next order
            next_order = (int(habits_df["Order"].max()) + 1) if not habits_df.empty else 1
            new_order = st.number_input("Position in day (Order)",
                                         value=next_order, min_value=1, step=1,
                                         help="1 = first thing in the morning. Lower = earlier in day.")

            submitted = st.form_submit_button("💾 Add Habit", use_container_width=True,
                                               type="primary")
            if submitted:
                if new_name.strip():
                    write_habit(new_name.strip(), new_icon.strip() or "🎯", int(new_order))
                    st.success(f"✅ Added: {new_icon} {new_name}")
                    st.rerun()
                else:
                    st.error("Enter a habit name.")

    if habits_df.empty:
        return

    # ── ACTIVE HABITS ────────────────────────────────────────────────────────
    active_df   = habits_df[habits_df["Active"] == True].reset_index(drop=True)
    inactive_df = habits_df[habits_df["Active"] == False].reset_index(drop=True)

    st.markdown('<div class="section-label">Active Habits — drag to reorder</div>',
                unsafe_allow_html=True)

    for idx, habit in active_df.iterrows():
        h_id    = str(habit["HabitID"])
        h_name  = str(habit["Name"])
        h_icon  = str(habit["Icon"]) or "🎯"
        h_order = int(habit["Order"])

        st.markdown(f"""
        <div style="background:{C['surface2']};border:1px solid {C['border']};
             border-radius:12px;padding:10px 14px;margin:4px 0;
             display:flex;align-items:center;gap:10px">
            <span style="font-size:1.1rem;flex-shrink:0">{h_icon}</span>
            <div style="flex:1;min-width:0">
                <div style="font-weight:700;font-size:.85rem">{h_name}</div>
                <div style="font-size:.65rem;color:{C['muted']}">Position {h_order}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # Reorder + disable + delete buttons
        bc1, bc2, bc3, bc4, bc5 = st.columns([1, 1, 1, 1, 2])

        with bc1:
            st.markdown('<div class="reorder-btn">', unsafe_allow_html=True)
            up_disabled = (idx == 0)
            if st.button("↑", key=f"up_{h_id}", disabled=up_disabled,
                         help="Move up"):
                prev = active_df.iloc[idx - 1]
                swap_habit_orders(h_id, h_order,
                                  str(prev["HabitID"]), int(prev["Order"]))
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with bc2:
            st.markdown('<div class="reorder-btn">', unsafe_allow_html=True)
            dn_disabled = (idx == len(active_df) - 1)
            if st.button("↓", key=f"dn_{h_id}", disabled=dn_disabled,
                         help="Move down"):
                nxt = active_df.iloc[idx + 1]
                swap_habit_orders(h_id, h_order,
                                  str(nxt["HabitID"]), int(nxt["Order"]))
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with bc3:
            # Disable (move to inactive)
            st.markdown('<div class="reorder-btn">', unsafe_allow_html=True)
            if st.button("⏸", key=f"dis_{h_id}", help="Pause habit"):
                toggle_habit_active(h_id, True)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with bc4:
            # Delete with confirmation
            if st.session_state.confirm_del == h_id:
                st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                if st.button("✓ Sure?", key=f"confirm_{h_id}"):
                    delete_habit(h_id)
                    st.session_state.confirm_del = None
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{h_id}", help="Delete"):
                    st.session_state.confirm_del = h_id
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with bc5:
            if st.session_state.confirm_del == h_id:
                st.markdown(f"<div style='font-size:.65rem;color:{C['expense']};padding:8px 0'>"
                            f"This deletes all logs too.</div>",
                            unsafe_allow_html=True)

    # ── INACTIVE / PAUSED ────────────────────────────────────────────────────
    if not inactive_df.empty:
        st.markdown('<div class="section-label">Paused Habits</div>', unsafe_allow_html=True)
        for _, habit in inactive_df.iterrows():
            h_id   = str(habit["HabitID"])
            h_name = str(habit["Name"])
            h_icon = str(habit["Icon"]) or "🎯"

            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.markdown(f"""
                <div style="padding:8px 4px;display:flex;align-items:center;gap:10px;
                     opacity:0.5;border-bottom:1px solid {C['surface2']}">
                    <span style="font-size:.95rem">{h_icon}</span>
                    <span style="font-size:.82rem;color:{C['muted']}">{h_name}</span>
                </div>""", unsafe_allow_html=True)
            with col_btn:
                if st.button("▶ Resume", key=f"res_{h_id}"):
                    toggle_habit_active(h_id, False)
                    st.rerun()

    # ── STATS SUMMARY ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f'<div class="section-label">Quick Stats</div>', unsafe_allow_html=True)
    logs_df = load_logs(days_back=30)
    if not logs_df.empty and not active_df.empty:
        # Last 7 days average
        scores_7 = []
        for i in range(7):
            d = date.today() - timedelta(days=i)
            s = compute_daily_score(d, active_df, logs_df)
            if s is not None:
                scores_7.append(s)
        avg_7 = round(sum(scores_7) / len(scores_7)) if scores_7 else 0

        total_completions = len(logs_df)

        qs1, qs2 = st.columns(2)
        with qs1:
            st.markdown(f"""
            <div class="card-sm" style="text-align:center">
                <div style="font-size:.6rem;color:{C['muted']};font-weight:800;
                       letter-spacing:.8px;text-transform:uppercase">7-Day Avg</div>
                <div class="mono" style="font-size:1.3rem;color:{C['primary']}">{avg_7}%</div>
            </div>""", unsafe_allow_html=True)
        with qs2:
            st.markdown(f"""
            <div class="card-sm" style="text-align:center">
                <div style="font-size:.6rem;color:{C['muted']};font-weight:800;
                       letter-spacing:.8px;text-transform:uppercase">Total ✓</div>
                <div class="mono" style="font-size:1.3rem;color:{C['income']}">{total_completions}</div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SETUP
# ═══════════════════════════════════════════════════════════════════════════════

def run_setup():
    if not st.session_state.setup_ok:
        with st.spinner("⚡ Setting up HabitTracker..."):
            try:
                ensure_habit_sheets()
                st.session_state.setup_ok = True
            except Exception as ex:
                st.error(f"**Setup failed:** {ex}")
                st.markdown("""
**What to check:**
1. `GOOGLE_CREDENTIALS` secret is set in Streamlit Cloud → App Settings → Secrets.
2. The same service account used for ClearSpend will work here.
3. The spreadsheet name in this file is `ClearSpend` — same as your main app.
""")
                st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_state()
    inject_css()
    run_setup()

    render_top_bar()

    if st.session_state.habit_nav == "today":
        screen_today()
    elif st.session_state.habit_nav == "manage":
        screen_manage()


if __name__ == "__main__":
    main()
