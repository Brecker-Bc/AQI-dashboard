import streamlit as st
import altair as alt
import pandas as pd

# ===============================
# Page & Theme
# ===============================
st.set_page_config(layout="wide", page_title="US County-Level AQI & Heat")

# Altair white theme
BASE_CONFIG = {
    "background": "white",
    "view": {"stroke": None},
    "axis": {
        "grid": True,
        "gridOpacity": 0.08,
        "tickSize": 3,
        "labelFontSize": 11,
        "titleFontSize": 12
    },
    "legend": {"titleFontSize": 12, "labelFontSize": 11}
}
alt.themes.register('white_bg', lambda: BASE_CONFIG)
alt.themes.enable('white_bg')

AQI_COLOR_CONT = alt.Scale(scheme='redyellowgreen', reverse=True)   # higher/worse -> red
HEAT_COLOR_CONT = alt.Scale(scheme='redyellowgreen', reverse=True)

# ===============================
# Data Loading (cached) + Cleaning
# ===============================
@st.cache_data
def load_and_clean():
    aqi = pd.read_csv('aqi_with_lat_lon.csv')
    heat = pd.read_csv('heat_with_lat_lon.csv')
    combined = pd.read_csv('combined_with_lat_lon_and_state.csv')

    # 1) Standardize headers (strip, remove NBSP)
    for df_ in (aqi, heat, combined):
        df_.columns = df_.columns.str.strip().str.replace('\xa0', ' ', regex=True)

    # 2) Tolerant rename for heat column (fix header mismatches)
    rename_map = {
        'Avg Daily Max Heat Index': 'Avg Daily Max Heat Index (F)',
        'Avg Daily Max Heat Index ( F )': 'Avg Daily Max Heat Index (F)',
        'Average Daily Max Heat Index (F)': 'Avg Daily Max Heat Index (F)'
    }
    combined.rename(
        columns={k: v for k, v in rename_map.items() if k in combined.columns},
        inplace=True
    )

    # 3) Force key columns to numeric
    for col in ["Median AQI", "Max AQI", "Avg Daily Max Heat Index (F)", "longitude", "latitude"]:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors='coerce')

    # 4) Build a clean county-level frame
    expected_cols = ['Median AQI', 'Avg Daily Max Heat Index (F)', 'longitude', 'latitude', 'County_Formatted', 'State_y']
    missing = [c for c in expected_cols if c not in combined.columns]
    if missing:
        st.warning(f"Missing expected columns in 'combined': {missing}")

    combined_clean = combined.copy()
    if all(c in combined_clean.columns for c in expected_cols):
        combined_clean = combined_clean[expected_cols].dropna(subset=['Median AQI', 'Avg Daily Max Heat Index (F)', 'longitude', 'latitude'])
    else:
        combined_clean = combined_clean.assign(**{c: pd.NA for c in expected_cols if c not in combined_clean.columns})
        combined_clean = combined_clean[expected_cols].dropna()

    return aqi, heat, combined, combined_clean

aqi, heat, combined, combined_clean = load_and_clean()

# ===============================
# Regions + Sidebar Filters
# ===============================
REGIONS = {
    "Northeast": {"CT","ME","MA","NH","RI","VT","NJ","NY","PA"},
    "Midwest": {"IL","IN","MI","OH","WI","IA","KS","MN","MO","NE","ND","SD"},
    "South": {"DE","FL","GA","MD","NC","SC","VA","DC","WV","AL","KY","MS","TN","AR","LA","OK","TX"},
    "West": {"AZ","CO","ID","MT","NV","NM","UT","WY","AK","CA","HI","OR","WA"}
}
state2region = {s:r for r,ss in REGIONS.items() for s in ss}
combined_clean["Region"] = combined_clean["State_y"].map(state2region).fillna("Other")

st.sidebar.header("Filters")

region_sel = st.sidebar.multiselect(
    "Region(s)",
    options=list(REGIONS.keys()),
    default=list(REGIONS.keys())
)

state_opts = sorted(combined_clean["State_y"].dropna().unique())
state_sel = st.sidebar.multiselect("State(s) (optional)", options=state_opts)

# Safe ranges (avoid min/max crash)
aqi_series  = combined_clean["Median AQI"].dropna()
heat_series = combined_clean["Avg Daily Max Heat Index (F)"].dropna()

aqi_lo  = float(aqi_series.min()) if not aqi_series.empty else 0.0
aqi_hi  = float(aqi_series.max()) if not aqi_series.empty else 150.0
heat_lo = float(heat_series.min()) if not heat_series.empty else 60.0
heat_hi = float(heat_series.max()) if not heat_series.empty else 120.0

aqi_range = st.sidebar.slider("Median AQI range", 0.0, max(150.0, aqi_hi), (aqi_lo, aqi_hi))
heat_range = st.sidebar.slider("Heat Index (°F) range", float(int(heat_lo)), float(int(max(120, heat_hi))), (heat_lo, heat_hi))

# Apply filters
df = combined_clean[
    combined_clean["Region"].isin(region_sel)
    & combined_clean["Median AQI"].between(aqi_range[0], aqi_range[1])
    & combined_clean["Avg Daily Max Heat Index (F)"].between(heat_range[0], heat_range[1])
]
if state_sel:
    df = df[df["State_y"].isin(state_sel)]

st.sidebar.download_button(
    "Download filtered data (CSV)",
    df.to_csv(index=False),
    "filtered_county_data.csv",
    "text/csv"
)

# ===============================
# Title & Intro
# ===============================
st.title("US County-Level Air Quality and Heat Index Dashboard")

st.markdown("""
### What Do These Metrics Mean?

**AQI (Air Quality Index):** A measure of how polluted the air is. Lower values (green) are better; higher values (red) are worse.

**Heat Index (°F):** How hot it feels when relative humidity is factored in with the actual air temperature. Higher values indicate more extreme heat.

---
""")

# ===============================
# County-Level Overview Maps (All data)
# ===============================
st.subheader("County-Level Overview Maps (All Data)")

aqi_map_all = alt.Chart(combined_clean).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=AQI_COLOR_CONT, title='Median AQI'),
    tooltip=['County_Formatted:N', 'State_y:N', alt.Tooltip('Median AQI:Q', format='.1f')]
).properties(title='Median AQI by County').project(type='albersUsa')

heat_map_all = alt.Chart(combined_clean).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Avg Daily Max Heat Index (F):Q', scale=HEAT_COLOR_CONT, title='Avg Daily Max Heat Index (°F)'),
    tooltip=['County_Formatted:N', 'State_y:N', alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')]
).properties(title='Avg Daily Max Heat Index by County').project(type='albersUsa')

st.altair_chart(alt.vconcat(aqi_map_all, heat_map_all).resolve_scale(color='independent'), use_container_width=True)

st.markdown("ℹ️ **Tip:** Use the sidebar to filter by region/state and numeric ranges. Brush the scatter to filter the linked map below.")

# ===============================
# Map with Brush (Filtered) + Bar summaries
# ===============================
st.subheader("Interactive County Map (Filtered) + Top Extremes")

brush = alt.selection_interval()
state_click = alt.selection_multi(name='StateSelector', fields=['State_y'], bind='legend')

map_with_brush = alt.Chart(df).transform_filter(
    state_click
).transform_filter(
    brush
).mark_circle(size=60).encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=AQI_COLOR_CONT, title='Median AQI'),
    tooltip=[
        'County_Formatted:N', 'State_y:N',
        alt.Tooltip('Median AQI:Q', format='.1f'),
        alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')
    ]
).add_params(brush, state_click).project(type='albersUsa').properties(
    title='Select Counties (brush) and/or highlight by state (legend)'
).interactive()

aqi_max_bar = alt.Chart(df).transform_filter(brush).transform_aggregate(
    max_aqi='max(Median AQI)', groupby=['County_Formatted']
).transform_window(
    rank='rank(max_aqi)', sort=[alt.SortField('max_aqi', order='descending')]
).transform_filter(
    alt.datum.rank == 1
).mark_bar().encode(
    y=alt.Y('County_Formatted:N', title='County', sort='-x'),
    x=alt.X('max_aqi:Q', title='Highest AQI'),
    color=alt.value('darkred'),
    tooltip=[alt.Tooltip('County_Formatted:N'), alt.Tooltip('max_aqi:Q', format='.1f')]
).properties(title='Highest AQI of Selected Counties')

heat_max_bar = alt.Chart(df).transform_filter(brush).transform_aggregate(
    max_heat='max(Avg Daily Max Heat Index (F))', groupby=['County_Formatted']
).transform_window(
    rank='rank(max_heat)', sort=[alt.SortField('max_heat', order='descending')]
).transform_filter(
    alt.datum.rank == 1
).mark_bar().encode(
    y=alt.Y('County_Formatted:N', title='County', sort='-x'),
    x=alt.X('max_heat:Q', title='Highest Heat Index (°F)'),
    color=alt.value('orange'),
    tooltip=[alt.Tooltip('County_Formatted:N'), alt.Tooltip('max_heat:Q', format='.1f')]
).properties(title='Highest Heat Index of Selected Counties')

st.altair_chart(map_with_brush, use_container_width=True)
st.altair_chart(alt.hconcat(aqi_max_bar, heat_max_bar).resolve_scale(x='independent'), use_container_width=True)

# ===============================
# State-Level Comparison (Filtered set, full state list shown)
# ===============================
st.subheader("State-Level Comparison (Filtered)")

all_states = pd.read_csv("https://raw.githubusercontent.com/jasonong/List-of-US-States/master/states.csv")
states_df = all_states.rename(columns={'Abbreviation': 'State_y'})[['State_y']]

reshaped = df[['State_y', 'Median AQI', 'Max AQI']].copy()
reshaped = reshaped.melt(id_vars=['State_y'], value_vars=['Median AQI', 'Max AQI'],
                         var_name='AQI Type', value_name='AQI Value')
reshaped = states_df.merge(reshaped, on='State_y', how='left')

aqi_metric_dropdown = alt.selection_point(
    name='AQI Metric',
    fields=['AQI Type'],
    bind=alt.binding_select(options=['Median AQI', 'Max AQI'], name='Select AQI Type:'),
    value='Median AQI'
)

state_click_bars = alt.selection_multi(name='StateSelectorBars', fields=['State_y'], bind='legend')

avg_aqi_chart = alt.Chart(reshaped).transform_filter(aqi_metric_dropdown).transform_aggregate(
    avg_value='mean(AQI Value)', groupby=['State_y']
).mark_bar().encode(
    y=alt.Y('State_y:N', title='State', sort='-x',
            axis=alt.Axis(labelFontSize=10, labelLimit=1000, labelOverlap=False)),
    x=alt.X('avg_value:Q', title='Average AQI', scale=alt.Scale(domain=[0, 150])),
    color=alt.condition(
        state_click_bars,
        alt.Color('State_y:N', legend=alt.Legend(title="State", columns=1, symbolLimit=100)),
        alt.value('lightgray')
    ),
    tooltip=[alt.Tooltip('State_y:N'), alt.Tooltip('avg_value:Q', format='.1f')]
).add_params(aqi_metric_dropdown, state_click_bars).properties(
    title='Average AQI by State (Filtered)',
    width=600,
    height=800
)

heat_state_df = df[['State_y', 'Avg Daily Max Heat Index (F)']].copy()
heat_state_df = states_df.merge(heat_state_df, on='State_y', how='left')

avg_heat_by_state = alt.Chart(heat_state_df).transform_aggregate(
    avg_heat='mean(Avg Daily Max Heat Index (F))', groupby=['State_y']
).mark_bar().encode(
    y=alt.Y('State_y:N', title='State', sort='-x',
            axis=alt.Axis(labelFontSize=10, labelLimit=1000, labelOverlap=False)),
    x=alt.X('avg_heat:Q', title='Average Heat Index (°F)'),
    color=alt.Color('avg_heat:Q', scale=HEAT_COLOR_CONT, title='Avg Heat Index (°F)'),
    tooltip=[alt.Tooltip('State_y:N'), alt.Tooltip('avg_heat:Q', format='.1f')]
).properties(
    title='Average Daily Max Heat Index by State (Filtered)',
    width=600,
    height=800
)

st.altair_chart(
    alt.vconcat(avg_heat_by_state, avg_aqi_chart).resolve_scale(x='independent', color='independent'),
    use_container_width=True
)

# ===============================
# Top 10 + Pie (Filtered)
# ===============================
st.subheader("Top 10 Counties by Median AQI (Filtered)")
if len(df) > 0:
    top10 = df.nlargest(10, 'Median AQI')[['County_Formatted', 'State_y', 'Median AQI', 'Avg Daily Max Heat Index (F)']]
    st.dataframe(top10)
else:
    st.info("No rows match the current filters.")

st.subheader("AQI Category Composition — Pie (Filtered)")

aqi_category_cols = ['Good Days', 'Moderate Days', 'Unhealthy for Sensitive Groups Days', 'Unhealthy Days']
have_all_cats = all(col in combined.columns for col in aqi_category_cols)

if have_all_cats:
    view_option = st.selectbox(
        "Select view:",
        ["All Counties (Filtered)", "Top 10 Worst Counties (by Median AQI, Filtered)"]
    )

    if view_option == "Top 10 Worst Counties (by Median AQI, Filtered)":
        if len(df) > 0:
            top10_df = df.nlargest(10, 'Median AQI')
            aqi_totals = top10_df[aqi_category_cols].sum().reset_index()
        else:
            aqi_totals = pd.DataFrame({'Category': aqi_category_cols, 'Days': 0})
    else:
        if len(df) > 0:
            aqi_totals = df[aqi_category_cols].sum().reset_index()
        else:
            aqi_totals = pd.DataFrame({'Category': aqi_category_cols, 'Days': 0})

    aqi_totals.columns = ['Category', 'Days']
    aqi_colors = ['#2ca02c', '#1f77b4', '#ff7f0e', '#d62728']  # green, blue, orange, red

    aqi_pie = alt.Chart(aqi_totals).mark_arc().encode(
        theta=alt.Theta(field="Days", type="quantitative"),
        color=alt.Color(
            field="Category",
            type="nominal",
            scale=alt.Scale(domain=aqi_totals['Category'].tolist(), range=aqi_colors),
            legend=alt.Legend(title="AQI Category")
        ),
        tooltip=['Category', alt.Tooltip('Days:Q', format=',')]
    ).properties(
        title=f"Proportion of Days by AQI Category ({view_option})",
        width=500, height=420
    )

    st.altair_chart(aqi_pie, use_container_width=True)
else:
    st.info("AQI category columns not found; skipping pie chart.")
