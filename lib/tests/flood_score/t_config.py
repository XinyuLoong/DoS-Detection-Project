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


def read_t_config():
   """Read and validate this profile test's configuration."""
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

   return config
