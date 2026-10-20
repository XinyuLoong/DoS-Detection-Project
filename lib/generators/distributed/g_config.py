"""Read and validate distributed flooding parameters."""

from lib.generators.common import read_generator_config, require_int, validate_attack_params


DEFAULT_CONFIG = {
    "info": {
        "name": "distributed",
        "role": "attack",
        "description": "Select distinct events sharing field values and concentrate them in time.",
        # Same-group instances reuse the complete set and must agree on these values.
        "selection_params": ["n_rows", "shared_fields"],
    },
    "params": {"n_rows": 100, "shared_fields": 3, "duration": 600, "attack_start": None},
}


def read_g_config(parameter_overrides=None):
    config = read_generator_config(__file__, DEFAULT_CONFIG, parameter_overrides)
    validate_attack_params(config["params"])
    require_int(config["params"]["shared_fields"], "shared_fields", 1)
    return config
