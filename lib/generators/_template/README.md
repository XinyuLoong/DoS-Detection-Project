# Adding a generator

Copy this directory to `lib/generators/<name>/`, using a lowercase Python name
such as `burst`. Set `DEFAULT_CONFIG["info"]["name"]` in the copied `g_config.py`
to the generator directory name. This module defines metadata and defaults;
no type-specific YAML is needed. Files under `etc/generation_config/` describe
complete experiments. Its `_template.yaml` is an experiment template, distinct
from this generator-code template.
The runner loads `g_generate.py` and `g_config.py` dynamically; no registry or
central type-specific branch needs editing.

1. Describe the generator and define parameter defaults in `DEFAULT_CONFIG`
   in the new generator's `g_config.py`.
2. Validate all parameters in `read_g_config()`. Raise `ValueError`, not `sys.exit`.
3. Implement `select_events(context, params)`. Return a mapping with `events`
   (a nonempty DataFrame of unique full events) and `metadata` (a dictionary).
   Use only `context['available_events']`, with columns in `event_columns` order.
4. List every parameter influencing selection in `info.selection_params`.
   Instances sharing a group must use equal values for these parameters.
   Use defaults for these parameters that permit `get_info()` to read the config.
5. Implement `run(context, params, selected_events)`, returning `data`, `metadata`,
   and a list of string `warnings`. Output exactly `n_rows` rows. Every selected
   event must appear, and no other complete event may appear. Add timestamps;
   the runner adds labels. Extra reference columns may be supplied; otherwise
   they are filled with missing values and recorded in warnings.
6. Add an instance with `id`, `type`, `event_group`, and optional `params` to an
   experiment YAML's `attacks` list under `etc/generation_config/`.
   Exercise same-group reuse, different-group
   disjointness, insufficient candidates, and reproducibility for the new type.

`context` contains `reference_df`, `event_columns`, `timestamp_column`,
`available_events`, and a NumPy Generator `rng`. Selection and generation have
separate random streams. Use `rng` rather than global randomness. The runner
passes copies so one instance cannot mutate another's inputs.

Metadata must be JSON-compatible; NumPy scalar values and missing event values
are normalized by the runner. Metadata should describe the actual event choice,
window, or other generated characteristics. Do not print or save files here.

The current contract adds rows made from reference events. Types that invent
new event values, delete rows, or modify existing background records need an
explicit future interface extension. Background generators use role
`background`, must implement the same entry points, and are not assigned attack
event groups. See `normal` for a background implementation.
