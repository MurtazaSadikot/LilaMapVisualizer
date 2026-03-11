import pandas as pd
import pyarrow.parquet as pq
import os


def load_day(folder, day_name):

    frames = []

    for f in os.listdir(folder):

        path = os.path.join(folder, f)

        try:
            table = pq.read_table(path)
            df = table.to_pandas()

            # decode event column
            df["event"] = df["event"].apply(
                lambda x: x.decode("utf-8") if isinstance(x, bytes) else x
            )

            df["date"] = day_name

            frames.append(df)

        except:
            continue

    return pd.concat(frames, ignore_index=True)


def load_all_data(root_folder):

    frames = []

    for day in os.listdir(root_folder):

        folder = os.path.join(root_folder, day)

        if os.path.isdir(folder):

            frames.append(load_day(folder, day))

    df = pd.concat(frames, ignore_index=True)

    # detect bots vs humans
    df["player_type"] = df["user_id"].apply(
        lambda x: "bot" if str(x).isdigit() else "human"
    )

    return df