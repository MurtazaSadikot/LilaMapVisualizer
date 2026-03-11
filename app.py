import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

from data_loader import load_all_data
from coordinate_mapper import convert_coordinates

st.set_page_config(layout="wide")

st.title("LILA BLACK Player Journey Visualization Tool")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data
def load_data():

    df = load_all_data("data/player_data")

    df = convert_coordinates(df)

    df["ts"] = pd.to_datetime(df["ts"])
    df["date"] = df["ts"].dt.date

    return df


df = load_data()

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Filters")

map_choice = st.sidebar.selectbox(
    "Map",
    sorted(df["map_id"].unique())
)

map_df = df[df["map_id"] == map_choice]

date_choice = st.sidebar.selectbox(
    "Date",
    sorted(map_df["date"].unique())
)

date_df = map_df[map_df["date"] == date_choice]

match_choice = st.sidebar.selectbox(
    "Match",
    sorted(date_df["match_id"].unique())
)

match_df = date_df[date_df["match_id"] == match_choice]

# --------------------------------------------------
# TIMELINE
# --------------------------------------------------

match_df = match_df.sort_values("ts")

timeline_index = st.slider(
    "Match Timeline",
    0,
    len(match_df),
    min(1000, len(match_df))
)

match_df = match_df.iloc[:timeline_index]

# Normalize timestamps for fading trails
match_df["time_norm"] = (
    (match_df["ts"] - match_df["ts"].min()) /
    (match_df["ts"].max() - match_df["ts"].min())
)

# --------------------------------------------------
# LOAD MINIMAP
# --------------------------------------------------

map_path = f"minimaps/{map_choice}_Minimap.png"

if map_choice == "Lockdown":
    map_path = "minimaps/Lockdown_Minimap.jpg"

minimap = Image.open(map_path)

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
# PLOT MAP
# --------------------------------------------------

fig = go.Figure()

# Draw movement trails with fading
for player_id, player_df in match_df.groupby("user_id"):

    player_df = player_df.sort_values("ts")

    xs = player_df["px"].values
    ys = player_df["py"].values
    times = player_df["time_norm"].values

    player_type = player_df["player_type"].iloc[0]

    color = "blue" if player_type == "human" else "orange"

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

    # Current position marker
    fig.add_trace(
        go.Scatter(
            x=[xs[-1]],
            y=[ys[-1]],
            mode="markers",
            marker=dict(
                size=10,
                color="white",
                line=dict(width=2, color="black")
            ),
            showlegend=False
        )
    )

# --------------------------------------------------
# EVENT MARKERS
# --------------------------------------------------

events_df = match_df[match_df["event"].isin(event_colors.keys())]

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

# --------------------------------------------------
# MINIMAP BACKGROUND
# --------------------------------------------------

fig.update_layout(
    images=[
        dict(
            source=minimap,
            xref="x",
            yref="y",
            x=0,
            y=1024,
            sizex=1024,
            sizey=1024,
            sizing="stretch",
            layer="below"
        )
    ],
    width=900,
    height=900
)

fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# HEATMAPS
# --------------------------------------------------

st.subheader("Heatmap Analysis")

heatmap_type = st.selectbox(
    "Heatmap Type",
    ["Kill Zones", "Death Zones", "High Traffic"]
)

if heatmap_type == "Kill Zones":

    heat_df = df[df["event"] == "Kill"]

elif heatmap_type == "Death Zones":

    heat_df = df[df["event"].isin(
        ["Killed", "BotKilled", "KilledByStorm"]
    )]

else:

    heat_df = df[df["event"].isin(
        ["Position", "BotPosition"]
    )]

heatmap = go.Figure(
    data=go.Histogram2d(
        x=heat_df["px"],
        y=heat_df["py"],
        nbinsx=50,
        nbinsy=50
    )
)

heatmap.update_yaxes(autorange="reversed")

st.plotly_chart(heatmap, use_container_width=True)

# --------------------------------------------------
# MATCH STATS
# --------------------------------------------------

st.subheader("Match Statistics")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Players",
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