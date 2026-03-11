import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import numpy as np

from data_loader import load_all_data
from coordinate_mapper import convert_coordinates

st.set_page_config(layout="wide")

st.title("LILA Black Player Journey Visualization")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data
def load_data():

    df = load_all_data("data/player_data")

    df = convert_coordinates(df)

    df["ts"] = pd.to_datetime(df["ts"])

    return df


df = load_data()

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Filters")

map_choice = st.sidebar.selectbox(
    "Map",
    sorted(df["map_id"].unique()),
    key="map_filter"
)

map_df = df[df["map_id"] == map_choice]

date_choice = st.sidebar.selectbox(
    "Date",
    sorted(map_df["date"].unique()),
    key="date_filter"
)

date_df = map_df[map_df["date"] == date_choice]

match_choice = st.sidebar.selectbox(
    "Match",
    sorted(date_df["match_id"].unique()),
    key="match_filter"
)

match_df = date_df[date_df["match_id"] == match_choice]

# --------------------------------------------------
# PLAYER FILTER
# --------------------------------------------------

st.sidebar.subheader("Player Filter")

player_mode = st.sidebar.radio(
    "Show Players",
    [
        "All Players",
        "Only Humans",
        "Only Bots",
        "Select Specific Players"
    ],
    key="player_filter"
)

if player_mode == "Only Humans":

    match_df = match_df[match_df["player_type"] == "human"]

elif player_mode == "Only Bots":

    match_df = match_df[match_df["player_type"] == "bot"]

elif player_mode == "Select Specific Players":

    players = st.sidebar.multiselect(
        "Select Players",
        sorted(match_df["user_id"].unique()),
        key="player_select"
    )

    if players:
        match_df = match_df[
            match_df["user_id"].isin(players)
        ]

# --------------------------------------------------
# TIMELINE
# --------------------------------------------------

match_df = match_df.sort_values("ts")

event_count = len(match_df)

if event_count == 0:
    st.warning("No events available for the selected filters.")
    st.stop()

timeline_index = st.slider(
    "Match Timeline",
    min_value=1,
    max_value=event_count,
    value=min(1000, event_count),
    key="timeline_slider"
)

match_df = match_df.iloc[:timeline_index]

# --------------------------------------------------
# NORMALIZE TIME
# --------------------------------------------------

if len(match_df) > 1:

    ts_min = match_df["ts"].min()
    ts_max = match_df["ts"].max()

    if ts_max != ts_min:
        match_df["time_norm"] = (
            (match_df["ts"] - ts_min) /
            (ts_max - ts_min)
        )
    else:
        match_df["time_norm"] = 1

else:
    match_df["time_norm"] = 1

# --------------------------------------------------
# LOAD MINIMAP
# --------------------------------------------------

map_path = f"minimaps/{map_choice}_Minimap.png"

if map_choice == "Lockdown":
    map_path = "minimaps/Lockdown_Minimap.jpg"

minimap = Image.open(map_path)

# --------------------------------------------------
# PLAYER COLORS
# --------------------------------------------------

players = sorted(match_df["user_id"].unique())

palette = px.colors.qualitative.Alphabet

player_colors = {
    player: palette[i % len(palette)]
    for i, player in enumerate(players)
}

# --------------------------------------------------
# EVENT COLORS
# --------------------------------------------------

event_colors = {
    "Kill": "red",
    "Killed": "black",
    "BotKill": "orange",
    "BotKilled": "brown",
    "Loot": "yellow",
    "KilledByStorm": "purple"
}

# --------------------------------------------------
# MAP VISUALIZATION
# --------------------------------------------------

st.subheader("Match Map")

fig = go.Figure()

for player_id, player_df in match_df.groupby("user_id"):

    player_df = player_df.sort_values("ts")

    xs = player_df["px"].values
    ys = player_df["py"].values
    times = player_df["time_norm"].values

    color = player_colors[player_id]

    for i in range(1, len(xs)):

        fig.add_trace(
            go.Scatter(
                x=[xs[i-1], xs[i]],
                y=[ys[i-1], ys[i]],
                mode="lines",
                line=dict(color=color, width=3),
                opacity=float(times[i]),
                showlegend=False
            )
        )

    fig.add_trace(
        go.Scatter(
            x=[xs[-1]],
            y=[ys[-1]],
            mode="markers",
            marker=dict(
                size=10,
                color=color,
                line=dict(width=2, color="black")
            ),
            name=str(player_id)
        )
    )

# Event markers

events_df = match_df[
    match_df["event"].isin(event_colors.keys())
]

for event_type, event_df in events_df.groupby("event"):

    fig.add_trace(
        go.Scatter(
            x=event_df["px"],
            y=event_df["py"],
            mode="markers",
            marker=dict(
                size=8,
                color=event_colors[event_type]
            ),
            name=event_type
        )
    )

# Map background

fig.update_layout(
    width=900,
    height=900,
    xaxis=dict(range=[0,1024], showgrid=False),
    yaxis=dict(range=[1024,0], showgrid=False, scaleanchor="x"),
    images=[
        dict(
            source=minimap,
            xref="x",
            yref="y",
            x=0,
            y=0,
            sizex=1024,
            sizey=1024,
            sizing="stretch",
            layer="below"
        )
    ]
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# HEATMAP OVERLAY
# --------------------------------------------------

st.subheader("Map Activity Heatmap")

show_heatmap = st.checkbox("Show Heatmap Overlay", True)

heatmap_type = st.selectbox(
    "Activity Type",
    ["Player Traffic", "Kill Hotspots", "Death Hotspots"],
    key="heatmap_selector"
)

if heatmap_type == "Kill Hotspots":

    heat_df = date_df[date_df["event"] == "Kill"]

elif heatmap_type == "Death Hotspots":

    heat_df = date_df[
        date_df["event"].isin(
            ["Killed","BotKilled","KilledByStorm"]
        )
    ]

else:

    heat_df = date_df[
        date_df["event"].isin(["Position","BotPosition"])
    ].sample(frac=0.1, random_state=1)


if show_heatmap and len(heat_df) > 10:

    heat_fig = go.Figure()

    heat_fig.add_trace(
        go.Histogram2d(
            x=heat_df["px"],
            y=heat_df["py"],
            nbinsx=40,
            nbinsy=40,
            colorscale="YlOrRd",
            opacity=0.6,
            showscale=False
        )
    )

    heat_fig.update_layout(
        width=900,
        height=900,
        xaxis=dict(range=[0,1024], showgrid=False),
        yaxis=dict(range=[1024,0], showgrid=False, scaleanchor="x"),
        images=[
            dict(
                source=minimap,
                xref="x",
                yref="y",
                x=0,
                y=0,
                sizex=1024,
                sizey=1024,
                sizing="stretch",
                layer="below"
            )
        ]
    )

    st.plotly_chart(heat_fig, use_container_width=True)

    st.caption(
        "Red zones indicate the highest player activity density."
    )

else:

    st.info("Not enough data for heatmap.")

# --------------------------------------------------
# MATCH STATISTICS
# --------------------------------------------------

st.subheader("Match Statistics")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Players Visible",
    match_df["user_id"].nunique()
)

col2.metric(
    "Kills",
    len(match_df[match_df["event"] == "Kill"])
)

col3.metric(
    "Loot Events",
    len(match_df[match_df["event"] == "Loot"])
)