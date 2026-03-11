import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

from data_loader import load_all_data
from coordinate_mapper import convert_coordinates

st.set_page_config(layout="wide")

st.title("LILA BLACK Player Journey Visualization Tool")

@st.cache_data
def load_data():
    df = load_all_data("data/player_data")
    df = convert_coordinates(df)
    return df

df = load_data()

# Sidebar Filters
st.sidebar.header("Filters")

map_choice = st.sidebar.selectbox(
    "Select Map",
    df["map_id"].unique()
)

filtered_map = df[df["map_id"] == map_choice]

match_choice = st.sidebar.selectbox(
    "Select Match",
    filtered_map["match_id"].unique()
)

filtered = filtered_map[filtered_map["match_id"] == match_choice]

# Load minimap
minimap_path = f"minimaps/{map_choice}_Minimap.png"

if map_choice == "Lockdown":
    minimap_path = "minimaps/Lockdown_Minimap.jpg"

img = Image.open(minimap_path)

st.image(img, width=600)

# Event Filters
st.sidebar.subheader("Events")

show_kills = st.sidebar.checkbox("Kills", True)
show_loot = st.sidebar.checkbox("Loot", True)
show_paths = st.sidebar.checkbox("Movement", True)

event_filter = []

if show_kills:
    event_filter.append("Kill")

if show_loot:
    event_filter.append("Loot")

if show_paths:
    event_filter.append("Position")

filtered = filtered[
    filtered["event"].isin(event_filter)
]

# Timeline
filtered = filtered.sort_values("ts")

time_index = st.slider(
    "Timeline",
    0,
    len(filtered),
    min(500, len(filtered))
)

filtered = filtered.iloc[:time_index]

# Plot
fig = px.scatter(
    filtered,
    x="px",
    y="py",
    color="player_type",
    hover_data=["event"],
    title="Player Events"
)

fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

# Heatmap
st.subheader("Kill Heatmap")

kills = df[df["event"] == "Kill"]

if len(kills) > 0:
    heatmap = px.density_heatmap(
        kills,
        x="px",
        y="py",
        nbinsx=50,
        nbinsy=50
    )

    heatmap.update_yaxes(autorange="reversed")

    st.plotly_chart(heatmap, use_container_width=True)

# Stats
st.subheader("Match Statistics")

col1, col2, col3 = st.columns(3)

col1.metric("Players", filtered["user_id"].nunique())
col2.metric("Kills", len(filtered[filtered["event"] == "Kill"]))
col3.metric("Loot Events", len(filtered[filtered["event"] == "Loot"]))