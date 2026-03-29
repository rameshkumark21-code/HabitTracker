import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import json, uuid, calendar
import plotly.graph_objects as go

# \u2500\u2500 PAGE CONFIG \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
st.set_page_config(
    page_title="HabitTracker",
    page_icon="\ud83d\udd25",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# \u2500\u2500 DESIGN TOKENS \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
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

# \u2500\u2500 GOOGLE SHEETS \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_NAME = "ClearSpend"

HABIT_HEADERS = ["HabitID", "Name", "Icon", "Order", "CreatedDate", "Active"]
LOG_HEADERS   = ["LogID", "Date", "HabitID", "HabitName"]


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  GOOGLE SHEETS CONNECTION
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

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


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  CRUD \u2014 HABITS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

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
    ss = get_ss()
    ws = ss.worksheet("HabitLogs")
    all_data = ws.get_all_records()
    for row in all_data:
        if str(row.get("Date", "")) == log_date and str(row.get("HabitID", "")) == habit_id:
            return
    ws.append_row([str(uuid.uuid4())[:8], log_date, habit_id, habit_name])
    st.cache_data.clear()

def delete_log(habit_id: str, log_date: str):
    ss = get_ss()
    ws = ss.worksheet("HabitLogs")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    date_col = hdrs.index("Date")    if "Date"    in hdrs else 1
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
    ws.append_row([str(uuid.uuid4())[:8], name.strip(), icon.strip() or "\ud83c\udfaf",
                   order, date.today().isoformat(), "TRUE"])
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


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  SCORE ENGINE
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

def compute_daily_score(target_date: date, active_habits: pd.DataFrame,
                        logs_df: pd.DataFrame) -> float | None:
    date_str   = target_date.isoformat()
    applicable = active_habits[active_habits["CreatedDate"] <= date_str]
    total = len(applicable)
    if total == 0:
        return None
    if logs_df.empty:
        return 0.0
    day_logs       = logs_df[logs_df["Date"] == date_str]
    completed_ids  = set(day_logs["HabitID"].astype(str).tolist())
    applicable_ids = set(applicable["HabitID"].astype(str).tolist())
    done = len(completed_ids & applicable_ids)
    return round(done / total * 100, 1)

def compute_21day_scores(active_habits: pd.DataFrame,
                         logs_df: pd.DataFrame) -> pd.DataFrame:
    today = date.today()
    rows  = []
    for i in range(20, -1, -1):
        d     = today - timedelta(days=i)
        score = compute_daily_score(d, active_habits, logs_df)
        rows.append({"Date": d, "Score": score})
    return pd.DataFrame(rows)

def compute_habit_streak(habit_id: str, logs_df: pd.DataFrame) -> int:
    today = date.today()
    if logs_df.empty:
        return 0
    completed_dates = set(
        logs_df[logs_df["HabitID"].astype(str) == habit_id]["Date"].tolist()
    )
    streak = 0
    check  = today
    while True:
        if check.isoformat() in completed_dates:
            streak += 1
            check  -= timedelta(days=1)
        else:
            break
    return streak

def compute_overall_streak(active_habits: pd.DataFrame, logs_df: pd.DataFrame) -> int:
    today  = date.today()
    streak = 0
    check  = today
    for _ in range(365):
        score = compute_daily_score(check, active_habits, logs_df)
        if score is None:
            break
        if score == 100.0:
            streak += 1
            check  -= timedelta(days=1)
        else:
            break
    return streak

def get_today_status(active_habits: pd.DataFrame, logs_df: pd.DataFrame):
    today_str = date.today().isoformat()
    if logs_df.empty:
        return 0, len(active_habits), set()
    today_logs    = logs_df[logs_df["Date"] == today_str]
    completed_ids = set(today_logs["HabitID"].astype(str).tolist())
    total         = len(active_habits)
    done          = len(completed_ids & set(active_habits["HabitID"].astype(str).tolist()))
    return done, total, completed_ids


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  HELPERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

def _make_7day_dots(habit_id: str, created_date: str,
                    logs_df: pd.DataFrame, today: date) -> str:
    """7 small coloured circles: green=done, red=missed, grey=pending/N/A."""
    completed_dates: set[str] = set()
    if not logs_df.empty:
        completed_dates = set(
            logs_df[logs_df["HabitID"].astype(str) == habit_id]["Date"].tolist()
        )

    dots = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.isoformat()
        if d_str < created_date:
            bg, title = C["surface2"], "N/A"
            opacity   = "0.25"
        elif d_str in completed_dates:
            bg, title = C["income"], "Done"
            opacity   = "1"
        elif d == today:
            bg, title = C["border"], "Pending"
            opacity   = "1"
        else:
            bg, title = C["expense"], "Missed"
            opacity   = "0.55"

        day_label = d.strftime("%a")
        dots.append(
            f'<span title="{day_label}: {title}" style="'
            f'width:7px;height:7px;border-radius:50%;'
            f'background:{bg};opacity:{opacity};'
            f'display:inline-block;flex-shrink:0;'
            f'cursor:default"></span>'
        )

    return (
        '<div style="display:flex;gap:3px;align-items:center">'
        + "".join(dots)
        + "</div>"
    )


def _week_completion_pct(active_habits: pd.DataFrame, logs_df: pd.DataFrame) -> int:
    """% of habit-days completed in the last 7 days."""
    today      = date.today()
    total_opp  = 0
    total_done = 0
    for i in range(6, -1, -1):
        d       = today - timedelta(days=i)
        d_str   = d.isoformat()
        applic  = active_habits[active_habits["CreatedDate"] <= d_str]
        if applic.empty:
            continue
        total_opp += len(applic)
        if not logs_df.empty:
            day_done = set(
                logs_df[logs_df["Date"] == d_str]["HabitID"].astype(str).tolist()
            )
            total_done += len(day_done & set(applic["HabitID"].astype(str).tolist()))
    return round(total_done / total_opp * 100) if total_opp else 0


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  CSS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

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

/* \u2500\u2500 CARDS \u2500\u2500 */
.card {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    border-radius:16px; padding:16px; margin:8px 0;
}}
.card-sm {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    border-radius:12px; padding:12px 14px; margin:4px 0;
}}

/* \u2500\u2500 TYPOGRAPHY \u2500\u2500 */
.page-title {{
    font-size:1.3rem; font-weight:900; color:{C["text"]}; padding:12px 4px 2px;
}}
.section-label {{
    font-size:.62rem; font-weight:800; letter-spacing:1.5px;
    text-transform:uppercase; color:{C["muted"]}; margin:12px 0 6px 2px;
}}
.mono {{ font-family:'JetBrains Mono',monospace; font-weight:600; }}

/* \u2500\u2500 SLIM HEADER \u2500\u2500 */
.slim-header {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px;
    padding:12px 14px;
    margin:10px 0 6px;
}}

/* \u2500\u2500 PROGRESS BAR \u2500\u2500 */
.bar-wrap {{
    background:{C["surface2"]}; border-radius:100px;
    height:7px; overflow:hidden;
}}
.bar-fill {{
    height:100%; border-radius:100px; transition:width .5s ease;
}}

/* \u2500\u2500 COMPACT HABIT TABLE \u2500\u2500 */
.habit-table {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px;
    overflow:hidden;
    margin:6px 0;
}}

/* Remove default Streamlit vertical gaps inside habit-table */
.habit-table > div > div > div[data-testid="stVerticalBlock"] {{
    gap:0 !important;
}}
.habit-table [data-testid="stHorizontalBlock"] {{
    gap:4px !important;
    align-items:center !important;
    padding:0 8px !important;
    border-bottom:1px solid {C["surface2"]};
    min-height:40px;
}}
.habit-table [data-testid="stHorizontalBlock"]:last-child {{
    border-bottom:none;
}}
.habit-table [data-testid="column"] {{
    padding:0 !important;
    overflow:visible !important;
}}

/* \u2500\u2500 COMPACT ROW BODY \u2500\u2500 */
.hrow {{
    display:flex;
    align-items:center;
    gap:7px;
    padding:5px 4px 5px 0;
    min-height:36px;
    overflow:hidden;
}}
.hrow.done {{
    opacity:.75;
}}
.hrow-name {{
    flex:1;
    font-size:.82rem;
    font-weight:700;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    min-width:0;
}}
.hrow-right {{
    display:flex;
    align-items:center;
    gap:5px;
    flex-shrink:0;
}}

/* \u2500\u2500 STREAK BADGE \u2500\u2500 */
.streak-badge {{
    background:rgba(249,115,22,0.15); color:#f97316;
    font-size:.58rem; font-weight:800;
    padding:2px 6px; border-radius:20px;
    white-space:nowrap; letter-spacing:.3px;
}}

/* \u2500\u2500 ALL BUTTONS RESET \u2500\u2500 */
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

/* \u2500\u2500 TOGGLE DONE \u2500\u2500 */
.tog-done [data-testid="stButton"] > button {{
    background:rgba(0,200,150,0.18) !important;
    color:{C["income"]} !important;
    border:1.5px solid {C["income"]} !important;
    border-radius:50% !important;
    width:30px !important; height:30px !important;
    font-size:.9rem !important; padding:0 !important;
    min-height:unset !important;
}}

/* \u2500\u2500 TOGGLE PENDING \u2500\u2500 */
.tog-pend [data-testid="stButton"] > button {{
    background:{C["surface2"]} !important;
    color:{C["muted"]} !important;
    border:1.5px solid {C["border"]} !important;
    border-radius:50% !important;
    width:30px !important; height:30px !important;
    font-size:.9rem !important; padding:0 !important;
    min-height:unset !important;
}}
.tog-pend [data-testid="stButton"] > button:hover {{
    border-color:{C["income"]} !important;
    color:{C["income"]} !important;
    background:rgba(0,200,150,0.08) !important;
}}

/* \u2500\u2500 PRIMARY / FORM SUBMIT \u2500\u2500 */
[data-testid="stFormSubmitButton"] > button,
[data-testid="stButton"] > button[kind="primary"] {{
    background:{C["primary"]} !important;
    color:white !important; border-radius:12px !important;
    font-size:.9rem !important; font-weight:800 !important;
    padding:10px 16px !important;
    box-shadow:0 3px 12px rgba(124,109,248,.4) !important;
}}

/* \u2500\u2500 REORDER BUTTONS \u2500\u2500 */
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

/* \u2500\u2500 DELETE \u2500\u2500 */
.del-btn [data-testid="stButton"] > button {{
    background:rgba(255,79,109,.1) !important;
    color:{C["expense"]} !important;
    border:1px solid rgba(255,79,109,.3) !important;
    border-radius:8px !important;
    font-size:.72rem !important;
    padding:3px 8px !important;
    width:auto !important;
}}

/* \u2500\u2500 INPUTS \u2500\u2500 */
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

/* \u2500\u2500 EXPANDER \u2500\u2500 */
[data-testid="stExpander"] {{
    background:{C["surface"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:12px !important;
    margin:6px 0 !important;
}}
[data-testid="stExpander"] summary {{
    color:{C["text"]} !important; font-weight:700 !important;
    font-size:.82rem !important;
    padding:8px 12px !important;
}}

/* \u2500\u2500 ALERTS / HR \u2500\u2500 */
[data-testid="stAlert"] {{ border-radius:12px !important; border:none !important; }}
hr {{ border-color:{C["border"]} !important; margin:12px 0 !important; }}

/* \u2500\u2500 SCROLLBAR \u2500\u2500 */
::-webkit-scrollbar {{ width:3px; }}
::-webkit-scrollbar-thumb {{ background:{C["border"]}; border-radius:2px; }}

/* \u2500\u2500 NAV DROPDOWN \u2500\u2500 */
div[data-key="habit_nav_dd"] > div > div > div {{
    background:rgba(124,109,248,0.12) !important;
    border:1px solid #7c6df8 !important;
    border-radius:10px !important;
    font-weight:800 !important; font-size:.82rem !important;
}}

/* \u2500\u2500 LOG DATE PICKER LABEL \u2500\u2500 */
[data-testid="stDateInput"] label {{
    font-size:.72rem !important;
    color:{C["muted"]} !important;
}}
</style>
""", unsafe_allow_html=True)


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  SESSION STATE
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

def init_state():
    defaults = {
        "habit_nav":   "today",
        "setup_ok":    False,
        "confirm_del": None,
        "log_date":    date.today(),  # for backdating logs
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#