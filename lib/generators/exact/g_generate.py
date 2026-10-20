"""Exact flooding uses a target selected once per event group."""

from lib.generators.common import attack_timestamps
from .g_config import read_g_config


def get_info():
    return read_g_config()["info"]


def select_events(context, params):
    candidates = context["available_events"]
    if candidates.empty:
        raise ValueError("No unused event remains for this exact event_group")
    events = candidates.sample(n=1, random_state=context["rng"]).reset_index(drop=True)
    return {"events": events, "metadata": {}}


def run(context, params, selected_events):
    if len(selected_events["events"]) != 1:
        raise ValueError("Exact flooding requires one selected event")
    data = selected_events["events"].iloc[[0] * params["n_rows"]].reset_index(drop=True)
    timestamps, metadata, warnings = attack_timestamps(context, params)
    data[context["timestamp_column"]] = timestamps
    return {"data": data, "metadata": metadata, "warnings": warnings}
