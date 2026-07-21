from datetime import datetime
from random import randint
from typing import List, Optional
from uuid import UUID

import pandas as pd  # type: ignore  # AGENT

from pce import server
from pce import settings as st
from pce.controller import Controller
from pce.environment import Object, Shadow


class Player:
    def __init__(self, index: int, game) -> None:
        self.index = index
        self.game = game

        # --- AGENT (Condition 1: non-contingent replay) --------------------
        # If this player slot is the agent, it does NOT read a live rotary
        # controller; instead it plays back a recorded 2023 participant's
        # positions (see agent_step() below). Set this up BEFORE the
        # init_nonmotion() call further down.
        self.is_agent = (
            st.AGENT_ENABLED and self.index == st.AGENT_PLAYER_INDEX
        )
        self.replay_positions = None    # AGENT: recorded positions (pos1) we play back
        self.replay_timestamps = None   # AGENT: recorded time (s) of each position -> time-based lookup
        self.replay_index = 0           # AGENT: how far through the recording we are (advances during a trial)
        if self.is_agent:
            df = pd.read_csv(st.AGENT_REPLAY_CSV)               # load the one recorded 2023 trial
            self.replay_positions = df["pos1"].tolist()         # P1's avatar position at each recorded tick
            self.replay_timestamps = df["timestamp"].tolist()   # seconds-from-trial-start for each recorded tick

        self.controller = Controller(
            index,
            game.box,
            self.rotary_callback,
            self.longpress_callback,
        )
        self._pid: Optional[int] = None
        self.init_nonmotion()
        self._uuid: Optional[UUID] = None

        self.person = None
        self.personality_pre = None
        self.personality_after = None
        self.strategy = None
        self.partner_traits = None

        self.avatar: Optional[Object] = None
        self.static: Optional[Object] = None
        self.shadow: Optional[Shadow] = None
        self.history_x: Optional[List[float]] = None
        self.history_button: Optional[List[int]] = None
        self.rotary_dts: Optional[List[datetime]] = None

        self.init_nonmotion()

    def __repr__(self):
        return f"P{self.index}={self.pid}"

    @property
    def uuid(self) -> Optional[UUID]:
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID) -> None:
        if self._uuid is not None:
            raise ValueError("uuid is already set")
        self._uuid = value

    @property
    def pid(self) -> Optional[int]:
        return self._pid

    @pid.setter
    def pid(self, value: int) -> None:
        if self._pid is not None:
            raise ValueError("pid is already set")
        self._pid = value

    def rotary_callback(self, direction: int) -> None:
        if self.avatar is not None:
            self.avatar.x += direction * st.ROTARY_INCREMENT
            # TODO: type: separate cases functionally as would do in Elm
            self.rotary_dts.append(datetime.utcnow())  # type: ignore

    # --- AGENT: move the replay avatar to its recorded position -------------
    # Called once per TICK from phase.py -> Trial.step(). `elapsed` is the
    # number of seconds since this trial started.
    #
    # WHY look up by TIME instead of by tick count: the live loop on this Mac
    # runs faster (~838 Hz) than the 2023 recording (~566 Hz). If we advanced
    # one recorded row per tick, we'd burn through the ~34k rows in ~40 s and
    # then freeze on the last row for the final ~20 s of the trial. Looking up
    # the recording by elapsed TIME plays it at its true speed and spans the
    # whole ~60 s trial no matter how fast the live loop runs.
    # (Fix is written; still to be verified end-to-end on a full trial.)
    def agent_step(self, elapsed: float) -> None:
        if not self.is_agent or self.avatar is None:
            return  # no-op for the live human, and before the avatar exists
        ts = self.replay_timestamps
        # Walk the pointer forward while the NEXT recorded timestamp is still
        # <= elapsed -> i.e. pick the latest recorded sample at/before "now".
        # `elapsed` only increases within a trial, so this never scans backward.
        while (self.replay_index + 1 < len(ts)
               and ts[self.replay_index + 1] <= elapsed):
            self.replay_index += 1
        i = min(self.replay_index, len(self.replay_positions) - 1)  # clamp to last recorded row
        self.avatar.x = self.replay_positions[i]  # place the agent avatar at that recorded position

    def _broadcast_events(self) -> None:
        if hasattr(self.game, "webapp"):
            server.ws_broadcast(
                self.game.webapp["ws_clients"],
                self.game.players_event(),
                # Provide the main event loop, as this may be called from
                # another OS thread coming from PiGPIO
                self.game.loop,
            )

    def longpress_callback(self) -> None:
        if self.can_become_ready and self.game.phase.can_become_ready(self):
            self._ready = True
            # Provide the main event loop, as this may be called from
            # another OS thread coming from PiGPIO
            self.controller.short_beep(loop=self.game.loop)
            self._broadcast_events()

    @property
    def can_become_ready(self) -> bool:
        return self.uuid is not None and self.pid is not None

    @property
    def ready(self) -> bool:
        return self._ready

    def clear_ready(self) -> None:
        self._ready = False
        self._broadcast_events()

    def init_motion(self, shadow_side) -> None:
        self.rotary_dts = [datetime.utcnow()]

        self.avatar = Object(
            randint(*st.AVATAR_STARTX_RANGES[self.index]), st.AVATAR_WIDTH
        )

        if self.index == 0:
            st.OBJ_LOCATION_ZERO = randint(*st.STATIC_X[self.index])
            self.static = Object(
                st.OBJ_LOCATION_ZERO, st.STATIC_WIDTH) #MAKING OBJECTS AN ARRAY #Object(st.STATIC_X[self.index], st.STATIC_WIDTH)
        elif self.index == 1:
            st.OBJ_LOCATION_ONE = st.OBJ_LOCATION_ZERO+300
            self.static = Object(
                st.OBJ_LOCATION_ONE, st.STATIC_WIDTH) #MAKING OBJECTS AN ARRAY #Object(st.STATIC_X[self.index], st.STATIC_WIDTH)

        self.shadow = Shadow(self.avatar, shadow_side)

        self.clear_ready()
        self.controller.clear_button_press()
        self.controller.clear_button_pressed_memory()

        self.history_x = []
        self.history_button = []

        self.replay_index = 0  # AGENT: rewind the replay to the first row for each new trial

    def init_nonmotion(self) -> None:
        self.avatar = None
        self.static = None
        self.shadow = None

        self.clear_ready()
        self.controller.clear_button_press()
        self.controller.clear_button_pressed_memory()

        self.history_x = None
        self.history_button = None
        self.rotary_dts = None

    def record(self) -> None:
        # TODO: type: separate cases functionally as would do in Elm
        self.history_x.append(self.avatar.x)  # type: ignore
        self.controller.record_button_press(self.history_button)
        # To test the delay between a button being pressed (as measured by a
        # direct connection to the EEG system) and this function being called as
        # python records the button pressed, send a trigger to the EEG system
        # here and compare its EEG detection to the direct connection to the EEG
        # system:
        #
        # if len(self.history_button) > 1:
        #     if self.history_button[-1] and not self.history_button[-2]:
        #         self.game.box.signal.trial()
        #     if not self.history_button[-1] and self.history_button[-2]:
        #         self.game.box.signal.standby()
