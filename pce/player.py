import logging
from datetime import datetime
from random import randint, random, shuffle, uniform
from typing import List, Optional
from uuid import UUID, uuid4

import pandas as pd  # type: ignore  # AGENT

from pce import server
from pce import settings as st
from pce.controller import Controller
from pce.environment import Object, Shadow

logger = logging.getLogger(__name__)  # AGENT 20260813: for the V/mode debug log


class Player:
    def __init__(self, index: int, game) -> None:
        self.index = index
        self.game = game

        # --- AGENT: which slot is the agent? ---------------------------------
        # If this player slot is the agent, it does NOT read a live rotary
        # controller; agent_step() drives it instead (see below). Set this up
        # BEFORE the init_nonmotion() call further down.
        self.is_agent = (
            st.AGENT_ENABLED and self.index == st.AGENT_PLAYER_INDEX
        )

        # OLD (20260716) position-replay prototype -- superseded 20260807 by
        # the contact-memory kernel below (replayed recorded POSITIONS, which
        # just retraced someone's old path; kept for reference, not deleted).
        # self.replay_positions = None
        # self.replay_timestamps = None
        # self.replay_index = 0
        # if self.is_agent:
        #     df = pd.read_csv(st.AGENT_REPLAY_CSV)
        #     self.replay_positions = df["pos1"].tolist()
        #     self.replay_timestamps = df["timestamp"].tolist()

        # --- AGENT: contact-memory kernel, 3 conditions (proposal.md §5.2) ------
        # 20260807 AH, 3rd condition (baseline) added 20260904 AH.
        # All three share ONE mechanism (agent_step() below): a contact-memory
        # V, a threshold-driven explore/engage switch, and x_last_contact to
        # return to. They differ ONLY in the source of c_t, selected by
        # st.AGENT_CONDITION ("baseline" | "non_contingent" | "contingent").
        self.replay_contact = None       # AGENT ("non_contingent" only): recorded c_t sequence (0/1 per row), (re)loaded per trial in init_motion()
        self.replay_timestamps = None    # AGENT ("non_contingent" only): recorded time (s) per row -> time-based lookup
        self.replay_index = 0            # AGENT ("non_contingent" only): how far through the recording we are

        # --- AGENT 20260816: a shuffled pool of "non_contingent" recordings -----
        # Previously a single fixed file was loaded once and replayed
        # identically every trial -- learnable ("regular = machine",
        # lab-notebook.md 2026-08-16). Now init_motion() draws a new file per
        # trial, without replacement, from this shuffled copy of
        # AGENT_REPLAY_CONTACT_POOL (refilled+reshuffled if ever exhausted).
        # Only loaded for "non_contingent" -- "baseline" and "contingent"
        # never touch a recording.
        self._replay_pool: List[str] = []
        if self.is_agent and st.AGENT_CONDITION == "non_contingent":
            self._replay_pool = list(st.AGENT_REPLAY_CONTACT_POOL)
            shuffle(self._replay_pool)

        self.V = 0.0                # AGENT: contact-memory state (resets each trial, see init_motion())
        self.x_last_contact = None  # AGENT: own position when contact last broke
        self._prev_c = 0            # AGENT: last tick's c_t, to detect the falling edge ("contact just broke")
        self._last_debug_t = -999.0  # AGENT: when the V/mode debug line was last logged
        self._explore_direction = 1  # AGENT 20260907: +1/-1, which way explore mode is currently sweeping (resets each trial, see init_motion())
        self._hold_anchor = None  # AGENT 20260915: fixed position "hold" jitters around, set fresh each time a hold begins (resets each trial, see init_motion())
        self._hold_elapsed = 0.0  # AGENT 20260915: seconds spent continuously holding so far (resets each trial, see init_motion())
        self._hold_cooldown_remaining = None  # AGENT 20260915: seconds left forcing explore after a capped hold (resets each trial, see init_motion())

        # --- AGENT 20260816: per-tick traces for the saved trial CSV ------------
        # V/c_t/mode, saved by phase.py's Trial.save() (only for the agent -- see
        # there). Appended once per tick in agent_step(), so length always matches
        # history_x/history_button. None outside a trial, [] during one (see
        # init_motion()/init_nonmotion() below, same pattern as history_x).
        self.V_trace: Optional[List[float]] = None
        self.c_trace: Optional[List[int]] = None
        self.engaging_trace: Optional[List[bool]] = None

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

        # --- AGENT: self-register the agent slot, 20260813 -------------------
        # Nobody opens the web frontend for this slot, but the rest of the
        # system (and the Elm frontend) expects a fully registered player:
        #   - `_pid`  : Trial.save() puts both players' pids in the filenames.
        #   - `person`: PreExperiment gates on it (phase.py).
        #   - `_uuid` : makes the slot read as "occupied", so the frontend does
        #               not offer it as joinable and `can_become_ready` is True.
        # The uuid is generated, never handed to a browser, so no client can
        # ever authenticate as the agent.
        if self.is_agent:
            self._pid = st.AGENT_PID
            self.person = {"agent": True}
            # str(), not a UUID object: everywhere else a uuid comes from the
            # session as a string, and meta_data() is JSON-serialised.
            self._uuid = str(uuid4())

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

    # OLD (20260716) position-replay prototype -- superseded 20260807 (kept
    # for reference, not deleted; see the __init__ comment above).
    # def agent_step(self, elapsed: float) -> None:
    #     if not self.is_agent or self.avatar is None:
    #         return  # no-op for the live human, and before the avatar exists
    #     ts = self.replay_timestamps
    #     while (self.replay_index + 1 < len(ts)
    #            and ts[self.replay_index + 1] <= elapsed):
    #         self.replay_index += 1
    #     i = min(self.replay_index, len(self.replay_positions) - 1)  # clamp to last recorded row
    #     self.avatar.x = self.replay_positions[i]  # place the agent avatar at that recorded position

    # --- AGENT: the contact-memory kernel, 3 conditions. 20260807 AH,
    # 3rd condition (baseline) added 20260904 AH.
    # Called once per TICK from phase.py -> Trial.step(), BEFORE record() /
    # update_feedbacks() for this same tick. `elapsed` is seconds since this
    # trial started; `dt` is seconds since the previous tick (for the
    # dt-aware V update). No-op for the live human.
    #
    # This is the 5-step loop from proposal.md §5.1 addendum (a):
    #   1. am I touching anything right now? -> c_t is 0 or 1
    #   2. update the memory: V <- V + (dt/tau)*(c_t - V)
    #   3. if contact just broke, store where I am -> x_last_contact
    #   4. if V > threshold -> engage; else -> explore
    #   5. move one step
    def agent_step(self, elapsed: float, dt: float) -> None:
        if not self.is_agent or self.avatar is None:
            return  # no-op for the live human, and before the avatar exists

        # --- step 1: am I touching anything right now? -----------------------
        if st.AGENT_CONDITION == "baseline":
            # Condition 1 (added 2026-09-04): contact input permanently
            # disconnected -- c_t fixed at 0 for the entire trial, regardless
            # of what the participant does. V (step 2) only ever decays and
            # never crosses AGENT_V_THRESHOLD, so the agent stays in "explore"
            # for the whole trial (proposal.md §5.2 Condition 1).
            c_t = 0
        elif st.AGENT_CONDITION == "contingent":
            # Condition 3: the agent's own LIVE contact flag, as last set by
            # update_feedbacks() on the PREVIOUS tick (this tick's
            # update_feedbacks() hasn't run yet -- see phase.py Trial.step()).
            # Same ambiguous avatar/shadow/static signal the human has.
            c_t = 1 if self.controller.feedback else 0

            # (static-object trap, known since 2026-08-16 -- see step 3 below
            # for the fix and why the original "only count the OTHER player"
            # approach was reverted.)
        else:
            # Condition 2 (non_contingent -- the only remaining value after
            # "baseline"/"contingent" above, no further check needed). Reads
            # c_t from a recorded 2023 trial, indexed by elapsed TIME (not
            # tick count) since the live loop's rate does not match the
            # recording's ~566 Hz.
            ts = self.replay_timestamps
            while (self.replay_index + 1 < len(ts)
                   and ts[self.replay_index + 1] <= elapsed):
                self.replay_index += 1
            i = min(self.replay_index, len(self.replay_contact) - 1)
            c_t = int(self.replay_contact[i])

        # --- step 2: update the memory ----------------------------------------
        # dt-aware so tau stays in seconds and the agent is rate-independent
        # across Mac/Pi (proposal.md §5.1 addendum (b)). dt is 0.0 on the very
        # first tick of a trial (no previous tick yet) -- skip the update then.
        if dt > 0:
            self.V += (dt / st.AGENT_TAU_SECS) * (c_t - self.V)

        # --- step 3: if contact just broke, store where I am -----------------
        # FIX 2026-09-30 (static-object trap): don't let x_last_contact become
        # the agent's own static object's position -- that's what was causing
        # return -> re-touch static -> break -> return loops. Can't fix this by
        # asking "which object caused the break" (c_t is deliberately merged
        # across avatar/shadow/static, proposal.md §5.4, and the non-contingent
        # replay's c_t has no such distinction to give even if we wanted it --
        # this is why the earlier "only count the OTHER player" fix was
        # reverted, it only worked for the contingent condition). Instead,
        # guard the WRITE using only the agent's own known, fixed static-object
        # position -- this works identically in all 3 conditions.
        if self._prev_c == 1 and c_t == 0:
            width = st.ENV_WIDTH
            dist_to_static = abs((self.static.x - self.avatar.x + width / 2) % width - width / 2)
            if dist_to_static > (st.STATIC_WIDTH + st.AVATAR_WIDTH) / 2:
                self.x_last_contact = self.avatar.x
            # else: leave x_last_contact unchanged -- currently sitting on my
            # own static object, don't let "return" send me back onto it.
        self._prev_c = c_t

        # --- step 4: explore/engage switch ------------------------------------
        engaging = self.V > st.AGENT_V_THRESHOLD

        # --- AGENT 20260816: record this tick's state for the saved trial CSV --
        self.c_trace.append(c_t)
        self.V_trace.append(self.V)
        self.engaging_trace.append(engaging)

        # --- step 5a: decide this tick's movement MODE --------------------------
        # FIXED 2026-09-15: capped-length holds. Bounded jitter (see step 5b)
        # fixed the old "constant crawl" towing bug, but real-hardware testing
        # the same day found a WORSE replacement: since the jittering agent
        # barely moves, a participant can just stand still near it and stay in
        # contact indefinitely ("camping") -- nothing ever forced a hold to
        # end. This adds an actual time cap: after AGENT_MAX_HOLD_SECS of
        # continuous holding, give up and force explore for
        # AGENT_HOLD_COOLDOWN_SECS (ignoring engaging/c_t during the cooldown,
        # so it doesn't just re-enter hold on the very next tick under
        # continued contact) -- both numbers taken from the real 2023 contact/
        # gap rhythm (~0.25s / ~0.5s) already used elsewhere in this file, not
        # from today's exploratory pilot session (see lab-notebook.md 09-15).
        if self._hold_cooldown_remaining is not None:
            self._hold_cooldown_remaining -= dt
            if self._hold_cooldown_remaining <= 0:
                self._hold_cooldown_remaining = None
            mode = "explore"
        elif engaging and c_t == 1:
            self._hold_elapsed += dt
            if self._hold_elapsed > st.AGENT_MAX_HOLD_SECS:
                self._hold_cooldown_remaining = st.AGENT_HOLD_COOLDOWN_SECS
                self._hold_elapsed = 0.0
                mode = "explore"  # give up this tick, straight into cooldown
            else:
                mode = "hold"
        elif engaging and self.x_last_contact is not None:
            mode = "return"
        else:
            mode = "explore"

        # --- step 5b: execute that mode ------------------------------------------
        if mode == "hold":
            # hold: jitter around a fixed anchor, not oscillate (data does not
            # support "probe" -- proposal.md §5.1 addendum (e)) and not a
            # steady crawl (towable -- see step 5a comment above).
            if self._hold_anchor is None:
                self._hold_anchor = self.avatar.x  # first tick of this hold: anchor here
            self.avatar.x = self._hold_anchor + uniform(
                -st.AGENT_HOLD_JITTER, st.AGENT_HOLD_JITTER
            )
        elif mode == "return":
            # return: head back toward where contact last broke (proposal.md
            # §5.1 addendum (f) -- V alone can't do this, needs x_last_contact).
            self._hold_anchor = None
            self._hold_elapsed = 0.0
            self._step_toward(self.x_last_contact, st.AGENT_RETURN_SPEED * dt)
        else:
            # explore: sweep the ring, occasionally reversing direction.
            # PLACEHOLDER 20260907 AH -- memoryless (Poisson-style) reversal:
            # each tick has probability dt/AGENT_EXPLORE_REVERSAL_MEAN_SECS of
            # flipping direction, giving randomized (not perfectly periodic)
            # intervals with that mean -- see settings.py for why this number
            # itself is a placeholder, not yet from the 2023 data.
            self._hold_anchor = None
            self._hold_elapsed = 0.0
            if random() < dt / st.AGENT_EXPLORE_REVERSAL_MEAN_SECS:
                self._explore_direction *= -1
            self.avatar.x += st.AGENT_EXPLORE_SPEED * self._explore_direction * dt

        # --- AGENT 20260813: watch the agent's internal state -----------------
        # The explore/engage switch is hard to SEE: while you chase the agent you
        # match its speed, so its slowdown is invisible from inside its own frame
        # of reference. This prints V and the mode so the state can be read
        # directly instead of inferred from motion. Rate-limited to
        # AGENT_DEBUG_LOG_SECS; set that to 0 to switch the logging off.
        if st.AGENT_DEBUG_LOG_SECS and (
            elapsed - self._last_debug_t >= st.AGENT_DEBUG_LOG_SECS
        ):
            self._last_debug_t = elapsed
            logger.info(
                "AGENT t=%5.1fs  c_t=%d  V=%.3f  %-7s  x=%5.1f  %s",
                elapsed,
                c_t,
                self.V,
                "ENGAGE" if engaging else "explore",
                self.avatar.x,
                "#" * int(self.V * 40),  # quick visual bar for V
            )

    def _step_toward(self, target: float, step_size: float) -> None:
        # AGENT: move at most `step_size` toward `target`, taking the shorter
        # way around the ring (the environment wraps -- see
        # environment.wrap_around / Object.x's setter).
        width = st.ENV_WIDTH
        delta = (target - self.avatar.x + width / 2) % width - width / 2
        if abs(delta) <= step_size:
            self.avatar.x = target
        else:
            self.avatar.x += step_size if delta > 0 else -step_size

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
        # AGENT 20260813: the agent is always ready -- there is nobody to press
        # its button. This is what the EXPERIMENTER VIEW reads (via
        # game.players_data()), so without it the frontend shows "participant 1
        # not ready" and refuses to advance, even though the backend gates in
        # phase.py already skip the agent.
        if self.is_agent:
            return True
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
        self.V = 0.0                # AGENT: contact memory resets every trial (proposal.md §5.1(a))
        self.x_last_contact = None  # AGENT: no stored return-point yet this trial
        self._prev_c = 0            # AGENT: no prior tick this trial
        self._explore_direction = 1  # AGENT 20260907: always start sweeping the same way each trial
        self._hold_anchor = None  # AGENT 20260915: no hold in progress at trial start
        self._hold_elapsed = 0.0  # AGENT 20260915: no hold in progress at trial start
        self._hold_cooldown_remaining = None  # AGENT 20260915: no cooldown in progress at trial start

        # --- AGENT 20260816: draw this trial's "non_contingent" recording -------
        # A fresh file per trial, without replacement (see the __init__
        # comment on _replay_pool for why). "baseline" and "contingent" never
        # load a recording (baseline's c_t is a fixed 0, contingent's is live).
        if self.is_agent and st.AGENT_CONDITION == "non_contingent":
            if not self._replay_pool:
                self._replay_pool = list(st.AGENT_REPLAY_CONTACT_POOL)
                shuffle(self._replay_pool)
            replay_csv = self._replay_pool.pop()
            # AGENT 20261007: log WHICH recording this trial drew. Until now the
            # filename was used to open the file and then discarded -- engine.log
            # printed the pool, never the draw -- so a non_contingent trial's c_t
            # could not be traced back to its 2023 source and the condition was
            # not reproducible (found in the 20261005 pilot QC). This line comes
            # immediately after phase.py's "Trial: agent condition = ...
            # (trial_index=N)", so the pairing is unambiguous in the log.
            logger.info("AGENT: non_contingent replay draw = %s", replay_csv)
            df = pd.read_csv(replay_csv)
            contact_col = f"motor_{st.AGENT_PLAYER_INDEX}_vibrate_software"
            self.replay_contact = df[contact_col].tolist()
            self.replay_timestamps = df["timestamp"].tolist()

        # --- AGENT 20260816: fresh per-tick traces for this trial ---------------
        self.V_trace = []
        self.c_trace = []
        self.engaging_trace = []

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

        self.V_trace = None
        self.c_trace = None
        self.engaging_trace = None

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
