import os
import yaml

_config_cache = None


def load_config():
    """Load configuration from config/config.yaml."""
    global _config_cache
    if _config_cache is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_path = os.path.join(root_dir, "config", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def get_config():
    """Get cached configuration."""
    return load_config()