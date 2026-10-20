"""Read and validate exact flooding parameters."""

from lib.generators.common import read_generator_config, validate_attack_params


DEFAULT_CONFIG = {
    "info": {
        "name": "exact",
        "role": "attack",
        "description": "Repeat one complete event within a time window.",
        "selection_params": [],
    },
    "params": {"n_rows": 500, "duration": 600, "attack_start": None},
}


def read_g_config(parameter_overrides=None):
    config = read_generator_config(__file__, DEFAULT_CONFIG, parameter_overrides)
    validate_attack_params(config["params"])
    return config
