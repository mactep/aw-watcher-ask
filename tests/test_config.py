# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT

"""Tests for configuration file handling."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from aw_watcher_ask.config import (
    ConfigError,
    get_default_config_path,
    load_config,
    _validate_config,
    _validate_question_groups,
)
from aw_watcher_ask.models import DialogType, FieldType, Question, QuestionGroup


def test_get_default_config_path():
    """Tests getting default config path."""
    path = get_default_config_path()
    assert path.name == "config.toml"
    assert path.parent.name == "aw-watcher-ask"
    assert path.parent.parent.name == "activitywatch"


def test_load_config_valid():
    """Tests loading a valid configuration file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "happiness.level"
type = "question"
title = "My happiness level"
text = "Are you feeling happy right now?"
schedule = "0 */1 * * * 0"
timeout = 120
until = "2100-12-31T23:59:59"
testing = false

[zenity]
extra_option = "value"
"""
        )
        f.flush()
        temp_path = f.name

    try:
        config = load_config(temp_path)
        assert config["question_id"] == "happiness.level"
        assert config["question_type"] == DialogType.question
        assert config["title"] == "My happiness level"
        assert config["text"] == "Are you feeling happy right now?"
        assert config["schedule"] == "0 */1 * * * 0"
        assert config["timeout"] == 120
        assert isinstance(config["until"], datetime)
        assert config["testing"] is False
        assert config["zenity_options"] == {"extra_option": "value"}
    finally:
        Path(temp_path).unlink()


def test_load_config_invalid_toml():
    """Tests handling invalid TOML syntax."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[invalid toml\n")
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ConfigError, match="Failed to parse TOML"):
            load_config(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_config_missing_fields():
    """Tests detecting missing required fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "test.question"
"""
        )
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ConfigError, match="Missing required field"):
            load_config(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_config_missing_question_section():
    """Tests detecting missing question section."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[zenity]
option = "value"
"""
        )
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ConfigError, match="Missing config: need \\[question\\] or \\[\\[question_groups\\]\\]"):
            load_config(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_config_invalid_dialog_type():
    """Tests validating dialog type enum values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "test.question"
type = "invalid_type"
"""
        )
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ConfigError, match="Invalid question type"):
            load_config(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_config_invalid_datetime():
    """Tests validating datetime format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "test.question"
type = "question"
until = "invalid-datetime"
"""
        )
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ConfigError, match="Invalid datetime format"):
            load_config(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_config_defaults():
    """Tests that optional fields get default values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "test.question"
type = "question"
"""
        )
        f.flush()
        temp_path = f.name

    try:
        config = load_config(temp_path)
        assert config["question_id"] == "test.question"
        assert config["question_type"] == DialogType.question
        assert config["title"] is None
        assert config["text"] is None
        assert config["schedule"] == "R * * * *"
        assert config["timeout"] == 60
        assert isinstance(config["until"], datetime)
        assert config["testing"] is False
        assert config["zenity_options"] == {}
    finally:
        Path(temp_path).unlink()


def test_load_config_file_not_found():
    """Tests handling missing config file."""
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config("/nonexistent/path/config.toml")


def test_validate_config_minimal():
    """Tests validating minimal config dict."""
    config = {
        "question": {
            "id": "test.id",
            "type": "question",
        }
    }
    result = _validate_config(config)
    assert result["question_id"] == "test.id"
    assert result["question_type"] == DialogType.question


def test_validate_config_with_all_fields():
    """Tests validating config dict with all fields."""
    config = {
        "question": {
            "id": "test.id",
            "type": "entry",
            "title": "Test Title",
            "text": "Test text",
            "schedule": "0 0 * * *",
            "timeout": 90,
            "until": "2025-01-01T00:00:00",
            "testing": True,
        },
        "zenity": {
            "width": "500",
            "height": "300",
        },
    }
    result = _validate_config(config)
    assert result["question_id"] == "test.id"
    assert result["question_type"] == DialogType.entry
    assert result["title"] == "Test Title"
    assert result["text"] == "Test text"
    assert result["schedule"] == "0 0 * * *"
    assert result["timeout"] == 90
    assert result["testing"] is True
    assert result["zenity_options"] == {"width": "500", "height": "300"}


def test_load_config_with_scale_options():
    """Tests loading config with scale type and min/max values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "happiness.level"
type = "scale"
title = "My happiness level"
text = "Are you feeling happy right now?"
min-value = 1
max-value = 10
schedule = "0 */1 * * * 0"
timeout = 120

[zenity]
extra_option = "value"
"""
        )
        f.flush()
        temp_path = f.name

    try:
        config = load_config(temp_path)
        assert config["question_id"] == "happiness.level"
        assert config["question_type"] == DialogType.scale
        assert config["zenity_options"] == {
            "extra_option": "value",
            "min-value": 1,
            "max-value": 10,
        }
    finally:
        Path(temp_path).unlink()


def test_load_config_with_scale_options_in_zenity():
    """Tests loading config with scale options in zenity section (backwards compat)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "happiness.level"
type = "scale"
title = "My happiness level"
text = "Are you feeling happy right now?"
schedule = "0 */1 * * * 0"
timeout = 120

[zenity]
min-value = 1
max-value = 10
"""
        )
        f.flush()
        temp_path = f.name

    try:
        config = load_config(temp_path)
        assert config["question_id"] == "happiness.level"
        assert config["question_type"] == DialogType.scale
        assert config["zenity_options"] == {
            "min-value": 1,
            "max-value": 10,
        }
    finally:
        Path(temp_path).unlink()


def test_load_config_with_question_groups():
    """Tests loading config with question_groups array."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[[question_groups]]
id = "daily-checkin"
title = "Daily Check-in"
text = "Please rate your current state:"
schedule = "*/10 * * * *"
timeout = 120

[[question_groups.questions]]
id = "happiness.level"
field_type = "combo"
label = "How happy are you?"
values = ["1", "2", "3", "4", "5"]
reason = true

[[question_groups.questions]]
id = "anxiety.level"
field_type = "combo"
label = "How anxious are you?"
values = ["1", "2", "3", "4", "5"]
reason = true
"""
        )
        f.flush()
        temp_path = f.name

    try:
        config = load_config(temp_path)
        assert config["has_question_groups"] is True
        assert len(config["question_groups"]) == 1
        
        group = config["question_groups"][0]
        assert group.id == "daily-checkin"
        assert group.title == "Daily Check-in"
        assert group.text == "Please rate your current state:"
        assert group.schedule == "*/10 * * * *"
        assert group.timeout == 120
        assert len(group.questions) == 2
        
        q1 = group.questions[0]
        assert q1.id == "happiness.level"
        assert q1.field_type == "combo"
        assert q1.label == "How happy are you?"
        assert q1.values == ["1", "2", "3", "4", "5"]
        assert q1.reason is True
        
        q2 = group.questions[1]
        assert q2.id == "anxiety.level"
        assert q2.field_type == "combo"
        assert q2.label == "How anxious are you?"
        assert q2.values == ["1", "2", "3", "4", "5"]
        assert q2.reason is True
    finally:
        Path(temp_path).unlink()


def test_load_config_mixed_format():
    """Tests loading config with both single question and question_groups."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[question]
id = "quick.mood"
type = "entry"
title = "Quick mood check"
schedule = "0 */2 * * *"
timeout = 30

[[question_groups]]
id = "daily-checkin"
title = "Daily Check-in"
schedule = "*/10 * * * *"

[[question_groups.questions]]
id = "happiness.level"
field_type = "combo"
label = "How happy?"
values = ["1", "2", "3"]
"""
        )
        f.flush()
        temp_path = f.name

    try:
        config = load_config(temp_path)
        assert config["has_question_groups"] is True
        assert len(config["question_groups"]) == 2
        
        # First group is from question_groups array
        group1 = config["question_groups"][0]
        assert group1.id == "daily-checkin"
        
        # Second group is converted from [question] section
        group2 = config["question_groups"][1]
        assert group2.id == "single-quick.mood"
    finally:
        Path(temp_path).unlink()


def test_validate_question_group_missing_id():
    """Tests that missing group id raises ConfigError."""
    config = {
        "question_groups": [
            {
                "title": "Test",
                "questions": [
                    {"id": "q1", "field_type": "entry", "label": "Q1"}
                ]
            }
        ]
    }
    with pytest.raises(ConfigError, match="missing required field 'id'"):
        _validate_question_groups(config)


def test_validate_question_group_missing_questions():
    """Tests that missing questions array raises ConfigError."""
    config = {
        "question_groups": [
            {
                "id": "test-group",
                "title": "Test"
            }
        ]
    }
    with pytest.raises(ConfigError, match="missing required 'questions' array"):
        _validate_question_groups(config)


def test_validate_question_missing_values_for_combo():
    """Tests that combo field without values raises ConfigError."""
    config = {
        "question_groups": [
            {
                "id": "test-group",
                "title": "Test",
                "questions": [
                    {"id": "q1", "field_type": "combo", "label": "Q1"}
                ]
            }
        ]
    }
    with pytest.raises(ConfigError, match="field_type 'combo' requires 'values' array"):
        _validate_question_groups(config)


def test_validate_question_with_reason_false():
    """Tests that reason defaults to False when not specified."""
    config = {
        "question_groups": [
            {
                "id": "test-group",
                "title": "Test",
                "questions": [
                    {"id": "q1", "field_type": "entry", "label": "Q1"}
                ]
            }
        ]
    }
    groups = _validate_question_groups(config)
    assert len(groups) == 1
    assert groups[0].questions[0].reason is False


def test_validate_question_group_with_until():
    """Tests parsing until datetime in question group."""
    config = {
        "question_groups": [
            {
                "id": "test-group",
                "title": "Test",
                "until": "2025-12-31T23:59:59",
                "questions": [
                    {"id": "q1", "field_type": "entry", "label": "Q1"}
                ]
            }
        ]
    }
    groups = _validate_question_groups(config)
    assert groups[0].until == datetime(2025, 12, 31, 23, 59, 59)
