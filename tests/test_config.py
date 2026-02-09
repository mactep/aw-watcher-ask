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
)
from aw_watcher_ask.models import DialogType


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
        with pytest.raises(ConfigError, match="Missing required \\[question\\] section"):
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
