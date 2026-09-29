#!/usr/bin/env python3

"""
generate_synthetic.py

Generate synthetic datasets for DoS / DDoS profiling experiments
based on an existing reference dataset.

Supported attack types:
    normal       - randomly sampled normal data only
    exact        - inject repeated identical events in a short time window
    distributed  - inject different events that share several event fields

Example usages:

1. Normal dataset
python generate_synthetic.py \
    -i history_scram-0f.csv \
    -o synthetic_0_normal.csv \
    --normal 10000 \
    --attack-type normal \
    --seed 42

2. Exact flood
python generate_synthetic.py \
    -i history_scram-0f.csv \
    -o synthetic_1_exact.csv \
    --normal 10000 \
    --attack 500 \
    --attack-type exact \
    --duration 600 \
    --seed 42

3. Distributed flood
python generate_synthetic.py \
    -i history_scram-0f.csv \
    -o synthetic_2_distributed.csv \
    --normal 10000 \
    --attack 300 \
    --attack-type distributed \
    --shared-fields 3 \
    --duration 600 \
    --seed 42
"""

import argparse
import itertools
import os
import sys

import numpy as np
import pandas as pd


DEFAULT_TIMESTAMP_COLUMN = "updated"

# Event columns in the current teacher dataset.
# The script will automatically remove timestamp / label columns if needed.
DEFAULT_EVENT_COLUMNS = [
    "scope",
    "source",
    "field",
    "value",
    "signature",
]


# ============================================================
# Utility functions
# ============================================================

def read_dataset(filepath):
    """Read and validate the reference dataset."""

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")

    df = pd.read_csv(filepath)

    if df.empty:
        raise ValueError("Input dataset is empty.")

    return df


def validate_columns(df, timestamp_column, event_columns):
    """Check that required columns exist."""

    missing = [
        col
        for col in event_columns + [timestamp_column]
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    if not pd.api.types.is_numeric_dtype(df[timestamp_column]):
        raise ValueError(
            f"Timestamp column '{timestamp_column}' must be numeric."
        )


def choose_attack_start(
    df,
    timestamp_column,
    duration,
    rng,
    requested_start=None,
):
    """
    Choose an attack window within the timestamp range of the reference data.
    """

    min_time = int(df[timestamp_column].min())
    max_time = int(df[timestamp_column].max())

    if requested_start is not None:
        attack_start = int(requested_start)

        if attack_start < min_time:
            print(
                f"WARNING: attack start {attack_start} is earlier than "
                f"reference data minimum timestamp {min_time}."
            )

        if attack_start + duration > max_time:
            print(
                f"WARNING: attack window extends beyond reference "
                f"data maximum timestamp {max_time}."
            )

        return attack_start

    latest_possible_start = max_time - duration

    if latest_possible_start <= min_time:
        raise ValueError(
            "Reference timestamp range is shorter than attack duration."
        )

    return int(
        rng.integers(
            min_time,
            latest_possible_start + 1,
        )
    )


def generate_attack_timestamps(
    attack_start,
    duration,
    n,
    rng,
):
    """
    Generate random integer timestamps uniformly within an attack window.
    """

    if n <= 0:
        return np.array([], dtype=np.int64)

    return rng.integers(
        attack_start,
        attack_start + duration,
        size=n,
        endpoint=False,
        dtype=np.int64,
    )


# ============================================================
# Normal dataset
# ============================================================

def generate_normal_data(
    df,
    n_normal,
    seed,
):
    """
    Generate normal data by sampling complete rows from the reference
    dataset.

    Sampling complete rows preserves realistic relationships between
    event fields instead of sampling each column independently.
    """

    if n_normal < 0:
        raise ValueError("--normal must be >= 0")

    if n_normal == 0:
        normal = df.iloc[0:0].copy()
    else:
        normal = df.sample(
            n=n_normal,
            replace=True,
            random_state=seed,
        ).copy()

    normal["truth_label"] = 0
    normal["attack_type"] = "normal"

    return normal


# ============================================================
# Exact flood
# ============================================================

def generate_exact_attack(
    df,
    event_columns,
    timestamp_column,
    n_attack,
    duration,
    rng,
    seed,
    attack_start=None,
):
    """
    Generate an exact flood.

    One real event from the reference dataset is selected.
    That identical event is then repeated many times in a short
    timestamp window.
    """

    if n_attack <= 0:
        raise ValueError(
            "--attack must be > 0 when attack-type is 'exact'."
        )

    # Select one complete real event.
    unique_events = (
        df[event_columns]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    base_event = unique_events.sample(
        n=1,
        random_state=seed,
    ).iloc[0]

    # Repeat that exact event.
    attack = pd.DataFrame(
        [base_event.to_dict()] * n_attack
    )

    # Choose attack time window.
    attack_start = choose_attack_start(
        df=df,
        timestamp_column=timestamp_column,
        duration=duration,
        rng=rng,
        requested_start=attack_start,
    )

    attack[timestamp_column] = generate_attack_timestamps(
        attack_start=attack_start,
        duration=duration,
        n=n_attack,
        rng=rng,
    )

    attack["truth_label"] = 1
    attack["attack_type"] = "exact"

    print("\n=== Exact flood ===")
    print(f"Injected attack rows : {n_attack}")
    print(f"Attack duration      : {duration} sec")
    print(f"Attack start         : {attack_start}")
    print(f"Repeated event:")
    for col in event_columns:
        print(f"  {col}: {base_event[col]}")

    return attack


# ============================================================
# Distributed flood helper
# ============================================================

def find_best_shared_group(
    df,
    event_columns,
    shared_fields,
):
    """
    Search all combinations of event columns of size `shared_fields`.

    For each combination, find the group containing the largest number
    of UNIQUE complete events.

    Example:

        shared_fields = 3

    Could discover that:

        scope + source + field

    contains many unique combinations of:

        value + signature

    This group is useful for constructing a distributed flood.
    """

    if shared_fields <= 0:
        raise ValueError("--shared-fields must be >= 1")

    if shared_fields >= len(event_columns):
        raise ValueError(
            "--shared-fields must be smaller than the total number "
            "of event columns."
        )

    unique_events = (
        df[event_columns]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    best = None

    combinations = itertools.combinations(
        event_columns,
        shared_fields,
    )

    for shared_cols_tuple in combinations:

        shared_cols = list(shared_cols_tuple)

        group_sizes = (
            unique_events
            .groupby(
                shared_cols,
                dropna=False,
            )
            .size()
            .sort_values(ascending=False)
        )

        if group_sizes.empty:
            continue

        max_size = int(group_sizes.iloc[0])
        group_key = group_sizes.index[0]

        # When grouping by one column, pandas may return a scalar.
        if shared_fields == 1:
            group_key = (group_key,)
        elif not isinstance(group_key, tuple):
            group_key = tuple(group_key)

        if best is None or max_size > best["size"]:
            best = {
                "shared_columns": shared_cols,
                "group_key": group_key,
                "size": max_size,
            }

    if best is None:
        raise ValueError(
            "Could not find a valid shared-field group."
        )

    return best


def extract_shared_group(
    df,
    event_columns,
    shared_columns,
    group_key,
):
    """
    Extract all unique complete events matching a selected shared group.
    """

    unique_events = (
        df[event_columns]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    mask = pd.Series(
        True,
        index=unique_events.index,
    )

    for col, value in zip(
        shared_columns,
        group_key,
    ):
        if pd.isna(value):
            mask &= unique_events[col].isna()
        else:
            mask &= unique_events[col].eq(value)

    candidates = (
        unique_events.loc[mask]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    return candidates


# ============================================================
# Distributed flood
# ============================================================

def generate_distributed_attack(
    df,
    event_columns,
    timestamp_column,
    n_attack,
    shared_fields,
    duration,
    rng,
    seed,
    attack_start=None,
):
    """
    Generate a distributed flood.

    Attack events share a subset of event fields, but the full events
    remain different.

    Example:

        scope    source    field       value    signature
        hosts    A         userlogin   v1       sig1
        hosts    A         userlogin   v2       sig2
        hosts    A         userlogin   v3       sig3

    Here three fields are shared:

        scope, source, field

    while value and signature vary.
    """

    if n_attack <= 0:
        raise ValueError(
            "--attack must be > 0 when attack-type is 'distributed'."
        )

    best = find_best_shared_group(
        df=df,
        event_columns=event_columns,
        shared_fields=shared_fields,
    )

    shared_columns = best["shared_columns"]
    group_key = best["group_key"]

    candidates = extract_shared_group(
        df=df,
        event_columns=event_columns,
        shared_columns=shared_columns,
        group_key=group_key,
    )

    available = len(candidates)

    print("\n=== Distributed flood candidate group ===")
    print(
        "Shared columns       : "
        + ", ".join(shared_columns)
    )

    for col, value in zip(
        shared_columns,
        group_key,
    ):
        print(f"  {col}: {value}")

    print(
        f"Unique candidate events: {available}"
    )

    # Important:
    # Do not silently sample with replacement because that would create
    # exact duplicate events and make the attack less purely distributed.
    if available < n_attack:
        raise ValueError(
            f"\nRequested {n_attack} distributed attack rows, but the "
            f"largest group sharing {shared_fields} fields contains only "
            f"{available} unique full events.\n\n"
            f"Try one of the following:\n"
            f"  1. reduce --attack to <= {available}\n"
            f"  2. reduce --shared-fields\n"
        )

    attack = candidates.sample(
        n=n_attack,
        replace=False,
        random_state=seed,
    ).copy()

    attack_start = choose_attack_start(
        df=df,
        timestamp_column=timestamp_column,
        duration=duration,
        rng=rng,
        requested_start=attack_start,
    )

    attack[timestamp_column] = generate_attack_timestamps(
        attack_start=attack_start,
        duration=duration,
        n=n_attack,
        rng=rng,
    )

    attack["truth_label"] = 1
    attack["attack_type"] = "distributed"

    print("\n=== Distributed flood ===")
    print(f"Injected attack rows : {n_attack}")
    print(f"Shared fields        : {shared_fields}")
    print(f"Attack duration      : {duration} sec")
    print(f"Attack start         : {attack_start}")

    return attack


# ============================================================
# Combine normal + attack
# ============================================================

def combine_datasets(
    normal,
    attack,
    original_columns,
    seed,
):
    """
    Combine normal and attack rows and shuffle them.

    Original dataset columns are kept in the original order.
    Ground-truth columns are appended at the end.
    """

    combined = pd.concat(
        [normal, attack],
        ignore_index=True,
        sort=False,
    )

    combined = combined.sample(
        frac=1,
        random_state=seed,
    ).reset_index(drop=True)

    output_columns = (
        list(original_columns)
        + ["truth_label", "attack_type"]
    )

    combined = combined[output_columns]

    return combined


# ============================================================
# Summary
# ============================================================

def print_summary(
    synthetic,
    timestamp_column,
    output_file,
):
    """Print basic information about the generated dataset."""

    print("\n========================================")
    print("Synthetic dataset generated")
    print("========================================")

    print(f"Output file       : {output_file}")
    print(f"Total rows        : {len(synthetic)}")

    counts = (
        synthetic["attack_type"]
        .value_counts()
    )

    print("\nRows by type:")
    print(counts.to_string())

    print(
        f"\nTimestamp minimum : "
        f"{int(synthetic[timestamp_column].min())}"
    )

    print(
        f"Timestamp maximum : "
        f"{int(synthetic[timestamp_column].max())}"
    )

    print("\nFirst 5 rows:")
    print(synthetic.head())

    print("========================================")


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic normal / exact flood / "
            "distributed flood datasets."
        )
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Reference CSV dataset.",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output synthetic CSV file.",
    )

    parser.add_argument(
        "--normal",
        type=int,
        default=10000,
        help="Number of normal rows. Default: 10000",
    )

    parser.add_argument(
        "--attack",
        type=int,
        default=0,
        help="Number of injected attack rows. Default: 0",
    )

    parser.add_argument(
        "--attack-type",
        choices=[
            "normal",
            "exact",
            "distributed",
        ],
        default="normal",
        help=(
            "Attack type: normal, exact, or distributed. "
            "Default: normal"
        ),
    )

    parser.add_argument(
        "--shared-fields",
        type=int,
        default=3,
        help=(
            "Number of event fields shared by distributed "
            "attack events. Default: 3"
        ),
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=600,
        help=(
            "Attack window duration in seconds. "
            "Default: 600"
        ),
    )

    parser.add_argument(
        "--attack-start",
        type=int,
        default=None,
        help=(
            "Optional attack start epoch timestamp. "
            "If omitted, a random valid start time is chosen."
        ),
    )

    parser.add_argument(
        "--timestamp-column",
        default=DEFAULT_TIMESTAMP_COLUMN,
        help=(
            f"Timestamp column name. "
            f"Default: {DEFAULT_TIMESTAMP_COLUMN}"
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed. Default: 42",
    )

    args = parser.parse_args()

    # -------------------------------
    # Validate CLI arguments
    # -------------------------------

    if args.normal < 0:
        parser.error("--normal must be >= 0")

    if args.attack < 0:
        parser.error("--attack must be >= 0")

    if args.duration <= 0:
        parser.error("--duration must be > 0")

    if (
        args.attack_type != "normal"
        and args.attack <= 0
    ):
        parser.error(
            "--attack must be > 0 when injecting an attack."
        )

    # -------------------------------
    # Random generator
    # -------------------------------

    rng = np.random.default_rng(args.seed)

    # -------------------------------
    # Load reference dataset
    # -------------------------------

    df = read_dataset(args.input)

    event_columns = [
        col
        for col in DEFAULT_EVENT_COLUMNS
        if col in df.columns
    ]

    validate_columns(
        df=df,
        timestamp_column=args.timestamp_column,
        event_columns=event_columns,
    )

    print("========================================")
    print("Reference dataset")
    print("========================================")
    print(f"Input             : {args.input}")
    print(f"Rows              : {len(df)}")
    print(
        "Event columns     : "
        + ", ".join(event_columns)
    )
    print(
        f"Timestamp column  : "
        f"{args.timestamp_column}"
    )

    # -------------------------------
    # Generate normal data
    # -------------------------------

    normal = generate_normal_data(
        df=df,
        n_normal=args.normal,
        seed=args.seed,
    )

    # -------------------------------
    # Generate attack data
    # -------------------------------

    if args.attack_type == "normal":

        # Empty attack dataframe.
        attack = normal.iloc[0:0].copy()

    elif args.attack_type == "exact":

        attack = generate_exact_attack(
            df=df,
            event_columns=event_columns,
            timestamp_column=args.timestamp_column,
            n_attack=args.attack,
            duration=args.duration,
            rng=rng,
            seed=args.seed + 1,
            attack_start=args.attack_start,
        )

    elif args.attack_type == "distributed":

        attack = generate_distributed_attack(
            df=df,
            event_columns=event_columns,
            timestamp_column=args.timestamp_column,
            n_attack=args.attack,
            shared_fields=args.shared_fields,
            duration=args.duration,
            rng=rng,
            seed=args.seed + 1,
            attack_start=args.attack_start,
        )

    else:
        raise ValueError(
            f"Unknown attack type: {args.attack_type}"
        )

    # -------------------------------
    # Combine
    # -------------------------------

    synthetic = combine_datasets(
        normal=normal,
        attack=attack,
        original_columns=df.columns,
        seed=args.seed,
    )

    # Ensure timestamps remain integer.
    synthetic[args.timestamp_column] = (
        synthetic[args.timestamp_column]
        .astype(np.int64)
    )

    # -------------------------------
    # Write output
    # -------------------------------

    output_dir = os.path.dirname(
        os.path.abspath(args.output)
    )

    os.makedirs(
        output_dir,
        exist_ok=True,
    )

    synthetic.to_csv(
        args.output,
        index=False,
    )

    # -------------------------------
    # Summary
    # -------------------------------

    print_summary(
        synthetic=synthetic,
        timestamp_column=args.timestamp_column,
        output_file=args.output,
    )


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:
        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)