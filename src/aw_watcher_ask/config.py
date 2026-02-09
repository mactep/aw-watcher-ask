# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT

"""Configuration file handling for aw-watcher-ask."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from aw_watcher_ask.models import DialogType

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


class ConfigError(Exception):
    """Configuration file related errors."""

    pass


def get_default_config_path() -> Path:
    """Returns the default configuration file path.

    Following XDG Base Directory specification:
    - Uses $XDG_CONFIG_HOME if set
    - Falls back to ~/.config if not set

    Returns:
        Path to ~/.config/activitywatch/aw-watcher-ask/config.toml
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_dir = Path(xdg_config_home)
    else:
        config_dir = Path.home() / ".config"

    return config_dir / "activitywatch" / "aw-watcher-ask" / "config.toml"


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads and validates the TOML configuration file.

    Args:
        config_path: Path to config file. If None, uses default path.

    Returns:
        Dictionary containing validated configuration.

    Raises:
        ConfigError: If config file doesn't exist or is invalid.
    """
    if config_path:
        path = Path(config_path)
    else:
        path = get_default_config_path()

    if not path.exists():
        raise ConfigError(
            f"Config file not found at {path}\n\n"
            f"Create it with:\n"
            f"  mkdir -p {path.parent}\n"
            f"  cat > {path} << 'EOF'\n"
            f"[question]\n"
            f"id = \"happiness.level\"\n"
            f"type = \"question\"\n"
            f"title = \"My happiness level\"\n"
            f"text = \"Are you feeling happy right now?\"\n"
            f"schedule = \"0 */1 * * * 0\"\n"
            f"timeout = 120\n"
            f"EOF\n\n"
            f"Or use: aw-watcher-ask --config /path/to/config.toml run"
        )

    if tomllib is None:
        raise ConfigError(
            "No TOML library available. Install tomli for Python < 3.11 "
            "or use Python 3.11+ (has built-in tomllib)"
        )

    try:
        with path.open("rb") as f:
            config_data = tomllib.load(f)
    except Exception as e:
        raise ConfigError(f"Failed to parse TOML config file: {e}")

    return _validate_config(config_data)


def _validate_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates configuration data and returns normalized version.

    Args:
        config_data: Raw configuration dictionary.

    Returns:
        Validated configuration with all required fields.

    Raises:
        ConfigError: If required fields are missing or invalid.
    """
    if "question" not in config_data:
        raise ConfigError("Missing required [question] section in config")

    question_config = config_data["question"]
    required_fields = ["id", "type"]
    for field in required_fields:
        if field not in question_config:
            raise ConfigError(f"Missing required field 'question.{field}' in config")

    question_id = question_config["id"]
    question_type_str = question_config["type"]

    try:
        question_type = DialogType(question_type_str)
    except ValueError:
        valid_types = [t.value for t in DialogType]
        raise ConfigError(
            f"Invalid question type '{question_type_str}'. "
            f"Must be one of: {', '.join(valid_types)}"
        )

    result = {
        "question_id": question_id,
        "question_type": question_type,
    }

    optional_fields = {
        "title": None,
        "text": None,
        "schedule": "R * * * *",
        "timeout": 60,
        "until": "2100-12-31T23:59:59",
        "testing": False,
    }

    for field, default_value in optional_fields.items():
        if field in question_config:
            result[field] = question_config[field]
        else:
            result[field] = default_value

    if "until" in result and isinstance(result["until"], str):
        try:
            result["until"] = datetime.fromisoformat(result["until"])
        except ValueError as e:
            raise ConfigError(f"Invalid datetime format for 'until': {e}")

    zenity_config = config_data.get("zenity", {})
    scale_fields = ["min-value", "max-value", "value"]
    for field in scale_fields:
        if field in question_config:
            zenity_config[field] = question_config[field]

    result["zenity_options"] = zenity_config

    return result
