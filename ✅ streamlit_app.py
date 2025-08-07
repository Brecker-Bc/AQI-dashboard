import streamlit as st
import altair as alt
import pandas as pd

st.set_page_config(layout="wide")
st.title("US County-Level Air Quality and Heat Index Dashboard")

st.markdown("""
### What Do These Metrics Mean?

**AQI (Air Quality Index):** A measure of how polluted the air is. Lower values (green) are better; higher values (red) are worse.

**Heat Index (°F):** How hot it feels when relative humidity is factored in with the actual air temperature. Higher values indicate more extreme heat.

---
""")

aqi = pd.read_csv('aqi_with_lat_lon.csv')
heat = pd.read_csv('heat_with_lat_lon.csv')
combined = pd.read_csv('combined_with_lat_lon_and_state.csv')
combined_clean = combined[['Median AQI', 'Avg Daily Max Heat Index (F)', 'longitude', 'latitude', 'County_Formatted', 'State_y']].dropna()

st.subheader("County-Level Maps")

aqi_map = alt.Chart(combined).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
    tooltip=['County_Formatted', alt.Tooltip('Median AQI:Q', format='.1f')]
).properties(title='Median AQI by County').project(type='albersUsa')

heat_map = alt.Chart(combined).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Avg Daily Max Heat Index (F):Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
    tooltip=['County_Formatted', alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')]
).properties(title='Avg Daily Max Heat Index by County').project(type='albersUsa')

st.altair_chart(alt.vconcat(aqi_map, heat_map).resolve_scale(color='independent'), use_container_width=True)

st.markdown("ℹ️ **Tip:** Select counties on the map or click a legend item to filter data by state.")

brush = alt.selection_interval()
# Updated State multi-selection for comparison
state_click = alt.selection_multi(name='StateSelector', fields=['State_y'], bind='legend')

map_with_brush = alt.Chart(combined_clean).transform_filter(
    state_click
).transform_filter(
    brush
).mark_circle(size=60).encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
    tooltip=[
        'County_Formatted', 'State_y',
        alt.Tooltip('Median AQI:Q', format='.1f'),
        alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')
    ]
).add_params(brush, state_click).project(type='albersUsa').properties(
    title='Select Counties in Multiple States'
).interactive()

aqi_max_bar = alt.Chart(combined_clean).transform_filter(brush).transform_aggregate(
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

heat_max_bar = alt.Chart(combined_clean).transform_filter(brush).transform_aggregate(
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

st.subheader("State-Level Comparison")
st.markdown("ℹ️ **Tip:** Select a two-letter state code in the legend to highlight its bar.")

all_states = pd.read_csv("https://raw.githubusercontent.com/jasonong/List-of-US-States/master/states.csv")  # columns: State, Abbreviation

states_df = all_states.rename(columns={'Abbreviation': 'State_y'})
reshaped = combined[['State_y', 'Median AQI', 'Max AQI']].copy()
reshaped = reshaped.melt(id_vars=['State_y'], value_vars=['Median AQI', 'Max AQI'], var_name='AQI Type', value_name='AQI Value')
reshaped = states_df[['State_y']].merge(reshaped, on='State_y', how='left')  # ensures all states present

aqi_metric_dropdown = alt.selection_point(
    name='AQI Metric',
    fields=['AQI Type'],
    bind=alt.binding_select(options=['Median AQI', 'Max AQI'], name='Select AQI Type:'),
    value='Median AQI'
)

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
    title='Average AQI by State',
    width=600,
    height=800
)

heat_state_df = combined[['State_y', 'Avg Daily Max Heat Index (F)']].copy()
heat_state_df = states_df[['State_y']].merge(heat_state_df, on='State_y', how='left')

avg_heat_by_state = alt.Chart(heat_state_df).transform_aggregate(
    avg_heat='mean(Avg Daily Max Heat Index (F))', groupby=['State_y']
).mark_bar().encode(
    y=alt.Y('State_y:N', title='State', sort='-x',
        axis=alt.Axis(labelFontSize=10, labelLimit=1000, labelOverlap=False)),
    x=alt.X('avg_heat:Q', title='Average Heat Index (°F)'),
    color=alt.Color('avg_heat:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True), title='Avg Heat Index (°F)'),
    tooltip=[alt.Tooltip('State_y:N'), alt.Tooltip('avg_heat:Q', format='.1f')]
).properties(
    title='Average Daily Max Heat Index by State',
    width=600,
    height=800
)

combined_bars = alt.vconcat(avg_heat_by_state, avg_aqi_chart).resolve_scale(x='independent', color='independent')
st.altair_chart(combined_bars, use_container_width=True)

top10 = combined_clean.nlargest(10, 'Median AQI')[['County_Formatted', 'State_y', 'Median AQI', 'Avg Daily Max Heat Index (F)']]
st.subheader("Top 10 Counties by AQI")
st.dataframe(top10)

# --- DROPDOWN TOGGLE ---
view_option = st.selectbox(
    "Select view:",
    ["All Counties", "Top 10 Worst Counties (by Median AQI)"]
)

# Columns for AQI categories
aqi_category_cols = [
    'Good Days', 
    'Moderate Days', 
    'Unhealthy for Sensitive Groups Days', 
    'Unhealthy Days'
]

# Filter data based on selection
if view_option == "Top 10 Worst Counties (by Median AQI)":
    top10_df = combined.nlargest(10, 'Median AQI')
    aqi_totals = top10_df[aqi_category_cols].sum().reset_index()
else:
    aqi_totals = combined[aqi_category_cols].sum().reset_index()

aqi_totals.columns = ['Category', 'Days']

# High-contrast colors
aqi_colors = [
    '#2ca02c',  # Good Days - green
    '#1f77b4',  # Moderate Days - blue
    '#ff7f0e',  # Unhealthy for Sensitive Groups - orange
    '#d62728'   # Unhealthy Days - red
]

# Pie chart
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
    title=f"Proportion of Days by AQI Category ({view_option})"
)

st.altair_chart(aqi_pie, use_container_width=True)
