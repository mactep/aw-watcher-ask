# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT


"""Direct zenity CLI wrapper for NixOS compatibility."""


import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


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
    form_fields: Optional[List[Dict[str, Any]]] = None,
    reason_fields: Optional[List[bool]] = None,
    **kwargs: Any,
) -> Tuple[bool, str]:
    """Display a zenity dialog and capture user input.

    Args:
        dialog_type: Type of dialog to display (e.g., "question", "entry", "forms")
        title: Window title for the dialog
        text: Text message to display
        timeout: Timeout in seconds
        form_fields: List of dicts with field_type, label, values (for forms dialog)
        reason_fields: List of bools indicating which form fields have reason fields
        **kwargs: Additional zenity options

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

    if dialog_type == "forms" and form_fields:
        for i, field in enumerate(form_fields):
            field_type = field.get("field_type", "entry")
            label = field.get("label", "")
            values = field.get("values", [])

            if field_type == "combo":
                cmd.extend(["--add-combo", label])
                if values:
                    cmd.extend(["--combo-values", "|".join(str(v) for v in values)])
            elif field_type == "entry":
                cmd.extend(["--add-entry", label])

            if reason_fields and i < len(reason_fields) and reason_fields[i]:
                cmd.extend(["--add-entry", "Reason"])

    min_value = kwargs.get("min-value")
    max_value = kwargs.get("max-value")
    value = kwargs.get("value")

    if min_value is not None:
        cmd.append(f"--min-value={min_value}")

    if max_value is not None:
        cmd.append(f"--max-value={max_value}")

    if value is None and min_value is not None and max_value is not None:
        value = (min_value + max_value) // 2

    if value is not None:
        cmd.append(f"--value={value}")

    logger.debug(f"Zenity command: {cmd}")

    env = os.environ.copy()
    if "DISPLAY" not in env:
        logger.warning("DISPLAY environment variable not set, zenity may not display windows")
    if "WAYLAND_DISPLAY" in env:
        logger.debug(f"Wayland display detected: {env['WAYLAND_DISPLAY']}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            env=env,
        )

        logger.debug(f"Zenity return code: {result.returncode}")
        logger.debug(f"Zenity stdout: {result.stdout!r}")
        if result.stderr:
            logger.debug(f"Zenity stderr: {result.stderr!r}")

        if result.returncode == 0:
            return True, result.stdout.strip()

        if result.returncode == 1:
            logger.warning(f"Zenity closed by user (return code 1)")
        elif result.returncode == 5:
            logger.warning("Zenity timed out or displayed warning (return code 5)")
        else:
            logger.warning(f"Zenity exited with unexpected return code {result.returncode}")

        return False, ""

    except subprocess.TimeoutExpired:
        logger.warning("Zenity subprocess timed out")
        return False, ""
    except FileNotFoundError:
        logger.error("Zenity not found in PATH")
        return False, ""
    except Exception as e:
        logger.error(f"Unexpected error running zenity: {e}")
        return False, ""
