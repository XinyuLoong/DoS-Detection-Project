"""Read and validate background sampling parameters."""

from lib.generators.common import read_generator_config, require_int


DEFAULT_CONFIG = {
    "info": {
        "name": "normal",
        "role": "background",
        "description": "Sample complete reference rows with replacement.",
        "selection_params": [],
    },
    "params": {"n_rows": 10000},
}


def read_g_config(parameter_overrides=None):
    config = read_generator_config(__file__, DEFAULT_CONFIG, parameter_overrides)
    require_int(config["params"]["n_rows"], "n_rows", 0)
    return config
