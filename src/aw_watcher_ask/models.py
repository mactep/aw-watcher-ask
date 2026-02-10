# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT

"""Representations for exchanging data with Zenity and ActivityWatch."""


from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class DialogType(str, Enum):
    calendar = "calendar"  # Display calendar dialog
    entry = "entry"  # Display text entry dialog
    error = "error"  # Display error dialog
    info = "info"  # Display info dialog
    file_selection = "file-selection"  # Display file selection dialog
    list = "list"  # Display list dialog
    notification = "notification"  # Display notification
    progress = "progress"  # Display progress indication dialog
    warning = "warning"  # Display warning dialog
    scale = "scale"  # Display scale dialog
    text_info = "text-info"  # Display text information dialog
    color_selection = "color-selection"  # Display color selection dialog
    question = "question"  # Display question dialog
    password = "password"  # Display password dialog
    forms = "forms"  # Display forms dialog


class FieldType(str, Enum):
    entry = "entry"  # Text entry field
    combo = "combo"  # Dropdown with predefined values


@dataclass
class Question:
    """Represents a single question in a question group."""
    id: str
    field_type: str
    label: str
    values: Optional[List[str]] = None
    reason: bool = False
    min_value: Optional[int] = None
    max_value: Optional[int] = None


@dataclass
class QuestionGroup:
    """Represents a group of questions with a shared schedule."""
    id: str
    title: str
    text: Optional[str] = None
    schedule: str = "R * * * *"
    timeout: int = 60
    until: Optional[datetime] = None
    questions: Optional[List[Question]] = None
    
    def __post_init__(self):
        if self.questions is None:
            self.questions = []
