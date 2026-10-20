"""Background sampling preserves original rows, including timestamps."""

from .g_config import read_g_config


def get_info():
    return read_g_config()["info"]


def select_events(context, params):
    return {"events": context["available_events"].copy(), "metadata": {}}


def run(context, params, selected_events):
    data = context["reference_df"].sample(
        n=params["n_rows"], replace=True, random_state=context["rng"]
    ).reset_index(drop=True)
    return {"data": data, "metadata": {"sampling": "with_replacement"}, "warnings": []}
