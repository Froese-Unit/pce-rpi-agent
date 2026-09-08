import argparse
import asyncio
import logging
import os
from collections import deque
from datetime import datetime
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional
from uuid import UUID

import aiohttp
from rich import box
from rich.panel import Panel
from rich.table import Table
from textual.app import App  # type: ignore
from textual.widget import Widget  # type: ignore

import pce.settings as st
from pce.box import Box
from pce.phase import Phase, new_phase
from pce.player import Player
from pce.types import Event, OutEvents
from pce.utils import create_task, run_at_rate

logger = logging.getLogger(__name__)


class WidgetHandler(logging.Handler):
    def __init__(
        self,
        msghandler: Callable[[logging.LogRecord], None],
        level: int = logging.NOTSET,
    ) -> None:
        self.msghandler = msghandler
        super().__init__(level=level)

    def emit(self, record: logging.LogRecord) -> None:
        self.msghandler(record)


class Log(Widget):
    def __init__(self) -> None:
        self.render_padding = 4
        self.records: Deque[logging.LogRecord] = deque([], maxlen=10)
        super().__init__()

    async def on_resize(self, event: Event) -> None:
        await super().on_resize(event)
        if self.records.maxlen != self.size[1] - self.render_padding:
            self.records = deque(
                self.records, maxlen=max(10, self.size[1] - self.render_padding)
            )

    def add_message(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        self.refresh()

    def render(self) -> Table:
        table = Table(
            show_header=True, header_style="magenta", box=box.SIMPLE, expand=True
        )
        table.add_column("Time", style="dim", no_wrap=True)
        table.add_column("Level", style="dim", no_wrap=True)
        table.add_column("Name", no_wrap=True, justify="right")
        table.add_column("Message", no_wrap=True, ratio=1)
        for record in self.records:
            table.add_row(record.asctime, record.levelname, record.name, record.message)

        return table


class State(Widget):
    def __init__(self, game: "Game") -> None:
        self.game = game
        super().__init__()

    def render(self) -> Panel:
        x0 = getattr(self.game.players[0].avatar, "x", None)
        x1 = getattr(self.game.players[1].avatar, "x", None)
        return Panel(f"Player 0: {x0}\nPlayer 1: {x1}")


class Tui(App):
    def __init__(
        self,
        game: "Game",
        cliargs: argparse.Namespace,
        stream_handler: logging.StreamHandler,
    ) -> None:
        self.game = game
        self.cliargs = cliargs
        self.stream_handler = stream_handler
        super().__init__()

    async def on_mount(self) -> None:
        self.state_widget = State(self.game)
        await self.view.dock(self.state_widget, edge="top", size=4)
        self.state_refresh_task = create_task(run_at_rate(4, self.state_widget.refresh))

        # TODO: add header with current keybindings

        log_widget = Log()
        logger.info("tui: adding widget handler")
        self.widget_handler = WidgetHandler(log_widget.add_message)
        self.widget_handler.setLevel(logging.INFO)
        self.widget_handler.setFormatter(logging.Formatter(st.LOGGING_FORMAT))
        logging.getLogger().addHandler(self.widget_handler)
        logger.info("tui: added widget handler")
        await self.view.dock(log_widget, edge="top")

        logger.info("tui: removing stream_handler")
        logging.getLogger().removeHandler(self.stream_handler)

    async def on_load(self, event) -> None:
        await self.bind("q", "quit")
        if self.cliargs.mockpins:
            await self.bind("right", "move(0, 1)")
            await self.bind("left", "move(0, -1)")
            await self.bind("up", "move(1, 1)")
            await self.bind("down", "move(1, -1)")
            await self.bind("0", "press(0)")
            await self.bind("1", "press(1)")
            await self.bind("9", "longpress(0)")
            await self.bind("2", "longpress(1)")

    async def action_move(self, player: int, direction: int) -> None:
        logger.info("tui: player %s: move %s", player, direction)
        # Multipy movement as the actual rotary encoder does 1024 ticks per rotation
        # 20260813 AH: bumped 10 -> st.TUI_MOVE_TICKS. At 10 ticks a keypress moves
        # 10 * 0.46875 = 4.7 units, so a ~15/s key-repeat gives ~70 units/s -- a
        # quarter of the agent's 280 units/s explore speed. You then cannot stay
        # in contact, V never reaches AGENT_V_THRESHOLD, and the agent looks like
        # it is ignoring you. Keyboard testing only; the real rotary is unaffected.
        for _ in range(st.TUI_MOVE_TICKS):
            self.game.players[player].rotary_callback(direction)

    async def action_press(self, player: int) -> None:
        logger.info("tui: player %s: button press", player)
        self.game.players[player].controller.log_button_press()

    async def action_longpress(self, player: int) -> None:
        logger.info("tui: player %s: button longpress", player)
        self.game.players[player].longpress_callback()

    async def action_quit(self) -> None:
        logger.info("tui: quit")
        self.state_refresh_task.cancel()

        logger.info("tui: restoring stream_handler")
        logging.getLogger().addHandler(self.stream_handler)
        logger.info("tui: removing widget_handler")
        logging.getLogger().removeHandler(self.widget_handler)
        await super().action_quit()


class Game:
    def __init__(
        self,
        cliargs: argparse.Namespace,
        sequence: List[Phase],
        stream_handler: logging.StreamHandler,
        trials_dir: str,
        log_dir: str,
        file_prefix: str,
    ) -> None:
        self.cliargs = cliargs
        self.sequence = sequence
        self.stream_handler = stream_handler
        self.trials_dir = trials_dir
        self.log_dir = log_dir
        self.file_prefix = file_prefix

        self.box = Box()
        self.players = [Player(i, self) for i in range(2)]
        self.experimenter_uuid = None
        self.phase: Optional[Phase] = None

        # if self.cliargs.test is None: # 20260715 AH edits (added and not self.cliargs.mockpins so the raw GPIO button-pin setup is skipped in mock mode.)
        #     import RPi.GPIO as GPIO
        #     GPIO.setmode(GPIO.BCM)
        #     GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 0 ground
        #     GPIO.setup(9, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 0 voltage
        #     GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 1 ground
        #     GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 1 voltage
        if self.cliargs.test is None and not self.cliargs.mockpins:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 0 ground
            GPIO.setup(9, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 0 voltage
            GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 1 ground
            GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)#player 1 voltage

    async def create_tasks(self, webapp: aiohttp.web.Application) -> None:
        self.webapp = webapp
        self.loop = asyncio.get_running_loop()

        async def run_tui():
            tui = Tui(self, self.cliargs, self.stream_handler)
            await tui.process_messages()
            logger.info("game: shutdown web app")
            raise aiohttp.web_runner.GracefulExit()

        if self.cliargs.tui:
            create_task(run_tui())

        self.phase = new_phase(0, self, webapp)
        self.phase.start()

    async def cancel_tasks(self, _app: aiohttp.web.Application) -> None:
        if self.phase is not None:
            self.phase.cleanup_tasks()

    def own_slot(self, uuid: UUID) -> Optional[str]:
        if self.experimenter_uuid == uuid:
            return "experimenter"
        if self.players[0].uuid == uuid:
            return "p0"
        if self.players[1].uuid == uuid:
            return "p1"
        return None

    def slots_data(self) -> Dict[str, Optional[UUID]]:
        return {
            "experimenter": self.experimenter_uuid,
            "p0": self.players[0].uuid,
            "p1": self.players[1].uuid,
        }

    def pids_data(self) -> Dict[str, Optional[int]]:
        return {
            "p0": self.players[0].pid,
            "p1": self.players[1].pid,
        }

    def meta_data(self, uuid: UUID) -> Dict[str, Any]:
        return {
            "slots": self.slots_data(),
            "pids": self.pids_data(),
            "uuid": uuid,
            "lang": st.LANGUAGE,
            "training_trial_has_questionnaires": st.TRAINING_TRIAL_HAS_QUESTIONNAIRES
        }

    def meta_event(self, uuid: UUID) -> Event:
        return {"tipe": OutEvents.meta, "data": self.meta_data(uuid)}

    def players_data(self) -> Dict[str, Dict[str, Any]]:
        return {
            "p0": {
                "x": getattr(
                    self.players[0].avatar, "x", st.AVATAR_STARTX_RANGES[0][0]
                ),
                "button": self.players[0].controller.button_pressed,
                "ready": self.players[0].ready,
                "clicked": self.players[0].controller.button_pressed_memory,
            },
            "p1": {
                "x": getattr(
                    self.players[1].avatar, "x", st.AVATAR_STARTX_RANGES[1][0]
                ),
                "button": self.players[1].controller.button_pressed,
                "ready": self.players[1].ready,
                "clicked": self.players[1].controller.button_pressed_memory,
            },
        }

    def players_event(self) -> Event:
        return {"tipe": OutEvents.players, "data": self.players_data()}
