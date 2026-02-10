# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT

"""Configuration file handling for aw-watcher-ask."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aw_watcher_ask.models import DialogType, FieldType, Question, QuestionGroup

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
    if "question_groups" in config_data:
        groups = _validate_question_groups(config_data)
        result = {
            "question_groups": groups,
            "has_question_groups": True,
            "testing": config_data.get("testing", False),
        }
        
        if "question" in config_data:
            single_group = _validate_single_question_as_group(config_data)
            groups.append(single_group)
        
        return result
    elif "question" in config_data:
        return _validate_single_question(config_data)
    else:
        raise ConfigError("Missing config: need [question] or [[question_groups]]")


def _validate_question_groups(config_data: Dict[str, Any]) -> List[QuestionGroup]:
    """Validates question_groups array and returns QuestionGroup objects.

    Args:
        config_data: Raw configuration dictionary with question_groups key.

    Returns:
        List of validated QuestionGroup objects.

    Raises:
        ConfigError: If question_groups are invalid.
    """
    groups_data = config_data.get("question_groups", [])
    
    if not groups_data:
        raise ConfigError("question_groups array is empty")

    groups = []
    
    for i, group_data in enumerate(groups_data):
        group_id = group_data.get("id")
        if not group_id:
            raise ConfigError(f"question_groups[{i}]: missing required field 'id'")
        
        title = group_data.get("title")
        if not title:
            raise ConfigError(f"question_groups[{i}]: missing required field 'title'")
        
        text = group_data.get("text")
        schedule = group_data.get("schedule", "R * * * *")
        timeout = group_data.get("timeout", 60)
        
        until = group_data.get("until")
        if until and isinstance(until, str):
            try:
                until = datetime.fromisoformat(until)
            except ValueError as e:
                raise ConfigError(f"question_groups[{i}]: invalid datetime format for 'until': {e}")
        
        questions_data = group_data.get("questions", [])
        if not questions_data:
            raise ConfigError(f"question_groups[{i}]: missing required 'questions' array")
        
        questions = []
        for j, q_data in enumerate(questions_data):
            q_id = q_data.get("id")
            if not q_id:
                raise ConfigError(f"question_groups[{i}].questions[{j}]: missing required field 'id'")
            
            field_type = q_data.get("field_type", "entry")
            try:
                FieldType(field_type)
            except ValueError:
                valid_types = [t.value for t in FieldType]
                raise ConfigError(
                    f"question_groups[{i}].questions[{j}]: invalid field_type '{field_type}'. "
                    f"Must be one of: {', '.join(valid_types)}"
                )
            
            label = q_data.get("label")
            if not label:
                raise ConfigError(f"question_groups[{i}].questions[{j}]: missing required field 'label'")
            
            values = q_data.get("values")
            if field_type == "combo" and not values:
                raise ConfigError(
                    f"question_groups[{i}].questions[{j}]: "
                    f"field_type 'combo' requires 'values' array"
                )
            
            reason = q_data.get("reason", False)
            
            min_value = q_data.get("min_value")
            max_value = q_data.get("max_value")
            
            if field_type == "combo" and (min_value is None or max_value is None) and values:
                try:
                    numeric_values = [int(v) for v in values if str(v).strip()]
                    if numeric_values:
                        if min_value is None:
                            min_value = min(numeric_values)
                        if max_value is None:
                            max_value = max(numeric_values)
                except ValueError:
                    pass
            
            question = Question(
                id=q_id,
                field_type=field_type,
                label=label,
                values=values,
                reason=reason,
                min_value=min_value,
                max_value=max_value,
            )
            questions.append(question)
        
        group = QuestionGroup(
            id=group_id,
            title=title,
            text=text,
            schedule=schedule,
            timeout=timeout,
            until=until,
            questions=questions,
        )
        groups.append(group)
    
    return groups


def _validate_single_question_as_group(config_data: Dict[str, Any]) -> QuestionGroup:
    """Converts single [question] config to QuestionGroup format.

    Args:
        config_data: Raw configuration with [question] section.

    Returns:
        QuestionGroup object with single question.
    """
    question_config = config_data["question"]
    question_id = question_config.get("id", "unknown")
    question_type = question_config.get("type", "question")
    title = question_config.get("title", question_id)
    text = question_config.get("text")
    schedule = question_config.get("schedule", "R * * * *")
    timeout = question_config.get("timeout", 60)
    
    until = question_config.get("until")
    if until and isinstance(until, str):
        until = datetime.fromisoformat(until)
    
    question = Question(
        id=question_id,
        field_type="entry",
        label=title or question_id,
        reason=False,
    )
    
    return QuestionGroup(
        id=f"single-{question_id}",
        title=title,
        text=text,
        schedule=schedule,
        timeout=timeout,
        until=until,
        questions=[question],
    )


def _validate_single_question(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates single question config and returns normalized version.

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
