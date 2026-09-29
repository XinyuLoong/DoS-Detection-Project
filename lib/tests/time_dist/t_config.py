import math
import os
import sys

import yaml


TPATH = os.path.dirname(os.path.abspath(__file__))
default_config_file = os.path.join(TPATH, "etc", "t_config.yaml")


def load_config(filepath):
   """Load configuration from a YAML file."""
   try:
      with open(filepath, "r", encoding="utf-8") as file:
         return yaml.safe_load(file)
   except (OSError, yaml.YAMLError) as error:
      print(f"Error reading configuration file '{filepath}': {error}",
            file=sys.stderr)
      sys.exit(1)


def read_t_config(parameter_overrides=None):
   """Read YAML defaults, merge runtime overrides, and validate the result."""
   config = load_config(default_config_file)
   if not isinstance(config, dict) or not isinstance(config.get("info"), dict):
      print(f"Configuration '{default_config_file}' must contain an info mapping.",
            file=sys.stderr)
      sys.exit(1)

   info = config["info"]
   for field, field_type in [
      ("name", str),
      ("level", str),
      ("description", str),
      ("dependencies", list),
      ("supports_iteration", bool)
   ]:
      if not isinstance(info.get(field), field_type):
         print((f"Configuration '{default_config_file}': info.{field} "
                f"must be a {field_type.__name__}."), file=sys.stderr)
         sys.exit(1)

   if not all(isinstance(name, str) for name in info["dependencies"]):
      print(f"Configuration '{default_config_file}': dependencies must be strings.",
            file=sys.stderr)
      sys.exit(1)

   if info["name"] != os.path.basename(TPATH):
      print(f"Profile test name mismatch in configuration '{default_config_file}'.",
            file=sys.stderr)
      sys.exit(1)

   params = config.get("params")
   if not isinstance(params, dict):
      print(f"Configuration '{default_config_file}' must contain a params mapping.",
            file=sys.stderr)
      sys.exit(1)

   if parameter_overrides is not None:
      if not isinstance(parameter_overrides, dict):
         raise ValueError("Parameter overrides must be a mapping")
      unknown = set(parameter_overrides) - set(params)
      if unknown:
         raise ValueError(f"Unknown parameters for {info['name']}: {unknown}")
      params.update(parameter_overrides)

   value = params.get("td_anom_cutoff_score")
   if not (type(value) in (int, float) and value >= 0 and
           (type(value) is int or math.isfinite(value))):
      print((f"Configuration '{default_config_file}': params.td_anom_cutoff_score "
             "must be a finite non-negative number."), file=sys.stderr)
      sys.exit(1)

   value = params.get("time_bin")
   if not (type(value) is int and value > 0):
      print((f"Configuration '{default_config_file}': params.time_bin "
             "must be a positive integer (seconds)."), file=sys.stderr)
      sys.exit(1)

   return config
