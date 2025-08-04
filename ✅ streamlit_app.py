import streamlit as st
import altair as alt
import pandas as pd

# Page setup
st.set_page_config(layout="wide")
st.title("US County-Level Air Quality and Heat Index Dashboard")

# Define key terms
st.markdown("""
### What Do These Metrics Mean?

**AQI (Air Quality Index):** A measure of how polluted the air is. Lower values (green) are better; higher values (red) are worse.

**Heat Index (°F):** How hot it feels when relative humidity is factored in with the actual air temperature. Higher values indicate more extreme heat.

---
""")

# Load datasets
aqi = pd.read_csv('aqi_with_lat_lon.csv')
heat = pd.read_csv('heat_with_lat_lon.csv')
combined = pd.read_csv('combined_with_lat_lon_and_state.csv')
combined_clean = combined[['Median AQI', 'Avg Daily Max Heat Index (F)', 'longitude', 'latitude', 'County_Formatted', 'State_y']].dropna()

# Maps side-by-side
st.subheader("County-Level Maps")

aqi_map = alt.Chart(combined).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
    tooltip=[alt.Tooltip('County_Formatted:N'), alt.Tooltip('Median AQI:Q', format='.1f')]
).properties(
    title='Median AQI by County'
).project(type='albersUsa')

heat_map = alt.Chart(combined).mark_circle().encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Avg Daily Max Heat Index (F):Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
    tooltip=[alt.Tooltip('County_Formatted:N'), alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')]
).properties(
    title='Avg Daily Max Heat Index by County'
).project(type='albersUsa')

heatandAQI = alt.vconcat(aqi_map, heat_map).resolve_scale(color='independent')
st.altair_chart(heatandAQI, use_container_width=True)

# Interactive selection
st.markdown("**Tip:** Use the legend or dropdowns to filter by state or AQI metric.")

brush = alt.selection_interval()
state_click = alt.selection_point(name='StateSelector', fields=['State_y'], bind='legend')

map_with_brush = alt.Chart(combined_clean).transform_filter(
    state_click
).transform_filter(
    brush
).mark_circle(size=60).encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
    tooltip=[
        alt.Tooltip('County_Formatted:N'),
        alt.Tooltip('State_y:N'),
        alt.Tooltip('Median AQI:Q', format='.1f'),
        alt.Tooltip('Avg Daily Max Heat Index (F):Q', format='.1f')
    ]
).add_params(brush).project(type='albersUsa').properties(
    title='Select Counties on US Map'
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
    tooltip=[
        alt.Tooltip('County_Formatted:N'),
        alt.Tooltip('max_aqi:Q', format='.1f')
    ]
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
    tooltip=[
        alt.Tooltip('County_Formatted:N'),
        alt.Tooltip('max_heat:Q', format='.1f')
    ]
).properties(title='Highest Heat Index of Selected Counties')

bar_comparison = alt.hconcat(aqi_max_bar, heat_max_bar).resolve_scale(x='independent')
st.altair_chart(map_with_brush, use_container_width=True)
st.altair_chart(bar_comparison, use_container_width=True)

# State-level comparison
st.subheader("State-Level Comparison")

aqi_metric_dropdown = alt.selection_point(
    name='AQI Metric',
    fields=['AQI Type'],
    bind=alt.binding_select(options=['Median AQI', 'Max AQI'], name='Select AQI Type:'),
    value='Median AQI'
)

reshaped = combined.melt(
    id_vars=['State_y'],
    value_vars=['Median AQI', 'Max AQI'],
    var_name='AQI Type',
    value_name='AQI Value'
)

avg_aqi_chart = alt.Chart(reshaped).transform_filter(aqi_metric_dropdown).transform_aggregate(
    avg_value='mean(AQI Value)', groupby=['State_y']
).mark_bar().encode(
    y=alt.Y('State_y:N', title='State', sort='-x'),
    x=alt.X('avg_value:Q', title='Average AQI', scale=alt.Scale(domain=[0, 150])),
    color=alt.condition(state_click, 'State_y:N', alt.value('lightgray')),
    tooltip=[
        alt.Tooltip('State_y:N'),
        alt.Tooltip('avg_value:Q', format='.1f')
    ]
).add_params(aqi_metric_dropdown, state_click).properties(
    title='Average AQI by State',
    width=600,
    height=800
)

avg_heat_by_state = alt.Chart(combined).transform_aggregate(
    avg_heat='mean(Avg Daily Max Heat Index (F))', groupby=['State_y']
).mark_bar().encode(
    y=alt.Y('State_y:N', title='State', sort='-x'),
    x=alt.X('avg_heat:Q', title='Average Heat Index (°F)'),
    color=alt.Color('avg_heat:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True), title='Avg Heat Index (°F)'),
    tooltip=[
        alt.Tooltip('State_y:N'),
        alt.Tooltip('avg_heat:Q', format='.1f')
    ]
).properties(
    title='Average Daily Max Heat Index by State',
    width=600,
    height=800
)

combined_bars = alt.vconcat(avg_heat_by_state, avg_aqi_chart).resolve_scale(
    x='independent', color='independent'
)

st.altair_chart(combined_bars, use_container_width=True)
