"""Distributed flooding reuses a complete set of distinct events per group."""

import itertools

import pandas as pd

from lib.generators.common import attack_timestamps
from .g_config import read_g_config


def get_info():
    return read_g_config()["info"]


def find_best_shared_group(events, event_columns, shared_fields):
    if shared_fields >= len(event_columns):
        raise ValueError("shared_fields must be smaller than the number of event columns")
    best = None
    for combination in itertools.combinations(event_columns, shared_fields):
        columns = list(combination)
        sizes = events.groupby(columns, dropna=False).size().sort_values(ascending=False)
        if sizes.empty:
            continue
        key = sizes.index[0]
        if shared_fields == 1:
            key = (key,)
        if best is None or int(sizes.iloc[0]) > best["size"]:
            best = {"shared_columns": columns, "group_key": key, "size": int(sizes.iloc[0])}
    if best is None:
        raise ValueError("No unused events remain for a distributed event_group")
    return best


def extract_shared_group(events, shared_columns, group_key):
    mask = pd.Series(True, index=events.index)
    for column, value in zip(shared_columns, group_key):
        mask &= events[column].isna() if pd.isna(value) else events[column].eq(value)
    return events.loc[mask].reset_index(drop=True)


def select_events(context, params):
    candidates = context["available_events"]
    best = find_best_shared_group(candidates, context["event_columns"], params["shared_fields"])
    candidates = extract_shared_group(candidates, best["shared_columns"], best["group_key"])
    if len(candidates) < params["n_rows"]:
        raise ValueError(
            f"Requested {params['n_rows']} distinct events, but the largest remaining "
            f"shared-field group contains {len(candidates)}; reduce n_rows or shared_fields"
        )
    events = candidates.sample(
        n=params["n_rows"], replace=False, random_state=context["rng"]
    ).reset_index(drop=True)
    return {"events": events, "metadata": {
        "shared_columns": best["shared_columns"],
        "shared_values": dict(zip(best["shared_columns"], best["group_key"])),
    }}


def run(context, params, selected_events):
    data = selected_events["events"].copy()
    if len(data) != params["n_rows"]:
        raise ValueError("Same-group distributed attacks must have the same n_rows")
    timestamps, metadata, warnings = attack_timestamps(context, params)
    data[context["timestamp_column"]] = timestamps
    return {"data": data, "metadata": metadata, "warnings": warnings}
