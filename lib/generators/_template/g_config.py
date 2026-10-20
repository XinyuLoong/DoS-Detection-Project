"""Define this generator's metadata/defaults and validate experiment overrides."""

from lib.generators.common import read_generator_config, validate_attack_params


DEFAULT_CONFIG = {
    "info": {
        # Change this to the copied directory name.
        "name": "_template",
        "role": "attack",
        "description": "TODO describe this generator.",
        # List every parameter influencing select_events, e.g. ["n_rows"].
        "selection_params": [],
    },
    "params": {"n_rows": 100, "duration": 600, "attack_start": None},
}


def read_g_config(parameter_overrides=None):
    config = read_generator_config(__file__, DEFAULT_CONFIG, parameter_overrides)
    validate_attack_params(config["params"])
    # Validate additional type-specific parameters here; raise ValueError on error.
    return config
