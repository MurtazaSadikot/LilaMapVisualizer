MAP_CONFIG = {
    "AmbroseValley": {"scale": 900, "origin_x": -370, "origin_z": -473},
    "GrandRift": {"scale": 581, "origin_x": -290, "origin_z": -290},
    "Lockdown": {"scale": 1000, "origin_x": -500, "origin_z": -500},
}


def world_to_minimap(x, z, map_name):

    config = MAP_CONFIG[map_name]

    u = (x - config["origin_x"]) / config["scale"]
    v = (z - config["origin_z"]) / config["scale"]

    px = u * 1024
    py = (1 - v) * 1024

    return px, py


def convert_coordinates(df):

    px_list = []
    py_list = []

    for _, row in df.iterrows():

        px, py = world_to_minimap(
            row["x"],
            row["z"],
            row["map_id"]
        )

        px_list.append(px)
        py_list.append(py)

    df["px"] = px_list
    df["py"] = py_list

    return df