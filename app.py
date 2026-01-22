import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# -----------------------------
# Oregon Tech colors (primary)
# -----------------------------
OT_BLUE = "#003767"   # Blue
OT_GOLD = "#FFD24F"   # Gold
OT_DARK = "#0B1F3A"
OT_LIGHT = "#F6F8FB"
OT_GRAY = "#6B7280"

# A simple OIT-friendly palette (blue/gold + neutrals)
PALETTE = [OT_BLUE, OT_GOLD, "#1F4E79", "#D4A82A", "#2E2E2E", "#6B7280", "#B0B7C3", "#7A5C00"]

REQUIRED_COLUMNS = [
    "EventId", "Title", "Location", "Department", "EventDate", "StartTime", "EndTime",
    "IsAllDayEvent", "IsTimedEvent", "EventType", "ContactName", "ContactEmail",
    "ContactPhone", "IsReOccurring", "IsOnMultipleCalendars", "Status", "EventTypeName"
]

st.set_page_config(page_title="Room Reservations Dashboard", layout="wide")

# -----------------------------
# CSS (Oregon Tech feel)
# -----------------------------
st.markdown(
    f"""
    <style>
      .stApp {{ background: {OT_LIGHT}; }}
      .block-container {{ padding-top: 1.2rem; }}
      h1,h2,h3 {{ color: {OT_BLUE} !important; }}

      section[data-testid="stSidebar"] {{
        background: white;
        border-right: 4px solid {OT_GOLD};
      }}

      div[data-testid="stMetric"] {{
        background: white;
        border: 1px solid #E5E7EB;
        border-left: 6px solid {OT_GOLD};
        border-radius: 14px;
        padding: 0.75rem;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Room Reservations Dashboard")

# -----------------------------
# Load + Normalize
# -----------------------------
def load_reservations(upload) -> pd.DataFrame:
    # If no upload, try local file name "reservations.csv"
    if upload is None:
        try:
            return pd.read_csv("reservations.csv")
        except Exception:
            return None

    name = upload.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(upload)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(upload)

    raise ValueError("Please upload a CSV or Excel file.")

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.warning(f"Missing columns (dashboard will still load): {missing}")

    # Dates like 9/3/2025
    if "EventDate" in df.columns:
        df["EventDate"] = pd.to_datetime(df["EventDate"], errors="coerce").dt.date

    # Times like 9:00AM
    for col in ["StartTime", "EndTime"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%I:%M%p", errors="coerce").dt.time

    # Derived time buckets
    if "StartTime" in df.columns:
        df["StartHour"] = df["StartTime"].apply(lambda t: t.hour if pd.notna(t) and t is not None else None)

    if "EventDate" in df.columns:
        df["DayOfWeek"] = pd.to_datetime(df["EventDate"], errors="coerce").dt.day_name()

    return df

def pie(series: pd.Series, title: str, top_n: int = 12):
    fig, ax = plt.subplots()
    s = series.dropna()
    if s.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        st.pyplot(fig)
        return

    counts = s.value_counts().head(top_n)
    colors = (PALETTE * ((len(counts) // len(PALETTE)) + 1))[: len(counts)]
    ax.pie(counts.values, labels=counts.index, autopct="%1.0f%%", startangle=90, colors=colors)
    ax.set_title(title)
    st.pyplot(fig)

def bar_counts(counts: pd.Series, title: str, xlabel: str = "", ylabel: str = "Reservations"):
    fig, ax = plt.subplots()
    ax.bar(counts.index.astype(str), counts.values, color=OT_BLUE)
    ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=45)
    st.pyplot(fig)

# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.header("Data")
    upload = st.file_uploader("Upload reservations.csv (or Excel)", type=["csv", "xlsx", "xls"])
    st.caption("Tip: If you run this app in a folder with a file named **reservations.csv**, it will auto-load.")

df_raw = load_reservations(upload)
if df_raw is None:
    st.info('Upload your CSV, or place a file named **reservations.csv** next to `app.py`.')
    st.stop()

df = normalize(df_raw)

# Basic sanity check
if "EventId" not in df.columns:
    st.error("This file doesn't look like the reservations export (missing EventId).")
    st.stop()

with st.sidebar:
    st.divider()
    st.header("Filters")

    # Date range
    if "EventDate" in df.columns and df["EventDate"].notna().any():
        min_d = min(df["EventDate"].dropna())
        max_d = max(df["EventDate"].dropna())
        d_start, d_end = st.date_input("Event date range", value=(min_d, max_d))
    else:
        d_start = d_end = None

    def uniq(col):
        if col not in df.columns:
            return []
        return sorted(df[col].dropna().unique().tolist())

    locations = st.multiselect("Location", options=uniq("Location"))
    depts = st.multiselect("Department", options=uniq("Department"))
    statuses = st.multiselect("Status", options=uniq("Status"))
    event_type_names = st.multiselect("EventTypeName", options=uniq("EventTypeName"))

    search_text = st.text_input("Search (Title / Contact / Email)", value="").strip()

# -----------------------------
# Apply filters
# -----------------------------
f = df.copy()

if d_start and d_end and "EventDate" in f.columns:
    f = f[(f["EventDate"].notna()) & (f["EventDate"] >= d_start) & (f["EventDate"] <= d_end)]

if locations and "Location" in f.columns:
    f = f[f["Location"].isin(locations)]

if depts and "Department" in f.columns:
    f = f[f["Department"].isin(depts)]

if statuses and "Status" in f.columns:
    f = f[f["Status"].isin(statuses)]

if event_type_names and "EventTypeName" in f.columns:
    f = f[f["EventTypeName"].isin(event_type_names)]

if search_text:
    mask = False
    for col in ["Title", "ContactName", "ContactEmail"]:
        if col in f.columns:
            mask = mask | f[col].astype(str).str.lower().str.contains(search_text.lower(), na=False)
    f = f[mask]

# -----------------------------
# KPIs
# -----------------------------
st.subheader("Overview")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total reservations", len(f))
m2.metric("Unique locations", f["Location"].nunique() if "Location" in f.columns else 0)
m3.metric("Unique departments", f["Department"].nunique() if "Department" in f.columns else 0)
m4.metric("Active (status)", int((f["Status"].astype(str).str.lower() == "active").sum()) if "Status" in f.columns else 0)

st.divider()

# -----------------------------
# Charts (tabs)
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Distribution", "Time Demand", "Details"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        pie(f["Location"] if "Location" in f.columns else pd.Series(dtype=object),
            "Total Reservations by Location (Pie)")
    with c2:
        pie(f["Department"] if "Department" in f.columns else pd.Series(dtype=object),
            "Total Reservations by Department (Pie)")

    st.subheader("Department Reservations by Location")
    if "Location" in f.columns and "Department" in f.columns and not f.empty:
        pivot = pd.pivot_table(
            f, index="Location", columns="Department", values="EventId",
            aggfunc="count", fill_value=0
        )
        st.bar_chart(pivot)  # Streamlit handles stacked-ish display per column
    else:
        st.info("Need Location + Department data for this chart.")

with tab2:
    st.subheader("Most Reserved Times (Start Hour)")

    # Exclude all-day from time charts (your file has none, but safe)
    time_df = f.copy()
    if "IsAllDayEvent" in time_df.columns:
        time_df = time_df[time_df["IsAllDayEvent"] == False]

    if "StartHour" in time_df.columns and time_df["StartHour"].notna().any():
        hour_counts = time_df["StartHour"].value_counts().sort_index()
        fig, ax = plt.subplots()
        ax.bar(hour_counts.index.astype(int), hour_counts.values, color=OT_BLUE)
        ax.set_title("Reservations by Start Hour")
        ax.set_xlabel("Hour of Day (0–23)")
        ax.set_ylabel("Reservations")
        st.pyplot(fig)
    else:
        st.info("No StartTime data available to chart.")

    st.subheader("Busiest Days of Week")
    if "DayOfWeek" in time_df.columns and time_df["DayOfWeek"].notna().any():
        # Order days Mon..Sun
        order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        day_counts = time_df["DayOfWeek"].value_counts().reindex(order).dropna()
        bar_counts(day_counts, "Reservations by Day of Week", xlabel="Day")
    else:
        st.info("No EventDate data available to chart.")

    st.subheader("Hot Rooms by Time (Location × Start Hour)")
    if "Location" in time_df.columns and "StartHour" in time_df.columns and not time_df.empty:
        heat = pd.pivot_table(
            time_df, index="Location", columns="StartHour", values="EventId",
            aggfunc="count", fill_value=0
        ).sort_index(axis=1)
        st.caption("Counts of reservations by room and start hour.")
        st.dataframe(heat, use_container_width=True)
    else:
        st.info("Need Location + StartTime for this view.")

with tab3:
    st.subheader("Filtered Reservations (Detail)")
    preferred = ["EventDate","StartTime","EndTime","Title","Location","Department","Status",
                 "ContactName","ContactEmail","EventTypeName","EventId"]
    cols = [c for c in preferred if c in f.columns] + [c for c in f.columns if c not in preferred]
    st.dataframe(f[cols].reset_index(drop=True), use_container_width=True, height=520)

    csv_bytes = f[cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered results (CSV)",
        data=csv_bytes,
        file_name="filtered_room_reservations.csv",
        mime="text/csv",
    )
