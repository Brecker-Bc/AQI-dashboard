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

# Consistent color choices
AQI_COLOR_CONT = alt.Scale(scheme='redyellowgreen', reverse=True)  # higher/worse -> red
HEAT_COLOR_CONT = alt.Scale(scheme='redyellowgreen', reverse=True)

# ===============================
# Data Loading (cached)
# ===============================
@st.cache_data
def load_data():
    aqi = pd.read_csv('aqi_with_lat_lon.csv')
    heat = pd.read_csv('heat_with_lat_lon.csv')
    combined = pd.read_csv('combined_with_lat_lon_and_state.csv')
    # Ensure expected cols exist
    needed_cols = {'Median AQI', 'Max AQI', 'Avg Daily Max Heat Index (F)',
                   'longitude', 'latitude', 'County_Formatted', 'State_y'}
    missing = needed_cols - set(combined.columns)
    if missing:
        st.warning(f"Missing expected columns in 'combined' CSV: {missing}")
    return aqi, heat, combined

aqi, heat, combined = load_data()

# ===============================
# Region mapping (US Census-style)
# ===============================
REGIONS = {
    "Northeast": {"CT","ME","MA","NH","RI","VT","NJ","NY","PA"},
    "Midwest": {"IL","IN","MI","OH","WI","IA","KS","MN","MO","NE","ND","SD"},
    "South": {"DE","FL","GA","MD","NC","SC","VA","DC","WV","AL","KY","MS","TN","AR","LA","OK","TX"},
    "West": {"AZ","CO","ID","MT","NV","NM","UT","WY","AK","CA","HI","OR","WA"}
}
state2region = {s:r for r,ss in REGIONS.items() for s in ss}
combined["Region"] = combined["State_y"].map(state2region).fillna("Other")

# A cleaned subset for county-level stuff
combined_clean = combined[['Median AQI', 'Avg Daily Max Heat Index (F)', 'longitude', 'latitude',
                           'County_Formatted', 'State_y', 'Region']].dropna()

# ===============================
# Sidebar Filters
# ===============================
st.sidebar.header("Filters")

region_sel = st.sidebar.multiselect(
    "Region(s)",
    options=list(REGIONS.keys()),
    default=list(REGIONS.keys())
)

state_opts = sorted(combined_clean["State_y"].dropna().unique())
state_sel = st.sidebar.multiselect("State(s) (optional)", options=state_opts)

aqi_min, aqi_max = float(combined_clean["Median AQI"].min()), float(combined_clean["Median AQI"].max())
heat_min, heat_max = float(combined_clean["Avg Daily Max Heat Index (F)"].min()), float(combined_clean["Avg Daily Max Heat Index (F)"].max())

aqi_range = st.sidebar.slider("Median AQI range", min_value=0.0, max_value=max(150.0, aqi_max),
                              value=(aqi_min, aqi_max))
heat_range = st.sidebar.slider("Heat Index (°F) range",
                               min_value=float(int(heat_min)),
                               max_value=float(int(max(120, heat_max))),
                               value=(heat_min, heat_max))

# Apply sidebar filters
df = combined_clean[
    combined_clean["Region"].isin(region_sel)
    & (combined_clean["Median AQI"].between(aqi_range[0], aqi_range[1]))
    & (combined_clean["Avg Daily Max Heat Index (F)"].between(heat_range[0], heat_range[1]))
]
if state_sel:
    df = df[df["State_y"].isin(state_sel)]

# Download button for filtered data
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
# County-Level Maps (All counties, unfiltered) for quick overview
# ===============================
st.subheader("County-Level Overview Maps")

aqi_map_all = alt.Chart(combined_clean).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=AQI_COLOR_CONT, title='Median AQI'),
    tooltip=['County_Formatted:N', 'State_y:N', alt.Tooltip('Median AQI:Q', format='.1f')]
).properties(title='Median AQI by County (All Data)').project(type='albersUsa')

heat_map_all = alt.Chart(combined_clean).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Avg Daily Max Heat Index (F):Q', scale=HEAT_COLOR_CONT, title='Avg Daily Max Heat Index (°F)'),
    tooltip=['County_Formatted:N', 'State_y:N', alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')]
).properties(title='Avg Daily Max Heat Index by County (All Data)').project(type='albersUsa')

st.altair_chart(alt.vconcat(aqi_map_all, heat_map_all).resolve_scale(color='independent'), use_container_width=True)

st.markdown("ℹ️ **Tip:** Use the sidebar to filter by regions, states, and numeric ranges. Use the scatter brush to further subset the map below.")

# ===============================
# Scatter ↔ Map (Linked by brush)
# ===============================
st.subheader("Explore Relationship: AQI vs Heat (Brush to Filter Map)")

brush = alt.selection_interval()

scatter = alt.Chart(df).mark_point(opacity=0.75).encode(
    x=alt.X('Median AQI:Q', title='Median AQI'),
    y=alt.Y('Avg Daily Max Heat Index (F):Q', title='Avg Daily Max Heat Index (°F)'),
    color=alt.Color('Region:N', legend=alt.Legend(title="Region")),
    tooltip=['County_Formatted:N','State_y:N',
             alt.Tooltip('Median AQI:Q', format='.1f'),
             alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')]
).add_params(brush).properties(
    title='AQI vs Heat Index (filtered by sidebar)',
    width=700, height=420
)

trend = scatter.transform_regression('Median AQI','Avg Daily Max Heat Index (F)').mark_line()

linked_map = alt.Chart(df).transform_filter(brush).mark_circle(size=60).encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=AQI_COLOR_CONT, title='Median AQI'),
    tooltip=['County_Formatted:N','State_y:N',
             alt.Tooltip('Median AQI:Q', format='.1f'),
             alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')]
).project('albersUsa').properties(
    title='Counties Matching Brushed Scatter',
    width=700, height=420
)

st.altair_chart((scatter + trend) | linked_map, use_container_width=True)

# ===============================
# Composition by Region (Normalized stack)
# ===============================
st.subheader("AQI Category Composition by Region")

aqi_category_cols = [
    'Good Days', 
    'Moderate Days', 
    'Unhealthy for Sensitive Groups Days', 
    'Unhealthy Days'
]

have_all_cats = all(col in combined.columns for col in aqi_category_cols)
if have_all_cats:
    comp = (combined[combined['County_Formatted'].isin(df['County_Formatted'])]
            .groupby('Region')[aqi_category_cols].sum().reset_index())
    comp_m = comp.melt('Region', var_name='Category', value_name='Days')
    comp_m['pct'] = comp_m.groupby('Region')['Days'].transform(lambda s: s/s.sum())

    stack = alt.Chart(comp_m).mark_bar().encode(
        x=alt.X('pct:Q', axis=alt.Axis(format='%', title='% of Days')),
        y=alt.Y('Region:N', sort='-x', title='Region'),
        color=alt.Color('Category:N', legend=alt.Legend(title="AQI Category")),
        tooltip=['Region','Category', alt.Tooltip('pct:Q', format='.0%')]
    ).properties(title='Proportion of AQI Categories (Filtered Regions/States)', width=900, height=260)

    st.altair_chart(stack, use_container_width=True)
else:
    st.info("AQI category columns not found; skipping composition chart.")

# ===============================
# Boxplots of AQI by Region (distribution view)
# ===============================
st.subheader("Distribution of Median AQI by Region")

box = alt.Chart(df).mark_boxplot(extent='min-max').encode(
    x=alt.X('Region:N', title='Region'),
    y=alt.Y('Median AQI:Q', title='Median AQI'),
    color='Region:N'
).properties(width=900, height=320)

st.altair_chart(box, use_container_width=True)

# ===============================
# Small-multiple regional mini maps
# ===============================
st.subheader("Regional Mini-Maps (Median AQI)")

facet_maps = alt.Chart(df).mark_circle(size=30).encode(
    longitude='longitude:Q', latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=AQI_COLOR_CONT, title='Median AQI'),
    tooltip=['County_Formatted:N','State_y:N',
             alt.Tooltip('Median AQI:Q', format='.1f'),
             alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')]
).project('albersUsa').properties(width=280, height=200).facet(
    facet='Region:N', columns=2, title=None
)
st.altair_chart(facet_maps, use_container_width=True)

# ===============================
# State-Level Comparison (full state list)
# ===============================
st.subheader("State-Level Comparison")

st.markdown("ℹ️ **Tip:** Use the legend to highlight a specific state bar. The averages reflect the **filtered** subset above.")

# Ensure all state abbreviations present in the bars
all_states = pd.read_csv("https://raw.githubusercontent.com/jasonong/List-of-US-States/master/states.csv")  # columns: State, Abbreviation
states_df = all_states.rename(columns={'Abbreviation': 'State_y'})[['State_y']]

# Build reshaped AQI table from filtered df
reshaped = df[['State_y', 'Median AQI', 'Max AQI']].copy()
reshaped = reshaped.melt(id_vars=['State_y'], value_vars=['Median AQI', 'Max AQI'],
                         var_name='AQI Type', value_name='AQI Value')
reshaped = states_df.merge(reshaped, on='State_y', how='left')  # ensures all states present, NaNs allowed

aqi_metric_dropdown = alt.selection_point(
    name='AQI Metric',
    fields=['AQI Type'],
    bind=alt.binding_select(options=['Median AQI', 'Max AQI'], name='Select AQI Type:'),
    value='Median AQI'
)

state_click = alt.selection_multi(name='StateSelector', fields=['State_y'], bind='legend')

avg_aqi_chart = alt.Chart(reshaped).transform_filter(aqi_metric_dropdown).transform_aggregate(
    avg_value='mean(AQI Value)', groupby=['State_y']
).mark_bar().encode(
    y=alt.Y('State_y:N', title='State', sort='-x',
            axis=alt.Axis(labelFontSize=10, labelLimit=1000, labelOverlap=False)),
    x=alt.X('avg_value:Q', title='Average AQI', scale=alt.Scale(domain=[0, 150])),
    color=alt.condition(
        state_click,
        alt.Color('State_y:N', legend=alt.Legend(title="State", columns=1, symbolLimit=100)),
        alt.value('lightgray')
    ),
    tooltip=[alt.Tooltip('State_y:N'), alt.Tooltip('avg_value:Q', format='.1f')]
).add_params(aqi_metric_dropdown, state_click).properties(
    title='Average AQI by State (Filtered)',
    width=600,
    height=800
)

# Heat bars
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

st.altair_chart(alt.vconcat(avg_heat_by_state, avg_aqi_chart).resolve_scale(x='independent', color='independent'),
                use_container_width=True)

# ===============================
# Top 10 & Pie Toggle (uses filtered df)
# ===============================
st.subheader("Top 10 Counties by Median AQI (Filtered)")
if len(df) > 0:
    top10 = df.nlargest(10, 'Median AQI')[['County_Formatted', 'State_y', 'Median AQI', 'Avg Daily Max Heat Index (F)']]
    st.dataframe(top10)
else:
    st.info("No rows match the current filters.")

# Pie toggle view
st.subheader("AQI Category Composition — Pie (All vs Top 10 Worst by Median AQI)")

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
        # all filtered counties
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
