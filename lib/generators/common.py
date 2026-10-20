"""Shared configuration, random streams, event checks, and time utilities."""

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


DEFAULT_EVENT_COLUMNS = ["scope", "source", "field", "value", "signature"]
LABEL_COLUMNS = ["truth_label", "attack_type", "attack_id"]
GENERATION_CONFIG_DIR = Path(__file__).resolve().parents[2] / "etc" / "generation_config"


def load_yaml(path):
    try:
        with open(path, encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in {path}: {error}") from error
    if not isinstance(config, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return config


def require_int(value, name, minimum=None):
    if type(value) is not int or (minimum is not None and value < minimum):
        suffix = f" >= {minimum}" if minimum is not None else ""
        raise ValueError(f"{name} must be an integer{suffix}")


def read_generator_config(module_file, defaults, overrides=None):
    """Copy module-defined defaults, merge experiment parameters, and validate."""
    directory = Path(module_file).parent
    config = copy.deepcopy(defaults)
    info, params = config.get("info"), config.get("params")
    if not isinstance(info, dict) or not isinstance(params, dict):
        raise ValueError("Generator configuration requires info and params mappings")
    if info.get("name") != directory.name:
        raise ValueError("Generator name must match its directory")
    if info.get("role") not in ("background", "attack"):
        raise ValueError("Generator role must be background or attack")
    if not isinstance(info.get("description"), str):
        raise ValueError("Generator description must be a string")
    selection_params = info.get("selection_params")
    if (not isinstance(selection_params, list)
            or not all(isinstance(key, str) and key in params for key in selection_params)):
        raise ValueError("info.selection_params must list parameters affecting event selection")
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("Parameter overrides must be a mapping")
        unknown = set(overrides) - set(params)
        if unknown:
            raise ValueError(f"Unknown parameters for {directory.name}: {sorted(unknown, key=str)}")
        params.update(copy.deepcopy(overrides))
    return config


def validate_attack_params(params):
    require_int(params["n_rows"], "n_rows", 1)
    require_int(params["duration"], "duration", 1)
    if params["attack_start"] is not None:
        require_int(params["attack_start"], "attack_start")


def make_rng(seed, *identity):
    """Stable named streams; independent of Python hash randomization or list order."""
    payload = json.dumps([seed, *identity], ensure_ascii=True).encode("utf-8")
    entropy = int.from_bytes(hashlib.sha256(payload).digest(), "big")
    return np.random.default_rng(entropy)


def event_index(df, columns):
    return pd.MultiIndex.from_frame(df[columns])


def validate_reference(df, event_columns, timestamp_column):
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Reference dataset must be a non-empty DataFrame")
    if not df.columns.is_unique:
        raise ValueError("Reference column names must be unique")
    if (not isinstance(event_columns, list) or not event_columns
            or not all(isinstance(col, str) and col for col in event_columns)
            or len(set(event_columns)) != len(event_columns)):
        raise ValueError("event_columns must be a non-empty list of unique column names")
    if not isinstance(timestamp_column, str) or not timestamp_column:
        raise ValueError("timestamp_column must be a column name")
    if timestamp_column in event_columns or set(event_columns) & set(LABEL_COLUMNS):
        raise ValueError("Event columns must exclude the timestamp and reserved label columns")
    if set(df.columns) & set(LABEL_COLUMNS) or timestamp_column in LABEL_COLUMNS:
        raise ValueError(f"Reference data must not contain reserved labels: {LABEL_COLUMNS}")
    missing = set(event_columns + [timestamp_column]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing reference columns: {sorted(missing)}")
    times = df[timestamp_column]
    if (not pd.api.types.is_numeric_dtype(times)
            or pd.api.types.is_bool_dtype(times)
            or pd.api.types.is_complex_dtype(times)
            or times.isna().any()
            or not np.isfinite(times).all()
            or not (times == np.floor(times)).all()):
        raise ValueError("Reference timestamps must be finite integer-valued numbers")
    if times.min() < -(2**63) or int(times.max()) >= 2**63 - 1:
        raise ValueError("Reference timestamps exceed the supported int64 range")


def attack_timestamps(context, params):
    """Choose a window and sample timestamps in [start, start + duration)."""
    times = context["reference_df"][context["timestamp_column"]]
    minimum, maximum = int(times.min()), int(times.max())
    duration = params["duration"]
    start = params["attack_start"]
    warnings = []
    if start is None:
        latest = maximum - duration
        if latest < minimum:
            raise ValueError("Reference timestamp range is shorter than attack duration")
        start = int(context["rng"].integers(minimum, latest + 1))
    elif start < minimum or start + duration > maximum:
        warnings.append("Requested attack window extends beyond the reference timestamp range")
    if start < -(2**63) or start + duration > 2**63 - 1:
        raise ValueError("Attack window exceeds the supported int64 range")
    timestamps = context["rng"].integers(start, start + duration, size=params["n_rows"])
    return timestamps, {"attack_start": start, "attack_end_exclusive": start + duration}, warnings


def json_safe(value):
    """Convert metadata to strict JSON values, including missing event fields."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or pd.isna(value):
        return None
    if isinstance(value, float) and not np.isfinite(value):
        raise ValueError("Metadata must not contain infinite values")
    if isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Metadata value is not JSON-compatible: {type(value).__name__}")
