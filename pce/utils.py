import asyncio
import csv
import functools
import inspect
import logging
import os
import pprint
import re
from concurrent.futures import CancelledError

logger = logging.getLogger(__name__)


camel_to_snake_pattern1 = re.compile("(.)([A-Z][a-z]+)")
camel_to_snake_pattern2 = re.compile("([a-z0-9])([A-Z])")


def camel_to_snake(name):
    name = camel_to_snake_pattern1.sub(r"\1_\2", name)
    return camel_to_snake_pattern2.sub(r"\1_\2", name).lower()


def create_task(coro, loop=None):
    if loop is None:
        loop = asyncio.get_running_loop()
    task = asyncio.run_coroutine_threadsafe(coro, loop)
    task.add_done_callback(functools.partial(_handle_task_result))
    return task


def run_in_executor(executor, loop, func, *args):
    task = loop.run_in_executor(executor, func, *args)
    task.add_done_callback(functools.partial(_handle_task_result))
    return task


def _handle_task_result(task):
    try:
        task.result()
    except CancelledError:
        pass  # Task cancellation should not be logged as an error.
    # Add the pylint ignore: we want to handle all exceptions here so that the result of the task
    # is properly logged. There is no point re-raising the exception in this callback.
    except Exception as e:  # pylint: disable=broad-except
        logger.exception(pprint.pformat(e))


async def run_at_rate(
    rate, f, condition=None, async_start_f=None, start_f=None, end_f=None
):
    assert not asyncio.iscoroutine(start_f)
    assert not asyncio.iscoroutine(end_f)

    logger.debug("run_at_rate: %s", f.__name__)
    loop = asyncio.get_running_loop()

    nargs_f = len(inspect.signature(f).parameters)
    if nargs_f == 0:
        call_f = f
    elif nargs_f == 1:
        call_f = lambda: f(loop_end_time)
    else:
        assert nargs_f == 2
        call_f = lambda: f(loop_end_time, start_time)

    if condition is None:
        call_condition = lambda: True
    else:
        nargs_condition = len(inspect.signature(condition).parameters)
        if nargs_condition == 0:
            call_condition = condition
        elif nargs_condition == 1:
            call_condition = lambda: condition(loop_end_time)
        else:
            assert nargs_condition == 2
            call_condition = lambda: condition(loop_end_time, start_time)

    if async_start_f is not None:
        await async_start_f()
    if start_f is not None:
        start_f()
    start_time = loop.time()
    loop_end_time = start_time

    while call_condition():
        call_f()
        await asyncio.sleep(1 / rate - (loop.time() - loop_end_time))
        loop_end_time = loop.time()

    if end_f is not None:
        end_f()


def public_variables(obj):
    return [
        (item, getattr(obj, item)) for item in dir(obj) if not item.startswith("__")
    ]


def px_true(d):
    return d["p0"] and d["p1"]


def save_csv(filepath, fieldnames, rows):
    add_header = not os.path.exists(filepath)
    with open(filepath, "a") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if add_header:
            writer.writeheader()
        writer.writerows(rows)
