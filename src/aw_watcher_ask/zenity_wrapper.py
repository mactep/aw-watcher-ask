# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT


"""Direct zenity CLI wrapper for NixOS compatibility."""


import subprocess
from typing import Any, Dict, Optional, Tuple


DIALOG_TYPE_MAP = {
    "calendar": "--calendar",
    "entry": "--entry",
    "error": "--error",
    "info": "--info",
    "file-selection": "--file-selection",
    "list": "--list",
    "notification": "--notification",
    "progress": "--progress",
    "warning": "--warning",
    "scale": "--scale",
    "text-info": "--text-info",
    "color-selection": "--color-selection",
    "question": "--question",
    "password": "--password",
    "forms": "--forms",
}


def show(
    dialog_type: str,
    title: Optional[str] = None,
    text: Optional[str] = None,
    timeout: int = 60,
    **kwargs: Any,
) -> Tuple[bool, str]:
    """Display a zenity dialog and capture user input.

    Args:
        dialog_type: Type of dialog to display (e.g., "question", "entry")
        title: Window title for the dialog
        text: Text message to display
        timeout: Timeout in seconds
        **kwargs: Additional zenity options (ignored for simple dialogs)

    Returns:
        Tuple of (success, content) where success is True if user responded,
        and content is the user's input or empty string.
    """

    if dialog_type not in DIALOG_TYPE_MAP:
        return False, ""

    cmd = ["zenity", DIALOG_TYPE_MAP[dialog_type]]

    if title:
        cmd.extend(["--title", title])

    if text:
        cmd.extend(["--text", text])

    if timeout:
        cmd.extend(["--timeout", str(timeout)])

    min_value = kwargs.get("min-value")
    if min_value is not None:
        cmd.extend(["--min-value", str(min_value)])

    max_value = kwargs.get("max-value")
    if max_value is not None:
        cmd.extend(["--max-value", str(max_value)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )

        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, ""

    except subprocess.TimeoutExpired:
        return False, ""
    except FileNotFoundError:
        return False, ""
    except Exception:
        return False, ""
