import streamlit as st
import pandas as pd
import plotly.express as px


# -----------------------------
# Oregon Tech Colors (Official)
# -----------------------------
OT_BLUE = "#003767"
OT_GOLD = "#FFD24F"
WHITE = "#FFFFFF"
GRAY_BG = "#F6F8FB"
GRAY_TEXT = "#475569"

# A clean extended palette (blue/gold + muted supporting colors)
OIT_PALETTE = [
    OT_BLUE, OT_GOLD,
    "#154574",  # secondary blue
    "#DA0000",  # secondary red
    "#334155",  # slate
    "#64748B",  # gray
    "#0F766E",  # teal
    "#7C3AED",  # purple
    "#C2410C",  # orange
    "#16A34A",  # green
]

st.set_page_config(page_title="Room Reservations Dashboard", layout="wide")

# -----------------------------
# CSS Styling
# -----------------------------
st.markdown(
    f"""
    <style>
      .stApp {{
        background: {GRAY_BG};
      }}
      .block-container {{
        padding-top: 1.2rem;
      }}
      h1, h2, h3 {{
        color: {OT_BLUE};
      }}
      section[data-testid="stSidebar"] {{
        background: {WHITE};
        border-right: 4px solid {OT_GOLD};
      }}
      div[data-testid="stMetric"] {{
        background: {WHITE};
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
# Load Reservations
# -----------------------------
def load_reservations(upload):
    if upload is None:
        try:
            return pd.read_csv("reservations.csv")
        except Exception:
            return None
    return pd.read_csv(upload)

df_raw = load_reservations(st.sidebar.file_uploader("Upload reservations.csv", type=["csv"]))

if df_raw is None:
    st.info("Upload your file OR place a file named **reservations.csv** next to app.py.")
    st.stop()

df = df_raw.copy()
df.columns = [c.strip() for c in df.columns]

# Parse Date + Time
df["EventDate"] = pd.to_datetime(df["EventDate"], errors="coerce")
df["StartTime_dt"] = pd.to_datetime(df["StartTime"], format="%I:%M%p", errors="coerce")
df["StartHour"] = df["StartTime_dt"].dt.hour
df["DayOfWeek"] = df["EventDate"].dt.day_name()

# Parse EndTime + build datetime ranges for timeline (Gantt)
df["EndTime_dt"] = pd.to_datetime(df.get("EndTime"), format="%I:%M%p", errors="coerce")

# Combine EventDate + time into full datetimes
df["StartDT"] = df["EventDate"].dt.normalize() + pd.to_timedelta(df["StartTime_dt"].dt.hour.fillna(0), unit="h") \
               + pd.to_timedelta(df["StartTime_dt"].dt.minute.fillna(0), unit="m")

df["EndDT"] = df["EventDate"].dt.normalize() + pd.to_timedelta(df["EndTime_dt"].dt.hour.fillna(0), unit="h") \
             + pd.to_timedelta(df["EndTime_dt"].dt.minute.fillna(0), unit="m")

# If an event ends after midnight (end < start), bump EndDT by 1 day
mask_cross_midnight = df["StartDT"].notna() & df["EndDT"].notna() & (df["EndDT"] < df["StartDT"])
df.loc[mask_cross_midnight, "EndDT"] = df.loc[mask_cross_midnight, "EndDT"] + pd.Timedelta(days=1)


# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("Filters")

min_date = df["EventDate"].min()
max_date = df["EventDate"].max()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date.date(), max_date.date())
)

d_start, d_end = date_range

filtered = df[
    (df["EventDate"].dt.date >= d_start) &
    (df["EventDate"].dt.date <= d_end)
].copy()

loc_options = sorted(filtered["Location"].dropna().unique())
dept_options = sorted(filtered["Department"].dropna().unique())

loc_filter = st.sidebar.multiselect("Location", options=loc_options)
dept_filter = st.sidebar.multiselect("Department", options=dept_options)

if loc_filter:
    filtered = filtered[filtered["Location"].isin(loc_filter)]
if dept_filter:
    filtered = filtered[filtered["Department"].isin(dept_filter)]

# -----------------------------
# KPIs
# -----------------------------
st.subheader("Overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Reservations", len(filtered))
c2.metric("Locations", filtered["Location"].nunique())
c3.metric("Departments", filtered["Department"].nunique())
c4.metric("Avg / Day", round(len(filtered) / max(1, filtered["EventDate"].dt.date.nunique()), 1))

st.divider()

# -----------------------------
# Helper: Top N + "Other"
# -----------------------------
def top_n_with_other(series: pd.Series, top_n: int = 8) -> pd.DataFrame:
    vc = series.dropna().astype(str).value_counts()
    top = vc.head(top_n)
    other = vc.iloc[top_n:].sum()

    out = top.reset_index()
    out.columns = ["Category", "Count"]

    if other > 0:
        out = pd.concat([out, pd.DataFrame([{"Category": "Other", "Count": int(other)}])], ignore_index=True)

    return out

# -----------------------------
# Charts
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Distribution", "Time Demand", "Details"])

with tab1:
    st.subheader("Distribution")

    left, right = st.columns(2)

    with left:
        loc_counts = top_n_with_other(filtered["Location"], top_n=8)
        fig_loc = px.pie(
            loc_counts,
            names="Category",
            values="Count",
            title="Total Reservations by Location",
            color_discrete_sequence=[OT_BLUE, OT_GOLD, "#154574", "#64748B", "#DA0000", "#0F766E", "#334155", "#C2410C", "#7C3AED"],
            hole=0.35
        )
        fig_loc.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_loc, use_container_width=True)

    with right:
        dept_counts = top_n_with_other(filtered["Department"], top_n=8)
        fig_dept = px.pie(
            dept_counts,
            names="Category",
            values="Count",
            title="Total Reservations by Department",
            color_discrete_sequence=[OT_BLUE, OT_GOLD, "#154574", "#64748B", "#DA0000", "#0F766E", "#334155", "#C2410C", "#7C3AED"],
            hole=0.35
        )
        fig_dept.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_dept, use_container_width=True)

    st.subheader("Reservations by Location (Stacked by Department)")

    # Instead of 25 rainbow categories, we limit to top depts
    top_departments = filtered["Department"].value_counts().head(8).index.tolist()
    compact = filtered.copy()
    compact["DeptGroup"] = compact["Department"].apply(lambda x: x if x in top_departments else "Other")

    stacked = (
        compact.groupby(["Location", "DeptGroup"])
        .size()
        .reset_index(name="Reservations")
    )

    fig_stack = px.bar(
        stacked,
        x="Location",
        y="Reservations",
        color="DeptGroup",
        title="Department Reservations by Location (Top 8 + Other)",
        barmode="stack",
        color_discrete_sequence=OIT_PALETTE
    )
    fig_stack.update_layout(
        legend_title_text="Department",
        xaxis_title="Location",
        yaxis_title="Reservations",
    )
    st.plotly_chart(fig_stack, use_container_width=True)

with tab2:
    st.subheader("Time Demand")

    # Reservations by hour
    hour_counts = (
        filtered.dropna(subset=["StartHour"])
        .groupby("StartHour")
        .size()
        .reset_index(name="Reservations")
        .sort_values("StartHour")
    )

    fig_hours = px.bar(
        hour_counts,
        x="StartHour",
        y="Reservations",
        title="Most Reserved Start Times (by Hour)",
        color_discrete_sequence=[OT_BLUE]
    )
    fig_hours.update_layout(
        xaxis_title="Hour of Day (0–23)",
        yaxis_title="Reservations"
    )
    st.plotly_chart(fig_hours, use_container_width=True)

    # Day of week
    order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    dow_counts = (
        filtered.dropna(subset=["DayOfWeek"])
        .groupby("DayOfWeek")
        .size()
        .reindex(order)
        .reset_index(name="Reservations")
    )

    fig_dow = px.bar(
        dow_counts,
        x="DayOfWeek",
        y="Reservations",
        title="Reservations by Day of Week",
        color_discrete_sequence=[OT_GOLD]
    )
    fig_dow.update_layout(
        xaxis_title="Day",
        yaxis_title="Reservations"
    )
    st.plotly_chart(fig_dow, use_container_width=True)

    # Heatmap: Location x StartHour
    st.subheader("Room Demand Heatmap (Location × Hour)")

    heat = (
        filtered.dropna(subset=["Location", "StartHour"])
        .groupby(["Location", "StartHour"])
        .size()
        .reset_index(name="Count")
    )

    fig_heat = px.density_heatmap(
        heat,
        x="StartHour",
        y="Location",
        z="Count",
        color_continuous_scale=["#EAF2FF", OT_BLUE],
        title="Heatmap of Reservations"
    )
    fig_heat.update_layout(
        xaxis_title="Start Hour",
        yaxis_title="Location"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # -----------------------------
    # Gantt Chart (Timeline)
    # -----------------------------
    # -----------------------------
    # Gantt Chart (Timeline)
    # -----------------------------
    st.subheader("Reservations Gantt (Time × Room)")

    # Build a base dataset for the Gantt picker:
    # - respects Location/Department filters
    # - DOES NOT depend on the dashboard date range, so you can pick past days
    gantt_base = df.copy()

    if loc_filter:
        gantt_base = gantt_base[gantt_base["Location"].isin(loc_filter)]
    if dept_filter:
        gantt_base = gantt_base[gantt_base["Department"].isin(dept_filter)]

    gantt_days = (
        gantt_base["EventDate"]
        .dropna()
        .dt.date
        .sort_values()
        .unique()
    )

    if len(gantt_days) == 0:
        st.info("No dates available for the current Location/Department filters.")
    else:
        min_gantt_day = gantt_days.min()
        max_gantt_day = gantt_days.max()

        # Calendar dropdown picker (single day)
        today = datetime.date.today()

        # Default = today if it's in range, otherwise clamp to min/max
        default_day = today
        if today < min_gantt_day:
            default_day = min_gantt_day
        elif today > max_gantt_day:
            default_day = max_gantt_day
        
        picked_day = st.date_input(
            "Pick a single day for the Gantt chart",
            value=default_day,
            min_value=min_gantt_day,
            max_value=max_gantt_day,
            key="gantt_day_picker"
        )

# If user picks a day with no events, snap to nearest available day
if picked_day not in set(gantt_days):
    gantt_days_sorted = sorted(gantt_days)
    picked_day = min(gantt_days_sorted, key=lambda d: abs(d - picked_day))
    st.caption(f"No events on the selected day; showing nearest day with events: {picked_day}")

        # If user picks a day that has no events, snap to nearest available day
        if picked_day not in set(gantt_days):
            gantt_days_sorted = sorted(gantt_days)
            # nearest date by absolute distance
            picked_day = min(gantt_days_sorted, key=lambda d: abs(d - picked_day))
            st.caption(f"No events on the selected day; showing nearest day with events: {picked_day}")

        gantt_src = gantt_base[
            gantt_base["EventDate"].dt.date == picked_day
        ].dropna(subset=["Location", "StartDT", "EndDT"]).copy()

        if gantt_src.empty:
            st.info("No reservations with valid Start/End times for that day.")
        else:
            color_field_options = [c for c in ["Department", "Status"] if c in gantt_src.columns]
            color_field = st.selectbox(
                "Color bars by",
                options=color_field_options or ["(none)"],
                key="gantt_color"
            )

            fig_gantt = px.timeline(
                gantt_src.sort_values(["Location", "StartDT"]),
                x_start="StartDT",
                x_end="EndDT",
                y="Location",
                color=None if color_field == "(none)" else color_field,
                hover_data=["Title", "Department", "Status", "StartDT", "EndDT"],
                title=f"Reservation Timeline by Room — {picked_day}"
            )

            fig_gantt.update_yaxes(autorange="reversed", title="Room / Location")
            fig_gantt.update_xaxes(title="Time")
            fig_gantt.update_layout(margin=dict(l=10, r=10, t=50, b=10))

            st.plotly_chart(fig_gantt, use_container_width=True)




with tab3:
    st.subheader("Filtered Reservation Records")

    show_cols = [
        "EventDate", "StartTime", "EndTime", "Title", "Location",
        "Department", "Status", "ContactName", "ContactEmail"
    ]
    show_cols = [c for c in show_cols if c in filtered.columns]

    st.dataframe(filtered[show_cols].sort_values("EventDate"), use_container_width=True, height=520)

    st.download_button(
        "Download Filtered CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_reservations.csv",
        mime="text/csv"
    )
