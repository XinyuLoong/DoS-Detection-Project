"""Copy into a named directory to add a generator without changing the runner."""

from .g_config import read_g_config


def get_info():
    return read_g_config()["info"]


def select_events(context, params):
    """Return unique full events chosen ONLY from context['available_events']."""
    # Use context['rng'] for reproducible randomness. The runner excludes events
    # already assigned to other groups of this type. Do not select from the full
    # reference_df, which could reintroduce those events.
    # Return {"events": selected_dataframe, "metadata": {...}}.
    raise NotImplementedError("Implement event selection for this generator")


def run(context, params, selected_events):
    """Generate n_rows using exactly the event set in selected_events['events']."""
    # Return {"data": dataframe, "metadata": {...}, "warnings": []}.
    # Required columns: context['event_columns'] and context['timestamp_column'].
    # Use context['rng']; do not add truth_label, attack_type, or attack_id.
    # Shared time helper: lib.generators.common.attack_timestamps(context, params).
    # No printing, file writes, or mutation of input data or configuration.
    raise NotImplementedError("Implement generation for this generator")
