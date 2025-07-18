import streamlit as st
import altair as alt
import pandas as pd

# Page setup
st.set_page_config(layout="wide")
st.title("US County-Level Air Quality and Heat Index Dashboard")

# Load data
combined = pd.read_csv('combined_with_lat_lon_and_state.csv')
combined_clean = combined[['Median AQI', 'Max AQI', 'Avg Daily Max Heat Index (F)', 'longitude', 'latitude', 'County_Formatted', 'State_y']].dropna()

# State-level aggregation

# Ensure these are numeric (coerce errors to NaN)
combined_clean['Median AQI'] = pd.to_numeric(combined_clean['Median AQI'], errors='coerce')
combined_clean['Avg Daily Max Heat Index (F)'] = pd.to_numeric(combined_clean['Avg Daily Max Heat Index (F)'], errors='coerce')

# Drop rows with NaN in those key columns
combined_clean = combined_clean.dropna(subset=['Median AQI', 'Avg Daily Max Heat Index (F)'])

state_avg = combined_clean.groupby('State_y').agg({
    'Median AQI': 'mean',
    'Avg Daily Max Heat Index (F)': 'mean'
}).reset_index()

# Selection: click a state
state_click = alt.selection_point(fields=["State_y"], bind="legend")

# US state-level AQI map
state_map = alt.Chart(combined_clean).mark_circle(size=60).encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    color=alt.Color('Median AQI:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
    tooltip=['State_y', 'Median AQI'],
    opacity=alt.condition(state_click, alt.value(1), alt.value(0.2))
).add_params(
    state_click
).properties(
    title="Click a State to View County-Level Data"
).project(type="albersUsa")

st.altair_chart(state_map, use_container_width=True)

# Filter based on state click
selected_state = state_click.get("State_y") if state_click.get("State_y") else None

if selected_state:
    filtered_df = combined_clean[combined_clean["State_y"] == selected_state]
    st.subheader(f"County-Level Data for {selected_state}")
    st.write(f"Counties found: {len(filtered_df)}")
    st.dataframe(filtered_df.head())

    # County Map
    map_with_filter = alt.Chart(filtered_df).mark_circle(size=60).encode(
        longitude='longitude:Q',
        latitude='latitude:Q',
        color=alt.Color('Median AQI:Q', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
        tooltip=['County_Formatted', 'Median AQI', 'Avg Daily Max Heat Index (F)']
    ).properties(title='County Map').project(type='albersUsa')

    # AQI Bar Chart (Top 5)
    aqi_max_bar = alt.Chart(filtered_df).transform_aggregate(
        max_aqi='max(Median AQI)',
        groupby=['County_Formatted']
    ).transform_window(
        rank='rank(max_aqi)',
        sort=[alt.SortField('max_aqi', order='descending')]
    ).transform_filter(
        alt.datum.rank <= 5
    ).mark_bar().encode(
        x=alt.X('County_Formatted:N', sort='-y', title='County'),
        y=alt.Y('max_aqi:Q', title='Max AQI'),
        color=alt.value('darkred'),
        tooltip=['County_Formatted:N', 'max_aqi:Q']
    ).properties(title='Top 5 Counties by AQI')

    # Heat Bar Chart (Top 5)
    heat_max_bar = alt.Chart(filtered_df).transform_aggregate(
        max_heat='max(Avg Daily Max Heat Index (F))',
        groupby=['County_Formatted']
    ).transform_window(
        rank='rank(max_heat)',
        sort=[alt.SortField('max_heat', order='descending')]
    ).transform_filter(
        alt.datum.rank <= 5
    ).mark_bar().encode(
        x=alt.X('County_Formatted:N', sort='-y', title='County'),
        y=alt.Y('max_heat:Q', title='Max Heat Index (°F)'),
        color=alt.value('orange'),
        tooltip=['County_Formatted:N', 'max_heat:Q']
    ).properties(title='Top 5 Counties by Heat Index')

    bar_charts = alt.hconcat(aqi_max_bar, heat_max_bar).resolve_scale(y='independent')
    full_display = alt.vconcat(map_with_filter, bar_charts)

    st.altair_chart(full_display, use_container_width=True)

else:
    st.info("Click a state above to see county-level charts and data.")
