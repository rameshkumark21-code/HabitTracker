"""
HabitTrack Pro — HabitKit UI Clone
Streamlit + Google Sheets backend
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import pytz
from streamlit_gsheets import GSheetsConnection
from streamlit_extras.stylable_container import stylable_container
import uuid
import calendar as cal_module

# ──────────────────────────────────────────────
# CONSTANTS & CONFIG
# ──────────────────────────────────────────────

APP_TZ = pytz.timezone("UTC")
MAX_PIN_ATTEMPTS = 5

ACCENT_COLORS = [
    "#22c55e",  # green
    "#3b82f6",  # blue
    "#a855f7",  # purple
    "#f97316",  # orange
    "#ef4444",  # red
    "#eab308",  # yellow
    "#06b6d4",  # cyan
    "#ec4899",  # pink
]

DEFAULT_HABITS = [
    {"HabitID": "h1", "Name": "Morning Exercise", "Icon": "🏃", "Color": "#22c55e",  "Target": "daily", "Active": 1, "SortOrder": 1},
    {"HabitID": "h2", "Name": "Read 30 Minutes",  "Icon": "📚", "Color": "#3b82f6",  "Target": "daily", "Active": 1, "SortOrder": 2},
    {"HabitID": "h3", "Name": "Meditate",          "Icon": "🧘", "Color": "#a855f7",  "Target": "daily", "Active": 1, "SortOrder": 3},
    {"HabitID": "h4", "Name": "Drink Water (2L)",  "Icon": "💧", "Color": "#06b6d4",  "Target": "daily", "Active": 1, "SortOrder": 4},
]

SHEET_LOG     = "Log"
SHEET_HABITS  = "Habits"
SHEET_SECURITY = "Security"

TABS = [
    ("📅", "Today"),
    ("📊", "Dashboard"),
    ("📆", "Calendar"),
    ("📈", "Stats"),
    ("🏷️", "Habits"),
    ("⚙️", "Manage"),
]

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="HabitTrack Pro",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# GLOBAL CSS
# ──────────────────────────────────────────────

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container {
    background: #0f0f0f !important;
    color: #f0f0f0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

.block-container { padding: 0.5rem 0.75rem 110px !important; max-width: 430px !important; margin: 0 auto !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: #0f0f0f; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

/* ── HABIT CARD ── */
.habit-card {
    background: #161616;
    border: 1px solid #222;
    border-radius: 16px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.habit-name  { font-size:.92rem; font-weight:600; color:#f0f0f0; }
.habit-meta  { font-size:.64rem; color:#555; margin-top:2px; }
.streak-badge {
    display:inline-flex; align-items:center; gap:3px;
    background:#1a1a1a; border-radius:20px; padding:3px 9px;
    font-size:.72rem; font-weight:700; color:#f97316;
}
.icon-badge {
    width:32px; height:32px; border-radius:10px;
    display:flex; align-items:center; justify-content:center;
    font-size:1rem; flex-shrink:0;
}

/* ── TODAY TAB ── */
.today-row {
    background:#161616; border:1px solid #222; border-radius:14px;
    padding:12px 14px; margin-bottom:6px;
    display:flex; align-items:center; justify-content:space-between;
}
.done-btn-outline {
    background:transparent; border:2px solid var(--hc);
    color:var(--hc); border-radius:50%; width:36px; height:36px;
    cursor:pointer; font-size:1.1rem; display:flex;
    align-items:center; justify-content:center;
}
.done-btn-filled {
    background:var(--hc); border:none; color:#fff;
    border-radius:50%; width:36px; height:36px;
    font-size:1.1rem; display:flex; align-items:center; justify-content:center;
}

/* ── CALENDAR ── */
.cal-day {
    background:#161616; border:1px solid #1e1e1e; border-radius:8px;
    padding:6px 4px; min-height:52px; font-size:.72rem; color:#555;
    text-align:center; position:relative;
}
.cal-day-today { border-color: #2563eb !important; }
.cal-dot { width:6px;height:6px;border-radius:50%;display:inline-block;margin:1px; }
.cal-header { font-size:.65rem; color:#555; text-align:center; padding:4px 0; font-weight:600; letter-spacing:.05em; }

/* ── PROGRESS BAR ── */
.prog-bar-wrap { background:#1e1e1e; border-radius:99px; height:6px; margin:10px 0 16px; }
.prog-bar-fill { border-radius:99px; height:6px; background:#3b82f6; transition:width .4s; }

/* ── PIN PAD ── */
.pin-dot { width:12px;height:12px;border-radius:50%;display:inline-block;margin:0 5px;background:#333; }
.pin-dot-filled { background:#f0f0f0; }
.pin-key {
    background:#1a1a1a; border:1px solid #2a2a2a; border-radius:12px;
    color:#f0f0f0; font-size:1.3rem; font-weight:600;
    padding:12px; cursor:pointer; width:100%; text-align:center;
}

/* ── SECTION HEADERS ── */
.section-title {
    font-size:.7rem; font-weight:700; color:#444;
    letter-spacing:.12em; text-transform:uppercase; margin:16px 0 8px;
}

/* ── STAT CARD ── */
.stat-card {
    background:#161616; border:1px solid #222; border-radius:14px;
    padding:14px; flex:1;
}
.stat-value { font-size:1.5rem; font-weight:800; color:#f0f0f0; line-height:1; }
.stat-label { font-size:.64rem; color:#555; margin-top:4px; }

/* ── MISC ── */
.date-header { font-size:1.3rem; font-weight:700; color:#2e2e2e; margin-bottom:14px; }
.all-done-msg { text-align:center; padding:40px 20px; color:#555; font-size:.9rem; }
.color-swatch {
    width:22px; height:22px; border-radius:50%;
    display:inline-block; cursor:pointer; margin:2px;
    border:2px solid transparent;
}
.color-swatch-active { border-color:#f0f0f0 !important; }

/* Remove Streamlit button default styles for nav usage */
[data-testid="stButton"] > button {
    font-family:'DM Sans',sans-serif !important;
}

/* Nav button style overrides - done via stylable_container key */
.stButton button {
    background: transparent !important;
    border: none !important;
    color: #555 !important;
    font-size: .65rem !important;
    font-weight:600 !important;
    padding: 6px 4px 2px !important;
    width: 100% !important;
    height: 54px !important;
    border-radius:0 !important;
    flex-direction: column !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:2px !important;
    cursor:pointer !important;
}

/* Expander clean */
details summary { color:#555 !important; font-size:.8rem !important; }
[data-testid="stExpander"] { background:#161616 !important; border:1px solid #222 !important; border-radius:12px !important; }

/* Input fields */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] > div > div {
    background:#1a1a1a !important; color:#f0f0f0 !important;
    border-color:#2a2a2a !important;
    font-family:'DM Sans',sans-serif !important;
}

/* Divider */
hr { border-color:#1e1e1e !important; margin:12px 0 !important; }

</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# GOOGLE SHEETS HELPERS
# ──────────────────────────────────────────────

@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def read_sheet(worksheet: str) -> pd.DataFrame:
    conn = get_conn()
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        if df is None:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()

def write_sheet(worksheet: str, df: pd.DataFrame):
    conn = get_conn()
    conn.update(worksheet=worksheet, data=df)
    st.cache_data.clear()


# ──────────────────────────────────────────────
# BOOTSTRAP
# ──────────────────────────────────────────────

def bootstrap_session():
    # Habits
    habits_df = read_sheet(SHEET_HABITS)
    if habits_df.empty or "HabitID" not in habits_df.columns:
        habits_df = pd.DataFrame(DEFAULT_HABITS)
        write_sheet(SHEET_HABITS, habits_df)
    st.session_state.habits_df = habits_df

    # Log
    log_df = read_sheet(SHEET_LOG)
    if log_df.empty or "Date" not in log_df.columns:
        log_df = pd.DataFrame(columns=["Date","Habit","Completed","Note","TimestampLogged"])
    log_df["Date"] = pd.to_datetime(log_df["Date"]).dt.date
    log_df["Completed"] = pd.to_numeric(log_df["Completed"], errors="coerce").fillna(0).astype(int)
    st.session_state.log_df = log_df

    # Security
    sec_df = read_sheet(SHEET_SECURITY)
    if sec_df.empty or "PIN" not in sec_df.columns:
        sec_df = pd.DataFrame({"PIN": [""]})
        write_sheet(SHEET_SECURITY, sec_df)
    pin_val = str(sec_df["PIN"].iloc[0]) if len(sec_df) > 0 else ""
    st.session_state.pin_hash = pin_val

    # Auto-miss detection
    auto_miss()

    st.session_state.bootstrapped = True


def auto_miss():
    """Mark yesterday's un-logged daily habits as missed (Completed=0)."""
    yesterday = date.today() - timedelta(days=1)
    habits_df = st.session_state.habits_df
    log_df = st.session_state.log_df

    active_daily = habits_df[
        (habits_df["Active"].astype(str) == "1") &
        (habits_df["Target"].str.lower() == "daily")
    ]
    for _, h in active_daily.iterrows():
        already = log_df[
            (log_df["Date"] == yesterday) &
            (log_df["Habit"] == h["HabitID"])
        ]
        if already.empty:
            new_row = pd.DataFrame([{
                "Date": yesterday,
                "Habit": h["HabitID"],
                "Completed": 0,
                "Note": "",
                "TimestampLogged": datetime.now().isoformat()
            }])
            log_df = pd.concat([log_df, new_row], ignore_index=True)
    st.session_state.log_df = log_df
    write_sheet(SHEET_LOG, log_df)


# ──────────────────────────────────────────────
# DATA HELPERS
# ──────────────────────────────────────────────

def today_date() -> date:
    return date.today()

def get_streak(habit_id: str) -> int:
    log_df = st.session_state.log_df
    habit_log = log_df[(log_df["Habit"] == habit_id) & (log_df["Completed"] == 1)]
    if habit_log.empty:
        return 0
    dates = sorted(habit_log["Date"].unique(), reverse=True)
    streak = 0
    check = today_date()
    for d in dates:
        if d == check:
            streak += 1
            check -= timedelta(days=1)
        elif d == check - timedelta(days=0):
            break
        else:
            break
    return streak

def get_best_streak(habit_id: str) -> int:
    log_df = st.session_state.log_df
    habit_log = log_df[(log_df["Habit"] == habit_id) & (log_df["Completed"] == 1)]
    if habit_log.empty:
        return 0
    dates = sorted(habit_log["Date"].unique())
    best = 1
    cur = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i-1] + timedelta(days=1):
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best

def get_completion_pct(habit_id: str, days: int = 30) -> float:
    log_df = st.session_state.log_df
    start = today_date() - timedelta(days=days - 1)
    habit_log = log_df[
        (log_df["Habit"] == habit_id) &
        (log_df["Date"] >= start) &
        (log_df["Date"] <= today_date())
    ]
    if habit_log.empty:
        return 0.0
    return habit_log["Completed"].sum() / days * 100

def is_done_today(habit_id: str) -> bool:
    log_df = st.session_state.log_df
    today = today_date()
    row = log_df[(log_df["Date"] == today) & (log_df["Habit"] == habit_id) & (log_df["Completed"] == 1)]
    return not row.empty

def toggle_habit_today(habit_id: str, note: str = ""):
    log_df = st.session_state.log_df
    today = today_date()
    existing = log_df[(log_df["Date"] == today) & (log_df["Habit"] == habit_id)]
    if existing.empty:
        # Add completed
        new_row = pd.DataFrame([{
            "Date": today, "Habit": habit_id,
            "Completed": 1, "Note": note,
            "TimestampLogged": datetime.now().isoformat()
        }])
        log_df = pd.concat([log_df, new_row], ignore_index=True)
    else:
        idx = existing.index[0]
        cur = log_df.at[idx, "Completed"]
        log_df.at[idx, "Completed"] = 0 if cur == 1 else 1
        if note:
            log_df.at[idx, "Note"] = note
    st.session_state.log_df = log_df
    write_sheet(SHEET_LOG, log_df)

def active_habits() -> pd.DataFrame:
    df = st.session_state.habits_df
    df["Active"] = pd.to_numeric(df["Active"], errors="coerce").fillna(0).astype(int)
    return df[df["Active"] == 1].sort_values("SortOrder", ignore_index=True)


# ──────────────────────────────────────────────
# TILE GRID RENDERER
# ──────────────────────────────────────────────

def render_habit_grid(habit_id: str, color: str, weeks: int = 18) -> str:
    log_df = st.session_state.log_df
    today = today_date()

    # Build date range: weeks*7 days ending today
    total_days = weeks * 7
    start_date = today - timedelta(days=total_days - 1)

    # Get completed dates for this habit
    habit_done = set(
        log_df[(log_df["Habit"] == habit_id) & (log_df["Completed"] == 1)]["Date"].tolist()
    )

    # Build date list: pad so first date is a Monday
    # We go back to the nearest Monday
    pad_start = start_date - timedelta(days=start_date.weekday())  # Monday
    all_dates = []
    d = pad_start
    while d <= today:
        all_dates.append(d)
        d += timedelta(days=1)

    # Ensure it's multiple of 7
    while len(all_dates) % 7 != 0:
        all_dates.append(all_dates[-1] + timedelta(days=1))

    tiles = []
    for d in all_dates:
        done = d in habit_done
        is_today = d == today
        in_range = d >= start_date

        if not in_range:
            bg = "transparent"
            outline = ""
        elif done:
            bg = color
            outline = ""
        else:
            bg = "#1e1e1e"
            outline = ""

        if is_today and in_range:
            outline = "outline:1px solid rgba(255,255,255,0.5);outline-offset:1px;"

        tiles.append(f"<div style='width:9px;height:9px;border-radius:2px;background:{bg};{outline}'></div>")

    grid = (
        "<div style='display:grid;"
        "grid-template-rows:repeat(7,9px);"
        "grid-auto-flow:column;"
        "gap:3px;"
        "overflow:hidden;'>"
        + "".join(tiles)
        + "</div>"
    )
    return grid


# ──────────────────────────────────────────────
# PIN GATE
# ──────────────────────────────────────────────

def show_pin_gate():
    pin_hash = st.session_state.get("pin_hash", "")
    if not pin_hash:
        st.session_state.authenticated = True
        return

    if st.session_state.get("authenticated"):
        return

    attempts = st.session_state.get("pin_attempts", 0)
    if attempts >= MAX_PIN_ATTEMPTS:
        st.error("Too many failed attempts. Restart the app.")
        st.stop()

    st.markdown("<br><br>", unsafe_allow_html=True)

    entered = st.session_state.get("pin_entered", "")

    # Dots
    dots_html = "<div style='display:flex;justify-content:center;gap:12px;margin:20px 0;'>"
    for i in range(4):
        cls = "pin-dot pin-dot-filled" if i < len(entered) else "pin-dot"
        dots_html += f"<span class='{cls}'></span>"
    dots_html += "</div>"

    with stylable_container("pin_gate", css_styles="""
        {background:#161616; border:1px solid #222; border-radius:20px;
         padding:24px 16px; max-width:300px; margin:0 auto;}
    """):
        st.markdown("<div style='text-align:center;font-size:1rem;font-weight:700;color:#f0f0f0;margin-bottom:8px;'>🔐 Enter PIN</div>", unsafe_allow_html=True)
        st.markdown(dots_html, unsafe_allow_html=True)

        keys = [["1","2","3"],["4","5","6"],["7","8","9"],["←","0","✓"]]
        for row in keys:
            c1, c2, c3 = st.columns(3)
            for col, k in zip([c1, c2, c3], row):
                with col:
                    if st.button(k, key=f"pin_{k}_{''.join(row)}", use_container_width=True):
                        if k == "←":
                            st.session_state.pin_entered = entered[:-1]
                        elif k == "✓":
                            if entered == pin_hash:
                                st.session_state.authenticated = True
                                st.session_state.pin_entered = ""
                            else:
                                st.session_state.pin_attempts = attempts + 1
                                st.session_state.pin_entered = ""
                                st.error(f"Wrong PIN ({MAX_PIN_ATTEMPTS - attempts - 1} attempts left)")
                        else:
                            new_pin = entered + k
                            st.session_state.pin_entered = new_pin
                            if len(new_pin) == 4:
                                if new_pin == pin_hash:
                                    st.session_state.authenticated = True
                                    st.session_state.pin_entered = ""
                                else:
                                    st.session_state.pin_attempts = attempts + 1
                                    st.session_state.pin_entered = ""
                                    st.error(f"Wrong PIN ({MAX_PIN_ATTEMPTS - attempts - 1} attempts left)")
                        st.rerun()

    st.stop()


# ──────────────────────────────────────────────
# BOTTOM NAV
# ──────────────────────────────────────────────

def render_nav():
    active = st.session_state.get("active_tab", 0)

    with stylable_container(
        key="bottom_nav",
        css_styles="""
        {
            position: fixed;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 430px;
            background: rgba(15,15,15,0.95);
            border-top: 1px solid #1e1e1e;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            z-index: 9999;
            padding: 0 4px;
        }
        """,
    ):
        cols = st.columns(6)
        for i, (icon, label) in enumerate(TABS):
            with cols[i]:
                is_active = active == i
                border_style = "border-top: 2px solid #3b82f6;" if is_active else "border-top: 2px solid transparent;"
                color_style = "color: #3b82f6 !important;" if is_active else "color: #555 !important;"

                with stylable_container(
                    key=f"nav_btn_{i}",
                    css_styles=f"""
                    button {{
                        {border_style}
                        {color_style}
                        background: transparent !important;
                        border-left: none !important;
                        border-right: none !important;
                        border-bottom: none !important;
                        border-radius: 0 !important;
                        width: 100% !important;
                        height: 54px !important;
                        font-size: .58rem !important;
                        font-weight: 600 !important;
                        padding: 4px 0 2px !important;
                        display: flex !important;
                        flex-direction: column !important;
                        align-items: center !important;
                        gap: 1px !important;
                    }}
                    """,
                ):
                    if st.button(f"{icon}\n{label}", key=f"nav_{i}"):
                        st.session_state.active_tab = i
                        st.rerun()


# ──────────────────────────────────────────────
# TAB 0: TODAY
# ──────────────────────────────────────────────

def tab_today():
    today = today_date()
    day_str = today.strftime("%A, %-d %b")
    st.markdown(f"<div class='date-header'>{day_str}</div>", unsafe_allow_html=True)

    habits = active_habits()
    if habits.empty:
        st.markdown("<div class='all-done-msg'>No habits yet.<br>Add one in the Habits tab 🌱</div>", unsafe_allow_html=True)
        return

    total = len(habits)
    done_count = sum(1 for _, h in habits.iterrows() if is_done_today(h["HabitID"]))

    # Progress bar
    pct = done_count / total if total else 0
    st.markdown(f"""
    <div style='display:flex;justify-content:space-between;font-size:.72rem;color:#555;margin-bottom:4px;'>
        <span>Today's Progress</span>
        <span style='color:#3b82f6;font-weight:700;'>{done_count} / {total}</span>
    </div>
    <div class='prog-bar-wrap'>
        <div class='prog-bar-fill' style='width:{pct*100:.0f}%;'></div>
    </div>
    """, unsafe_allow_html=True)

    if done_count == total and total > 0:
        st.markdown("<div class='all-done-msg'>All done! 🎉<br><span style='font-size:.75rem;color:#2e2e2e;'>Great work today!</span></div>", unsafe_allow_html=True)
        return

    for _, h in habits.iterrows():
        hid = h["HabitID"]
        color = h.get("Color", "#3b82f6")
        icon = h.get("Icon", "⭐")
        name = h["Name"]
        streak = get_streak(hid)
        done = is_done_today(hid)

        # Card row
        btn_style = (
            f"background:{color};border:none;color:#fff;"
            if done else
            f"background:transparent;border:2px solid {color};color:{color};"
        )

        col_left, col_right = st.columns([5, 1])
        with col_left:
            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:10px;'>
                <div class='icon-badge' style='background:{color}22;'>
                    <span>{icon}</span>
                </div>
                <div>
                    <div class='habit-name'>{name}</div>
                    <span class='streak-badge'>🔥 {streak} days</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            btn_label = "✓" if done else "○"
            with stylable_container(key=f"today_btn_{hid}", css_styles=f"""
                button {{
                    {btn_style}
                    border-radius:50% !important;
                    width:36px !important; height:36px !important;
                    padding:0 !important; font-size:1rem !important;
                    font-weight:700 !important; min-height:36px !important;
                }}
            """):
                if st.button(btn_label, key=f"toggle_{hid}"):
                    toggle_habit_today(hid)
                    st.rerun()

        # Note expander if done
        if done:
            with st.expander("Add note", expanded=False):
                note = st.text_area("Note", key=f"note_{hid}", label_visibility="collapsed", placeholder="How did it go?")
                if st.button("Save note", key=f"save_note_{hid}"):
                    toggle_habit_today(hid, note)
                    st.rerun()

        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# TAB 1: DASHBOARD
# ──────────────────────────────────────────────

def tab_dashboard():
    st.markdown("<div class='section-title'>Habit Overview</div>", unsafe_allow_html=True)

    habits = active_habits()
    if habits.empty:
        st.markdown("<div class='all-done-msg'>No habits yet.</div>", unsafe_allow_html=True)
        return

    # Sort control
    sort_by = st.selectbox(
        "", ["Streak", "Name", "Completion %"],
        key="dash_sort", label_visibility="collapsed"
    )

    habit_list = habits.to_dict("records")
    if sort_by == "Streak":
        habit_list.sort(key=lambda h: get_streak(h["HabitID"]), reverse=True)
    elif sort_by == "Name":
        habit_list.sort(key=lambda h: h["Name"])
    else:
        habit_list.sort(key=lambda h: get_completion_pct(h["HabitID"]), reverse=True)

    for h in habit_list:
        hid = h["HabitID"]
        color = h.get("Color", "#3b82f6")
        icon = h.get("Icon", "⭐")
        name = h["Name"]
        streak = get_streak(hid)
        pct30 = get_completion_pct(hid, 30)
        total_done = len(st.session_state.log_df[
            (st.session_state.log_df["Habit"] == hid) &
            (st.session_state.log_df["Completed"] == 1)
        ])

        grid_html = render_habit_grid(hid, color, weeks=18)

        st.markdown(f"""
        <div class='habit-card'>
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                <div class='icon-badge' style='background:{color}22;'>
                    <span>{icon}</span>
                </div>
                <div style='flex:1;'>
                    <div class='habit-name'>{name}</div>
                    <div class='habit-meta'>{h.get("Target","daily").capitalize()}</div>
                </div>
                <span class='streak-badge'>🔥 {streak}</span>
            </div>
            <div style='overflow-x:auto;padding-bottom:2px;'>
                {grid_html}
            </div>
            <div style='display:flex;justify-content:space-between;margin-top:8px;'>
                <span class='habit-meta'>{pct30:.0f}% last 30 days</span>
                <span class='habit-meta'>{total_done} total</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Add habit button
    st.markdown("<br>", unsafe_allow_html=True)
    with stylable_container("add_habit_dash", css_styles="""
        button {
            background: #161616 !important; border: 1px dashed #333 !important;
            color: #555 !important; border-radius: 12px !important;
            width: 100% !important; font-size:.85rem !important; height:44px !important;
        }
    """):
        if st.button("+ Add Habit", key="dash_add"):
            st.session_state.active_tab = 4
            st.rerun()


# ──────────────────────────────────────────────
# TAB 2: CALENDAR
# ──────────────────────────────────────────────

def tab_calendar():
    today = today_date()

    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month
    if "cal_selected" not in st.session_state:
        st.session_state.cal_selected = None

    year  = st.session_state.cal_year
    month = st.session_state.cal_month

    # Month nav
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        with stylable_container("cal_prev", css_styles="button{background:#161616!important;border:1px solid #222!important;color:#f0f0f0!important;border-radius:8px!important;width:100%!important;}"):
            if st.button("‹", key="cal_prev"):
                m = month - 1
                y = year
                if m < 1:
                    m = 12; y -= 1
                st.session_state.cal_month = m
                st.session_state.cal_year  = y
                st.rerun()
    with col2:
        st.markdown(f"<div style='text-align:center;font-size:.95rem;font-weight:700;color:#f0f0f0;padding:6px 0;'>{date(year, month, 1).strftime('%B %Y')}</div>", unsafe_allow_html=True)
    with col3:
        with stylable_container("cal_next", css_styles="button{background:#161616!important;border:1px solid #222!important;color:#f0f0f0!important;border-radius:8px!important;width:100%!important;}"):
            if st.button("›", key="cal_next"):
                m = month + 1
                y = year
                if m > 12:
                    m = 1; y += 1
                st.session_state.cal_month = m
                st.session_state.cal_year  = y
                st.rerun()

    # Day headers
    day_names = ["Mo","Tu","We","Th","Fr","Sa","Su"]
    hcols = st.columns(7)
    for i, dn in enumerate(day_names):
        with hcols[i]:
            st.markdown(f"<div class='cal-header'>{dn}</div>", unsafe_allow_html=True)

    # Build calendar
    habits = active_habits()
    log_df = st.session_state.log_df

    # Precompute: dates → list of habit colors done
    month_cal = cal_module.monthcalendar(year, month)

    def get_dots_for_day(d: date) -> str:
        done_habits = log_df[
            (log_df["Date"] == d) & (log_df["Completed"] == 1)
        ]["Habit"].tolist()
        dots = ""
        for hid in done_habits:
            row = habits[habits["HabitID"] == hid]
            if not row.empty:
                c = row.iloc[0]["Color"]
                dots += f"<span class='cal-dot' style='background:{c};'></span>"
        return dots

    for week in month_cal:
        wcols = st.columns(7)
        for i, day_num in enumerate(week):
            with wcols[i]:
                if day_num == 0:
                    st.markdown("<div style='min-height:52px;'></div>", unsafe_allow_html=True)
                else:
                    d = date(year, month, day_num)
                    is_today = d == today
                    is_selected = st.session_state.cal_selected == d
                    today_cls = "cal-day-today" if is_today else ""
                    sel_style = "border-color:#f97316!important;" if is_selected else ""
                    dots = get_dots_for_day(d)
                    st.markdown(f"""
                    <div class='cal-day {today_cls}' style='{sel_style}' id='cal_{day_num}'>
                        <div style='font-size:.7rem;color:{"#f0f0f0" if is_today else "#555"};font-weight:{"700" if is_today else "400"};'>{day_num}</div>
                        <div style='display:flex;flex-wrap:wrap;margin-top:3px;justify-content:center;'>{dots}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("", key=f"cal_day_{day_num}_{month}_{year}",
                                 help=d.strftime("%b %d")):
                        st.session_state.cal_selected = d
                        st.rerun()

    # Selected day detail
    sel = st.session_state.cal_selected
    if sel:
        st.markdown(f"<div class='section-title'>{sel.strftime('%A, %B %-d')}</div>", unsafe_allow_html=True)
        done_that_day = log_df[(log_df["Date"] == sel) & (log_df["Completed"] == 1)]

        if done_that_day.empty:
            st.markdown("<div style='color:#555;font-size:.8rem;padding:8px 0;'>Nothing logged.</div>", unsafe_allow_html=True)
        else:
            for _, row in done_that_day.iterrows():
                h_row = habits[habits["HabitID"] == row["Habit"]]
                if h_row.empty:
                    continue
                h = h_row.iloc[0]
                color = h.get("Color", "#3b82f6")
                st.markdown(f"""
                <div style='display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #1e1e1e;'>
                    <div class='icon-badge' style='background:{color}22;width:24px;height:24px;font-size:.8rem;'>{h["Icon"]}</div>
                    <span style='font-size:.85rem;color:#f0f0f0;'>{h["Name"]}</span>
                    {"<span style='font-size:.7rem;color:#555;margin-left:auto;'>"+str(row['Note'])+"</span>" if row.get("Note") else ""}
                </div>
                """, unsafe_allow_html=True)

        # Completion % for this month
        total_possible = len(habits) * cal_module.monthrange(year, month)[1]
        total_done_month = len(log_df[
            (log_df["Date"].apply(lambda d: d.year == year and d.month == month)) &
            (log_df["Completed"] == 1)
        ]) if not log_df.empty else 0
        month_pct = total_done_month / total_possible * 100 if total_possible else 0
        st.markdown(f"""
        <div style='margin-top:12px;text-align:center;'>
            <div style='font-size:1.8rem;font-weight:800;color:#f0f0f0;'>{month_pct:.0f}%</div>
            <div style='font-size:.65rem;color:#555;'>Completion this month</div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# TAB 3: STATS
# ──────────────────────────────────────────────

def tab_stats():
    habits = active_habits()
    log_df = st.session_state.log_df
    today = today_date()

    # Perfect days
    if not log_df.empty and not habits.empty:
        total_h = len(habits)
        daily_done = log_df[log_df["Completed"]==1].groupby("Date")["Habit"].nunique()
        perfect_days = int((daily_done >= total_h).sum())
    else:
        perfect_days = 0

    # Heatmap: last 52 weeks
    st.markdown("<div class='section-title'>Contribution Heatmap</div>", unsafe_allow_html=True)

    weeks = 26
    heatmap_start = today - timedelta(days=weeks*7 - 1)
    pad = heatmap_start - timedelta(days=heatmap_start.weekday())
    heat_dates = []
    d = pad
    while d <= today:
        heat_dates.append(d)
        d += timedelta(days=1)

    total_h = max(len(habits), 1)
    heat_tiles = []
    for d in heat_dates:
        done_count = 0
        if not log_df.empty:
            done_count = len(log_df[(log_df["Date"]==d) & (log_df["Completed"]==1)])
        intensity = min(done_count / total_h, 1.0)
        if d > today:
            bg = "transparent"
        elif intensity == 0:
            bg = "#1e1e1e"
        else:
            # Interpolate from dark green to bright green
            g_val = int(50 + intensity * 155)
            bg = f"rgb(0,{g_val},60)"
        is_today = "outline:1px solid rgba(255,255,255,0.5);outline-offset:1px;" if d == today else ""
        heat_tiles.append(f"<div style='width:9px;height:9px;border-radius:2px;background:{bg};{is_today}'></div>")

    heatmap_html = (
        "<div style='overflow-x:auto;'>"
        "<div style='display:grid;grid-template-rows:repeat(7,9px);grid-auto-flow:column;gap:3px;'>"
        + "".join(heat_tiles)
        + "</div></div>"
    )
    st.markdown(heatmap_html, unsafe_allow_html=True)

    # Summary stats
    st.markdown("<div class='section-title'>Summary</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-value'>🏆 {perfect_days}</div>
            <div class='stat-label'>Perfect Days</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        total_completions = len(log_df[log_df["Completed"]==1]) if not log_df.empty else 0
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-value'>✅ {total_completions}</div>
            <div class='stat-label'>Total Completions</div>
        </div>
        """, unsafe_allow_html=True)

    # Per-habit stats
    st.markdown("<div class='section-title'>Per-Habit Stats</div>", unsafe_allow_html=True)

    for _, h in habits.iterrows():
        hid = h["HabitID"]
        color = h.get("Color", "#3b82f6")
        streak = get_streak(hid)
        best   = get_best_streak(hid)
        pct7   = get_completion_pct(hid, 7)
        pct30  = get_completion_pct(hid, 30)
        pct90  = get_completion_pct(hid, 90)
        total  = len(log_df[(log_df["Habit"]==hid) & (log_df["Completed"]==1)]) if not log_df.empty else 0

        st.markdown(f"""
        <div class='habit-card'>
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                <div class='icon-badge' style='background:{color}22;'>{h["Icon"]}</div>
                <div class='habit-name'>{h["Name"]}</div>
                <span class='streak-badge' style='margin-left:auto;'>🔥 {streak}</span>
            </div>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:#f0f0f0;'>{streak}</div>
                    <div class='habit-meta'>Current streak</div>
                </div>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:#f0f0f0;'>{best}</div>
                    <div class='habit-meta'>Best streak</div>
                </div>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:{color};'>{pct30:.0f}%</div>
                    <div class='habit-meta'>Last 30 days</div>
                </div>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:#f0f0f0;'>{total}</div>
                    <div class='habit-meta'>All-time total</div>
                </div>
            </div>
            <div style='margin-top:10px;'>
                <div style='display:flex;justify-content:space-between;font-size:.65rem;color:#555;margin-bottom:3px;'>
                    <span>7d {pct7:.0f}%</span><span>30d {pct30:.0f}%</span><span>90d {pct90:.0f}%</span>
                </div>
                <div style='background:#1e1e1e;border-radius:99px;height:4px;'>
                    <div style='background:{color};border-radius:99px;height:4px;width:{pct30:.0f}%;'></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Best day of week
    st.markdown("<div class='section-title'>Best Day of Week</div>", unsafe_allow_html=True)
    day_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    if not log_df.empty:
        log_copy = log_df[log_df["Completed"]==1].copy()
        log_copy["dow"] = pd.to_datetime(log_copy["Date"]).dt.dayofweek
        dow_counts = log_copy.groupby("dow").size().reindex(range(7), fill_value=0)
    else:
        dow_counts = pd.Series([0]*7)

    max_val = max(dow_counts.max(), 1)
    for i, (label, count) in enumerate(zip(day_labels, dow_counts)):
        bar_w = count / max_val * 100
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>
            <span style='font-size:.72rem;color:#555;width:28px;'>{label}</span>
            <div style='flex:1;background:#1e1e1e;border-radius:99px;height:8px;'>
                <div style='background:#3b82f6;border-radius:99px;height:8px;width:{bar_w:.0f}%;'></div>
            </div>
            <span style='font-size:.65rem;color:#555;width:20px;text-align:right;'>{count}</span>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# TAB 4: HABITS MANAGEMENT
# ──────────────────────────────────────────────

def tab_habits():
    habits_df = st.session_state.habits_df
    active = active_habits()

    st.markdown("<div class='section-title'>Active Habits</div>", unsafe_allow_html=True)

    for idx, row in habits_df[habits_df["Active"].astype(str)=="1"].iterrows():
        color = row.get("Color","#3b82f6")
        with st.expander(f"{row['Icon']} {row['Name']}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Name", value=row["Name"], key=f"hname_{idx}")
                new_icon = st.text_input("Icon (emoji)", value=row["Icon"], key=f"hicon_{idx}", max_chars=2)
            with c2:
                new_target = st.selectbox("Target", ["daily","3x per week","5x per week"], key=f"htgt_{idx}",
                    index=["daily","3x per week","5x per week"].index(row["Target"]) if row["Target"] in ["daily","3x per week","5x per week"] else 0)

            # Color swatches
            st.markdown("<div style='font-size:.7rem;color:#555;margin-bottom:4px;'>Color</div>", unsafe_allow_html=True)
            swatch_html = "<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
            for c in ACCENT_COLORS:
                sel = "border:2px solid #f0f0f0;" if c == color else "border:2px solid transparent;"
                swatch_html += f"<div class='color-swatch' style='background:{c};{sel}' title='{c}'></div>"
            swatch_html += "</div>"
            st.markdown(swatch_html, unsafe_allow_html=True)
            new_color = st.selectbox("Color value", ACCENT_COLORS, key=f"hcolor_{idx}",
                index=ACCENT_COLORS.index(color) if color in ACCENT_COLORS else 0,
                format_func=lambda c: c)

            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("💾 Save", key=f"save_habit_{idx}"):
                    habits_df.at[idx,"Name"]   = new_name
                    habits_df.at[idx,"Icon"]   = new_icon
                    habits_df.at[idx,"Target"] = new_target
                    habits_df.at[idx,"Color"]  = new_color
                    st.session_state.habits_df = habits_df
                    write_sheet(SHEET_HABITS, habits_df)
                    st.success("Saved!")
                    st.rerun()
            with bcol2:
                if st.button("🗃️ Archive", key=f"archive_{idx}"):
                    habits_df.at[idx,"Active"] = 0
                    st.session_state.habits_df = habits_df
                    write_sheet(SHEET_HABITS, habits_df)
                    st.rerun()

    # Add new habit
    st.markdown("<div class='section-title'>Add New Habit</div>", unsafe_allow_html=True)
    with stylable_container("add_habit_form", css_styles="""
        {background:#161616;border:1px solid #222;border-radius:16px;padding:14px;}
    """):
        n_name   = st.text_input("Habit Name", key="new_hname", placeholder="e.g. Morning Run")
        n_icon   = st.text_input("Icon (emoji)", key="new_hicon", value="⭐", max_chars=2)
        n_target = st.selectbox("Target", ["daily","3x per week","5x per week"], key="new_htgt")
        n_color  = st.selectbox("Color", ACCENT_COLORS, key="new_hcolor",
                    format_func=lambda c: c)

        if st.button("➕ Add Habit", key="add_habit_btn"):
            if n_name.strip():
                new_id = str(uuid.uuid4())[:8]
                max_order = int(habits_df["SortOrder"].max()) + 1 if not habits_df.empty else 1
                new_row = pd.DataFrame([{
                    "HabitID": new_id, "Name": n_name.strip(),
                    "Icon": n_icon, "Color": n_color,
                    "Target": n_target, "Active": 1, "SortOrder": max_order
                }])
                habits_df = pd.concat([habits_df, new_row], ignore_index=True)
                st.session_state.habits_df = habits_df
                write_sheet(SHEET_HABITS, habits_df)
                st.success(f"Added '{n_name}'!")
                st.rerun()
            else:
                st.warning("Please enter a habit name.")


# ──────────────────────────────────────────────
# TAB 5: MANAGE
# ──────────────────────────────────────────────

def tab_manage():
    habits_df = st.session_state.habits_df

    # Sort order
    st.markdown("<div class='section-title'>Sort Order</div>", unsafe_allow_html=True)
    active = habits_df[habits_df["Active"].astype(str)=="1"].sort_values("SortOrder")
    for i, (idx, row) in enumerate(active.iterrows()):
        c1, c2, c3 = st.columns([4,1,1])
        with c1:
            st.markdown(f"<div style='padding:8px;font-size:.85rem;color:#f0f0f0;'>{row['Icon']} {row['Name']}</div>", unsafe_allow_html=True)
        with c2:
            if st.button("▲", key=f"up_{idx}") and i > 0:
                prev_idx = active.index[i-1]
                habits_df.at[idx,"SortOrder"], habits_df.at[prev_idx,"SortOrder"] = \
                    habits_df.at[prev_idx,"SortOrder"], habits_df.at[idx,"SortOrder"]
                st.session_state.habits_df = habits_df
                write_sheet(SHEET_HABITS, habits_df)
                st.rerun()
        with c3:
            if st.button("▼", key=f"dn_{idx}") and i < len(active)-1:
                next_idx = active.index[i+1]
                habits_df.at[idx,"SortOrder"], habits_df.at[next_idx,"SortOrder"] = \
                    habits_df.at[next_idx,"SortOrder"], habits_df.at[idx,"SortOrder"]
                st.session_state.habits_df = habits_df
                write_sheet(SHEET_HABITS, habits_df)
                st.rerun()

    # Archive/restore
    archived = habits_df[habits_df["Active"].astype(str)=="0"]
    if not archived.empty:
        st.markdown("<div class='section-title'>Archived Habits</div>", unsafe_allow_html=True)
        for idx, row in archived.iterrows():
            c1, c2 = st.columns([4,1])
            with c1:
                st.markdown(f"<div style='padding:8px;font-size:.85rem;color:#555;'>{row['Icon']} {row['Name']}</div>", unsafe_allow_html=True)
            with c2:
                if st.button("↩️", key=f"restore_{idx}"):
                    habits_df.at[idx,"Active"] = 1
                    st.session_state.habits_df = habits_df
                    write_sheet(SHEET_HABITS, habits_df)
                    st.rerun()

    # Export CSV
    st.markdown("<div class='section-title'>Export</div>", unsafe_allow_html=True)
    log_df = st.session_state.log_df
    if not log_df.empty:
        csv = log_df.to_csv(index=False)
        st.download_button(
            "📥 Download Log CSV", data=csv,
            file_name="habittrack_log.csv", mime="text/csv",
            key="export_csv"
        )

    # Change PIN
    st.markdown("<div class='section-title'>Security</div>", unsafe_allow_html=True)
    with stylable_container("pin_change", css_styles="""
        {background:#161616;border:1px solid #222;border-radius:14px;padding:14px;}
    """):
        new_pin = st.text_input("New PIN (4 digits, leave blank to disable)", key="new_pin",
                                type="password", max_chars=4, placeholder="••••")
        if st.button("Set PIN", key="set_pin"):
            if new_pin and (not new_pin.isdigit() or len(new_pin) != 4):
                st.warning("PIN must be exactly 4 digits.")
            else:
                st.session_state.pin_hash = new_pin
                sec_df = pd.DataFrame({"PIN": [new_pin]})
                write_sheet(SHEET_SECURITY, sec_df)
                st.success("PIN updated!" if new_pin else "PIN disabled.")
                st.rerun()

    # Delete all log data
    st.markdown("<div class='section-title'>Danger Zone</div>", unsafe_allow_html=True)
    if st.button("🗑️ Clear All Log Data", key="clear_log"):
        if st.session_state.get("confirm_clear"):
            empty_log = pd.DataFrame(columns=["Date","Habit","Completed","Note","TimestampLogged"])
            st.session_state.log_df = empty_log
            write_sheet(SHEET_LOG, empty_log)
            st.session_state.confirm_clear = False
            st.success("Log cleared.")
            st.rerun()
        else:
            st.session_state.confirm_clear = True
            st.warning("Click again to confirm.")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    inject_css()

    # Bootstrap
    if not st.session_state.get("bootstrapped"):
        bootstrap_session()

    # Init session state
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "pin_entered" not in st.session_state:
        st.session_state.pin_entered = ""
    if "pin_attempts" not in st.session_state:
        st.session_state.pin_attempts = 0

    # PIN gate
    show_pin_gate()

    # Render active tab
    tab = st.session_state.active_tab
    if   tab == 0: tab_today()
    elif tab == 1: tab_dashboard()
    elif tab == 2: tab_calendar()
    elif tab == 3: tab_stats()
    elif tab == 4: tab_habits()
    elif tab == 5: tab_manage()

    # Bottom nav (always rendered last so it's on top)
    render_nav()


if __name__ == "__main__":
    main()
