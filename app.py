import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
    ]
)

if player_mode == "Only Humans":

    match_df = match_df[
        match_df["player_type"] == "human"
    ]

elif player_mode == "Only Bots":

    match_df = match_df[
        match_df["player_type"] == "bot"
    ]

elif player_mode == "Select Specific Players":

    players = st.sidebar.multiselect(
        "Select Players",
        sorted(match_df["user_id"].unique())
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
    value=min(1000, event_count)
)

match_df = match_df.iloc[:timeline_index]

# --------------------------------------------------
# SAFE TIME NORMALIZATION
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
# CREATE FIGURE
# --------------------------------------------------

fig = go.Figure()

# --------------------------------------------------
# MOVEMENT TRAILS (FADE OVER TIME)
# --------------------------------------------------

for player_id, player_df in match_df.groupby("user_id"):

    player_df = player_df.sort_values("ts")

    xs = player_df["px"].values
    ys = player_df["py"].values

    times = player_df.get(
        "time_norm",
        pd.Series([1]*len(player_df))
    ).values

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

    # current position
    fig.add_trace(
        go.Scatter(
            x=[xs[-1]],
            y=[ys[-1]],
            mode="markers",
            marker=dict(
                size=10,
                color=color,
                line=dict(width=2,color="black")
            ),
            name=str(player_id)
        )
    )

# --------------------------------------------------
# EVENT MARKERS
# --------------------------------------------------

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

# --------------------------------------------------
# COMBAT INTERACTION LINES
# --------------------------------------------------

kills = match_df[
    match_df["event"].isin(["Kill","BotKill"])
]

deaths = match_df[
    match_df["event"].isin(["Killed","BotKilled"])
]

pair_count = min(len(kills), len(deaths))

for i in range(pair_count):

    fig.add_trace(
        go.Scatter(
            x=[kills.iloc[i]["px"], deaths.iloc[i]["px"]],
            y=[kills.iloc[i]["py"], deaths.iloc[i]["py"]],
            mode="lines",
            line=dict(color="red", width=1, dash="dot"),
            opacity=0.6,
            showlegend=False
        )
    )

# --------------------------------------------------
# ADD MINIMAP BACKGROUND
# --------------------------------------------------

fig.update_layout(
    width=900,
    height=900,
    xaxis=dict(
        range=[0,1024],
        showgrid=False,
        zeroline=False
    ),
    yaxis=dict(
        range=[1024,0],
        showgrid=False,
        zeroline=False,
        scaleanchor="x"
    ),
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
# HEATMAP ANALYSIS
# --------------------------------------------------

st.subheader("Heatmap Analysis")

heatmap_type = st.selectbox(
    "Heatmap Type",
    ["Kill Zones","Death Zones","High Traffic"]
)

if heatmap_type == "Kill Zones":

    heat_df = df[df["event"]=="Kill"]

elif heatmap_type == "Death Zones":

    heat_df = df[df["event"].isin(
        ["Killed","BotKilled","KilledByStorm"]
    )]

else:

    heat_df = df[df["event"].isin(
        ["Position","BotPosition"]
    )]

heatmap = go.Figure(
    data=go.Histogram2d(
        x=heat_df["px"],
        y=heat_df["py"],
        nbinsx=50,
        nbinsy=50
    )
)

heatmap.update_layout(
    xaxis=dict(range=[0,1024]),
    yaxis=dict(range=[1024,0])
)

st.plotly_chart(heatmap, use_container_width=True)

# --------------------------------------------------
# MATCH STATS
# --------------------------------------------------

st.subheader("Match Statistics")

col1,col2,col3 = st.columns(3)

col1.metric(
    "Players Visible",
    match_df["user_id"].nunique()
)

col2.metric(
    "Kills",
    len(match_df[match_df["event"]=="Kill"])
)

col3.metric(
    "Loot Events",
    len(match_df[match_df["event"]=="Loot"])
)