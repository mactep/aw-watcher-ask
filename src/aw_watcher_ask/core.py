# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT


"""Watcher function and helpers."""


import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from aw_client import ActivityWatchClient
from aw_core.models import Event
from croniter import croniter
from loguru import logger

from aw_watcher_ask.models import DialogType, Question, QuestionGroup
from aw_watcher_ask.utils import fix_id, is_valid_id, get_current_datetime
from aw_watcher_ask.zenity_wrapper import show as zenity_show


def _bucket_setup(client: ActivityWatchClient, question_id: str) -> str:
    """Makes sure a bucket exists in the client for the given event type."""

    bucket_id = "{}_{}".format(client.client_name, client.client_hostname)
    client.create_bucket(bucket_id, event_type=question_id)

    return bucket_id


def _client_setup(testing: bool = False) -> ActivityWatchClient:
    """Builds a new ActivityWatcher client instance and bucket."""

    # set client name
    client_name = "aw-watcher-ask"
    if testing:
        client_name = "test-" + client_name

    # create client representation
    return ActivityWatchClient(client_name, testing=testing)


def _ask_one(
    question_id: str, question_type: DialogType, title: str, *args, **kwargs
) -> Dict[str, Any]:
    """Captures an user's response to a dialog box with a single field."""
    kwargs.pop("ctx", None)
    logger.debug(f"Calling zenity with type={question_type.value}, title={title}")
    logger.debug(f"Additional kwargs: {kwargs}")

    success, content = zenity_show(
        question_type.value, title=title, *args, **kwargs
    )

    result = {
        "success": success,
        "question_id": question_id,
        "title": title,
        "value": content,
    }

    if question_type == DialogType.scale:
        result["min-value"] = kwargs.get("min-value")
        result["max-value"] = kwargs.get("max-value")

    logger.debug(f"Zenity response: success={success}, content={content!r}")
    return result


def _ask_many(
    group_id: str,
    questions: List[Question],
    title: str,
    text: Optional[str],
    timeout: int,
    **kwargs,
) -> Dict[str, Dict[str, Any]]:
    """Captures the user's response to a dialog box with multiple fields.

    Args:
        group_id: Identifier for the question group
        questions: List of Question objects with id, field_type, label, values, reason
        title: Window title for the dialog
        text: Text message to display
        timeout: Timeout in seconds
        **kwargs: Additional zenity options

    Returns:
        Dict mapping question_id to response dict. Empty values are excluded.
    """
    form_fields = [
        {
            "field_type": q.field_type,
            "label": q.label,
            "values": q.values or []
        }
        for q in questions
    ]
    
    reason_fields = [q.reason for q in questions]

    success, content = zenity_show(
        "forms",
        title=title,
        text=text,
        timeout=timeout,
        form_fields=form_fields,
        reason_fields=reason_fields,
        **kwargs
    )

    if not success or not content:
        return {}

    values = content.split("|")
    result = {}

    for i, question in enumerate(questions):
        value_idx = i * 2 if question.reason else i
        reason_idx = value_idx + 1 if question.reason else -1
        
        if value_idx < len(values):
            response = {
                "success": True,
                "question_id": question.id,
                "group_id": group_id,
                "title": question.label,
                "value": values[value_idx],
                "field_type": question.field_type,
            }
            
            if question.reason and reason_idx < len(values):
                response["reason"] = values[reason_idx]
            
            result[question.id] = response

    return result


def main(
    question_id: str,
    question_type: DialogType = DialogType.question,
    title: Optional[str] = None,
    schedule: str = "R * * * *",
    until: datetime = datetime(2100, 12, 31),
    timeout: int = 60,
    testing: bool = False,
    verbose: bool = False,
    *args,
    **kwargs,
) -> None:
    """Gathers user's inputs and send them to ActivityWatch.

    This watcher periodically presents a dialog box to the user, and stores the
    provided answer on the locally running [ActivityWatch]
    (https://docs.activitywatch.net/) server. It relies on [Zenity]
    (https://help.gnome.org/users/zenity/stable/index.html.en) to construct
    simple graphic interfaces.

    Arguments:
        question_id: A short string to identify your question in ActivityWatch
            server records. Should contain only lower-case letters, numbers and
            dots. If `title` is not provided, this will also be the
            key to identify the content of the answer in the ActivityWatch
            bucket's raw data.
        question_type: The type of dialog box to present the user, provided as
            one of [`aw_watcher_ask.models.DialogType`]
            [aw_watcher_ask.models.DialogType] enumeration types. Currently,
            `DialogType.forms`, `DialogType.list` and
            `DialogType.file_selection` are not supported. Defaults to
            `DialogType.question`.
        title: An optional title for the question. If provided, this
            will be both the title of the dialog box and the key that
            identifies the content of the answer in the ActivityWatch bucket's
            raw data.
        schedule: A [cron-tab expression](https://en.wikipedia.org/wiki/Cron)
            that controls the execution intervals at which the user should be
            prompted to answer the given question. Accepts 'R' as a keyword at
            second, minute and hour positions, for prompting at random times.
            Might be a classic five-element expression, or optionally have a
            sixth element to indicate the seconds.
        until: A [`datetime.datetime`]
            (https://docs.python.org/3/library/datetime.html#datetime-objects)
            object, that indicates the date and time when to stop gathering
            input from the user. Defaults to `datetime(2100, 12, 31)`.
        timeout: The amount of seconds to wait for user's input. Defaults to
            60 seconds.
        testing: Whether to run the [`aw_client.ActivityWatchClient`]
            (https://docs.activitywatch.net/en/latest/api/python.html
            #aw_client.ActivityWatchClient) client in testing mode.
        verbose: Whether to enable debug logging output. Defaults to False.
        *args: Variable lenght argument list to be passed to [`zenity.show()`]
            (https://pyzenity.gitbook.io/docs/) Zenity wrapper.
        **kwargs: Variable lenght argument list to be passed to
            [`zenity.show()`](https://pyzenity.gitbook.io/docs/) Zenity
            wrapper.

    Raises:
        NotImplementedError: If the provided `question_type` is one of
            `DialogType.forms`, `DialogType.list` or
            `DialogType.file_selection`.
    """

    log_format = "{time} <{extra[question_id]}>: {level} - {message}"
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO", format=log_format)
    log = logger.bind(question_id=question_id)

    log.info("Starting new watcher...")

    # fix question-id if it was provided with forbidden characters
    if not is_valid_id(question_id):
        question_id = fix_id(question_id)
        log.warning(
            f"An invalid question_id was provided. Fixed to `{question_id}`."
        )
        log = log.bind(question_id=question_id)

    # fix offset-naive datetimes
    if not until.tzinfo:
        system_timezone = get_current_datetime().astimezone().tzinfo
        until = until.replace(tzinfo=system_timezone)

    # start client and bucket
    client = _client_setup(testing=testing)
    log.info(
        f"Client created and connected to server at {client.server_address}."
    )
    bucket_id = _bucket_setup(client, question_id)

    # execution schedule
    executions = croniter(schedule, start_time=get_current_datetime())

    # run service
    while get_current_datetime() < until:
        # wait until next execution
        next_execution = executions.get_next(datetime)
        log.info(
            f"Next execution scheduled to {next_execution.isoformat()}."
        )
        sleep_time = next_execution - get_current_datetime()
        time.sleep(max(sleep_time.total_seconds(), 0))

        log.info(
            "New prompt fired. Waiting for user input..."
        )
        if question_type.value in ["forms", "file-selection", "list"]:
            # TODO: not implemented
            answer = _ask_many(
                question_type=question_type,
                title=title or question_id,
                timeout=timeout,
                *args,
                **kwargs,
            )
        else:
            answer = _ask_one(
                question_id=question_id,
                question_type=question_type,
                title=(
                    title if title else question_id
                ),
                timeout=timeout,
                *args,
                **kwargs,
            )

        log.debug(f"Answer received: {answer}")

        if not answer["success"]:
            log.info("Prompt timed out with no response from user.")
        else:
            log.info(f"User provided response: {answer}")

        event = Event(timestamp=get_current_datetime(), data=answer)
        client.insert_event(bucket_id, event)
        log.info(f"Event stored in bucket '{bucket_id}'.")


def main_for_groups(
    question_groups: List[QuestionGroup],
    testing: bool = False,
    verbose: bool = False,
) -> None:
    """Runs multiple question groups with independent schedules.

    Each group has its own croniter for scheduling. When a group triggers,
    all its questions are displayed in a single zenity forms dialog.
    Each question response is stored as a separate event in ActivityWatch.

    Args:
        question_groups: List of QuestionGroup objects to run
        testing: Whether to run ActivityWatch Client in testing mode
        verbose: Whether to enable debug logging output
    """
    log_format = "{time} <{extra[group_id]}>: {level} - {message}"
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO", format=log_format)

    log = logger.bind(group_id="main")
    log.info(f"Starting watcher with {len(question_groups)} question groups...")

    client = _client_setup(testing=testing)
    log.info(f"Client created and connected to server at {client.server_address}.")

    bucket_id = _bucket_setup(client, "ask.question")

    group_executions = []
    for group in question_groups:
        until = group.until if group.until else datetime(2100, 12, 31)
        if not until.tzinfo:
            system_timezone = get_current_datetime().astimezone().tzinfo
            until = until.replace(tzinfo=system_timezone)
        cron = croniter(group.schedule, start_time=get_current_datetime())
        group_executions.append({
            "group": group,
            "croniter": cron,
            "until": until,
            "next_execution": cron.get_next(datetime),
        })

    while True:
        active_groups = [e for e in group_executions if e["until"] > get_current_datetime()]
        
        if not active_groups:
            log.info("All question groups have expired. Stopping watcher.")
            break

        next_times = [(e["next_execution"], e["group"].id) for e in active_groups]
        next_times.sort(key=lambda x: x[0])
        next_execution, next_group_id = next_times[0]
        log.info(f"Next execution scheduled to {next_execution.isoformat()} for group '{next_group_id}'.")

        sleep_time = next_execution - get_current_datetime()
        time.sleep(max(sleep_time.total_seconds(), 0))

        triggered_groups = [
            e for e in group_executions
            if e["until"] > get_current_datetime()
            and e["next_execution"].timestamp() == next_execution.timestamp()
        ]

        for execution in triggered_groups:
            group = execution["group"]
            log.info(f"New prompt fired for group '{group.id}'. Waiting for user input...")

            responses = _ask_many(
                group_id=group.id,
                questions=group.questions,
                title=group.title,
                text=group.text,
                timeout=group.timeout,
            )

            for question in group.questions:
                response = responses.get(question.id)
                
                if response:
                    log.info(f"Question '{question.id}': User provided response: {response['value']}")
                    if response.get("reason"):
                        log.info(f"Question '{question.id}': Reason: {response['reason']}")
                else:
                    log.info(f"Question '{question.id}': No response from user")
                    response = {
                        "success": False,
                        "question_id": question.id,
                        "group_id": group.id,
                        "title": question.label,
                        "value": "",
                        "field_type": question.field_type,
                    }
                    if question.reason:
                        response["reason"] = ""

                event = Event(timestamp=get_current_datetime(), data=response)
                client.insert_event(bucket_id, event)
                log.info(f"Event for question '{question.id}' stored in bucket '{bucket_id}'.")
            
            execution["next_execution"] = execution["croniter"].get_next(datetime)

            for question in group.questions:
                response = responses.get(question.id)
                
                if response:
                    log.info(f"Question '{question.id}': User provided response: {response['value']}")
                    if response.get("reason"):
                        log.info(f"Question '{question.id}': Reason: {response['reason']}")
                else:
                    log.info(f"Question '{question.id}': No response from user")
                    response = {
                        "success": False,
                        "question_id": question.id,
                        "group_id": group.id,
                        "title": question.label,
                        "value": "",
                        "field_type": question.field_type,
                    }
                    if question.reason:
                        response["reason"] = ""

                event = Event(timestamp=get_current_datetime(), data=response)
                client.insert_event(bucket_id, event)
                log.info(f"Event for question '{question.id}' stored in bucket '{bucket_id}'.")
