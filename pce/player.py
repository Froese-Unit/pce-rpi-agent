from datetime import datetime
from random import randint
from typing import List, Optional
from uuid import UUID

from pce import server
from pce import settings as st
from pce.controller import Controller
from pce.environment import Object, Shadow


class Player:
    def __init__(self, index: int, game) -> None:
        self.index = index
        self.game = game
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
