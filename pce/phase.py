import asyncio
import logging
import os
from contextlib import contextmanager
from random import randint
from typing import List

import pandas  # type: ignore
from scipy import ones_like  # type: ignore

from pce import server
from pce import settings as st
from pce.environment import overlaps
from pce.utils import (camel_to_snake, create_task, px_true, run_at_rate,
                       save_csv)

logger = logging.getLogger(__name__)


class Phase:
    training_types = [None, "visible", "hidden"]

    def __init__(self, index, game, webapp, **kwargs):
        # kwargs so far unused, but they may bubble up from sub-classes
        self.index = index
        self.game = game
        self.webapp = webapp
        self.box = game.box
        self.players = game.players

        self.history_motor_0 = [] #Shows that motor is on
        self.history_motor_1 = [] #Shows that motor is on

    def controllers_broadcast(self, schedule):
        return asyncio.gather(*[p.controller.blink(schedule) for p in self.players])

    @property
    def done(self):
        raise NotImplementedError

    def event(self):
        return {"tipe": server.OutEvents.phase, "data": self.event_data()}

    def event_data(self):
        raise NotImplementedError

    def handle_questionnaire(self, player, qtype, answers):
        if qtype in self.player_qtypes:
            self.handle_player_questionnaire(player, qtype, answers)
        elif qtype in self.trial_qtypes:
            self.handle_trial_questionnaire(player, qtype, answers)
        else:
            raise ValueError(f"{qtype} is not part of known questionnaires")

    def handle_trial_questionnaire(self, player, qtype, answers):
        assert qtype in self.trial_qtypes
        getattr(self, f"handle_trial_{qtype}")(player, answers)

    def handle_player_questionnaire(self, player, qtype, answers):
        assert qtype in self.player_qtypes
        assert getattr(player, qtype) is None
        setattr(player, qtype, answers)

        filepath = os.path.join(
            self.game.trials_dir,
            f"{self.game.file_prefix}_DATA=player-questionnaires_P{player.index}={player.pid}.csv",
        )
        logger.info(
            "%s: saving %s questionnaire for %s to %s",
            type(self).__name__,
            qtype,
            player,
            filepath,
        )

        for answer in answers:
            assert (
                "questionnaire" not in answer
            ), "Answer already has a 'questionnaire' field"
            answer["questionnaire"] = qtype

        save_csv(
            filepath,
            ["questionnaire", "question_id", "question_text", "answer"],
            answers,
        )

    def serve_players(self):
        server.ws_broadcast(self.webapp["ws_clients"], self.game.players_event())

    def start(self):
        logger.info("Phase: start")

        # Clear button presses before starting tasks, and broadcast to ws clients
        logger.debug("Phase: players init_nonmotion")
        for p in self.players:
            p.init_nonmotion()
        logger.debug("Phase: send players event to ws clients")
        server.ws_broadcast(self.webapp["ws_clients"], self.game.players_event())

        # Start tasks for the phase, and broadcast to ws clients
        self.start_tasks()
        logger.debug("Phase: send phase event to ws clients")
        server.ws_broadcast(self.webapp["ws_clients"], self.event())

        logger.debug("Phase: started")

    def start_tasks(self):
        raise NotImplementedError

    def cleanup(self):
        logger.info("Phase: cleanup")
        self.cleanup_tasks()
        # Clear button presses
        for p in self.players:
            p.init_nonmotion()

    def cleanup_tasks(self):
        raise NotImplementedError

    def can_become_ready(self, player):
        raise NotImplementedError

    @property
    def next_phase(self):
        if self.index == len(self.game.sequence) - 1:
            # This is the last phase
            return None
        return self.game.sequence[self.index + 1]

    @property
    def next_phase_cls(self):
        if self.next_phase is None:
            # This is the last phase
            return None
        return self.next_phase[0]

    @property
    def next_phase_props(self):
        if self.next_phase is None:
            # This is the last phase
            return None
        return self.next_phase[1]

    def move_next_phase(self, **kwargs):
        logger.info("Phase: move_next_phase")
        if not self.done:
            raise ValueError("next_phase() called but self.done is False")
        self.game.phase = new_phase(self.index + 1, self.game, self.webapp, **kwargs)
        self.cleanup()
        self.game.phase.start()
        return self.game.phase


def new_phase(index, game, webapp, **kwargs) -> Phase:
    new_cls, sequence_kwargs = game.sequence[index]
    logger.debug("new_phase: sequence_kwargs = %s", sequence_kwargs)
    logger.debug("new_phase: kwargs = %s", kwargs)
    return new_cls(index, game, webapp, **sequence_kwargs, **kwargs)


class PreExperiment(Phase):

    player_qtypes: List[str] = ["person", "personality_pre"]
    trial_qtypes: List[str] = []

    def questionnaires_data(self):
        return {
            "person": {
                "p0": self.players[0].person is not None,
                "p1": self.players[1].person is not None,
            },
            "personality_pre": {
                "p0": self.players[0].personality_pre is not None,
                "p1": self.players[1].personality_pre is not None,
            },
        }

    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
            "questionnaires": self.questionnaires_data(),
            "config": {
                "env_width": st.ENV_WIDTH,
                "avatar_width": st.AVATAR_WIDTH,
                "static_width": st.STATIC_WIDTH,
                "static0": getattr(
                    self.players[0].static, "x", st.STATIC_X[0][0] #st.STATIC_X[0], #MAKING AN ARRAY
                ),
                "static1": getattr(
                    self.players[0].static, "x", st.STATIC_X[0][0] #st.STATIC_X[1], #MAKING AN ARRAY
                ) + 300,
                "shadow_delta0": st.SHADOW_DELTA_RANGE[0],
                "shadow_delta1": st.SHADOW_DELTA_RANGE[0],
                "training": None,
            },
            "personality_questions_limit": st.GLOBAL["PERSONALITY_QUESTIONS_LIMIT"],
        }

    def start_tasks(self):
        logger.info("PreStart: start_tasks")
        #shadow_side = 2 * randint(0, 1) - 1
        shadow_side = 1 #no more switching sides, from Leonardos PI
        for p in self.players:
            p.init_motion(shadow_side)

        def tick():
            for p in self.players:
                # Make sure the button press cache is read
                p.controller.clear_button_press()

        self.serve_players_task = create_task(
            run_at_rate(st.REFRESH_RATE_VISUAL, self.serve_players)
        )
        self.tick_task = create_task(run_at_rate(st.REFRESH_RATE_VISUAL, tick))

    def cleanup_tasks(self):
        logger.info("PreExperiment: cleanup_tasks")
        self.serve_players_task.cancel()
        self.tick_task.cancel()

    def can_become_ready(self, player):
        return False

    @property
    def done(self):
        qdone = all([px_true(q) for q in self.questionnaires_data().values()])
        pidsdone = all([p.pid is not None for p in self.players])
        return pidsdone and qdone


class PreFirstResting(Phase):
    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
        }

    def start_tasks(self):
        logger.info("PreFirstResting: start_tasks")
        self.notify_task = create_task(self.controllers_broadcast_start())

    def cleanup(self):
        logger.info("PreFirstResting: cleanup")
        self.notify_task.cancel()

    def can_become_ready(self, player):
        return True

    @property
    def done(self):
        return all([p.ready for p in self.players])

    async def controllers_broadcast_start(self):
        logger.debug("PreFirstResting: controllers_broadcast_start")
        schedule = [(1, 0, st.AUDIO_FREQ_HIGH)]
        await self.controllers_broadcast(schedule)


class Resting(Phase):
    def __init__(self, *args, **kwargs):
        self._done = False
        super().__init__(*args, **kwargs)

    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
            "duration": st.GLOBAL["DURATION_SECS"]["resting"],
        }

    def start_tasks(self):
        logger.info("Resting: start_tasks")

        async def run():
            self.box.signal.trial()
            await asyncio.sleep(st.GLOBAL["DURATION_SECS"]["resting"])
            self.box.signal.standby()
            self._done = True
            create_task(self.controllers_broadcast_end())
            logger.info("Resting: move to next phase")
            self.move_next_phase()

        self.run_task = create_task(run())

    def cleanup(self):
        logger.info("Resting: cleanup")
        self.run_task.cancel()

    def can_become_ready(self, player):
        return False

    @property
    def done(self):
        return self._done

    async def controllers_broadcast_end(self):
        logger.debug("Resting: controllers_broadcast_end")
        schedule = [
            (0.4, 0, st.AUDIO_FREQ),
            (0.4, 0, int(st.AUDIO_FREQ * 1.5)),
            (0.6, 0.2, st.AUDIO_FREQ_HIGH),
            (0.1, 0, st.AUDIO_FREQ),
        ]
        await self.controllers_broadcast(schedule)


class PreTrials(Phase):
    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
        }

    def start_tasks(self):
        pass

    def cleanup_tasks(self):
        pass

    def can_become_ready(self, player):
        return True

    @property
    def done(self):
        return all([p.ready for p in self.players])


class Trial(Phase):
    def __init__(self, *args, training=None, **kwargs):
        assert training in self.training_types
        self._done = False
        self.training = training
        super().__init__(*args, **kwargs)

    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
            "duration": st.GLOBAL["DURATION_SECS"]["trial"],
            "config": {
                "env_width": st.ENV_WIDTH,
                "avatar_width": st.AVATAR_WIDTH,
                "static_width": st.STATIC_WIDTH,
                "static0": getattr(
                    self.players[0].static, "x", st.STATIC_X[0][0] #st.STATIC_X[0], #MAKING AN ARRAY
                ),
                "static1": getattr(
                    self.players[0].static, "x", st.STATIC_X[0][0] #st.STATIC_X[1], #MAKING AN ARRAY
                ) + 300,
                "shadow_delta0": self.players[0].shadow.delta,
                "shadow_delta1": self.players[1].shadow.delta,
                "training": self.training,
            },
        }

    def start_tasks(self):
        logger.info("Trial: start_tasks")
        #shadow_side = 2 * randint(0, 1) - 1
        shadow_side = 1 #no more switching sides, from Leonardos PI
        for p in self.players:
            p.init_motion(shadow_side)
            p.controller.led_on()
        self.timestamps = []
        trial_duration = st.GLOBAL["DURATION_SECS"]["trial"]

        def step(current_time, start_time):
            # --- AGENT: drive the replay avatar once per tick ----------------
            # This inner step() is the body of the trial loop; it runs every
            # tick. For the replay agent we advance it to its recorded position
            # for the current elapsed time BEFORE record()/update_feedbacks(),
            # so the logged row and the haptic feedback reflect the agent's move
            # on this same tick. agent_step() is a no-op for the live human.
            elapsed = current_time - start_time      # seconds since trial start
            for p in self.players:
                p.agent_step(elapsed)                # AGENT: time-based replay
            self.record(current_time - start_time)
            self.update_feedbacks()

        def cond(current_time, start_time):
            return current_time - start_time < trial_duration

        def end():
            self.box.signal.standby()
            self._done = True
            create_task(self.controllers_broadcast_end())
            for p in self.players:
                p.controller.feedback = False
                p.controller.led_off()

            if not self.training:
                logger.info("Trial: save data")
                self.save()
            else:
                logger.info("Trial: demo or training trial, not saving data")

            logger.info("Trial: move to next phase")
            self.move_next_phase(
                trial_clicks=[sum(p.history_button) != 0 for p in self.players]
            )

        self.serve_players_task = create_task(
            run_at_rate(st.REFRESH_RATE_VISUAL, self.serve_players)
        )
        self.run_task = create_task(
            run_at_rate(
                st.REFRESH_RATE_DATA,
                step,
                cond,
                async_start_f=self.controllers_broadcast_start,
                start_f=self.box.signal.trial,
                end_f=end,
            )
        )

    def cleanup_tasks(self):
        logger.info("Trial: cleanup_tasks")
        self.serve_players_task.cancel()
        self.run_task.cancel()

    def can_become_ready(self, player):
        return False

    @property
    def done(self):
        return self._done

    async def controllers_broadcast_start(self):
        logger.debug("Trial: controllers_broadcast_start")
        await self.controllers_broadcast(
            [(0.1, 0.5, None) for _ in range(3)] + [(1, 0, st.AUDIO_FREQ_HIGH)]
        )
        # FIXME: turn on led here, as the broadcast turns off

    async def controllers_broadcast_end(self):
        logger.debug("Trial: controllers_broadcast_end")
        await self.controllers_broadcast([(1, 0.5, None)])

    def update_feedbacks(self):
        for i in range(len(self.players)):
            p = self.players[i]
            np = self.players[1 - i]
            active = any(
                (
                    overlaps(p.avatar, p.static),
                    overlaps(p.avatar, np.avatar),
                    overlaps(p.avatar, np.shadow),
                )
            )
            # To measure the delay between RPi deciding to start feedback, and
            # feedback actually starting on the buzzer, send a trigger to EEG
            # here, and measure when the buzzer receives a start signal by
            # giving it a direct connection to the EEG system.
            #
            # Maybe create another box.Signaller or two.
            #
            if active and not p.controller.feedback:
             #   self.box.signal.trial()
                if p.index == 0:
                    st.MOTOR_EXCEL_0 = st.MOTOR_ON #Shows that motor is on
                elif p.index == 1:
                    st.MOTOR_EXCEL_1 = st.MOTOR_ON #Shows that motor is on
            if not active and p.controller.feedback:
             #   self.box.signal.standby()
                if p.index == 0:
                    st.MOTOR_EXCEL_0 = st.MOTOR_OFF #Shows that motor is off
                elif p.index == 1:
                    st.MOTOR_EXCEL_1 = st.MOTOR_OFF #Shows that motor is off
            p.controller.feedback = active

    def record(self, timestamp):
        for p in self.players:
            p.record()
        self.timestamps.append(timestamp)
        self.history_motor_0.append(st.MOTOR_EXCEL_0) #Shows that motor is on
        self.history_motor_1.append(st.MOTOR_EXCEL_1) #Shows that motor is on

    def trial_index(self):
        # Our trial_index is equal to the number of non-training trials
        # preceding us in the phase sequence.
        preceding_phases = self.game.sequence[: self.index]
        return sum(
            [
                phase_cls == Trial and not args.get("training")
                for phase_cls, args in preceding_phases
            ]
        )

    def save(self):
        data = pandas.DataFrame({"timestamp": self.timestamps})
        data[f"static_object_0"] = st.OBJ_LOCATION_ZERO #Shows that motor is on
        data[f"static_object_1"] = st.OBJ_LOCATION_ZERO + 300 #Shows that motor is on
        data[f"motor_0_vibrate_software"] = self.history_motor_0 #Shows that motor is on
        data[f"motor_1_vibrate_software"] = self.history_motor_1 #Shows that motor is on
        for p in self.players:
            assert len(data.timestamp) == len(p.history_x)
            data[f"pos{p.index}"] = p.history_x
            assert len(data.timestamp) == len(p.history_button)
            data[f"button{p.index}"] = p.history_button
            data[f"shadow_delta{p.index}"] = ones_like(p.history_x) * p.shadow.delta

        filepath = os.path.join(
            self.game.trials_dir,
            f"{self.game.file_prefix}_DATA=controllers_P0={self.players[0].pid}_P1={self.players[1].pid}_TRIAL={self.trial_index()}.csv",
        )
        logger.info("saving trial data")
        data.to_csv(filepath, index_label="index")
        logger.info(f"trial data saved to '{filepath}'")

        for p in self.players:
            rotary_filepath = os.path.join(
                self.game.log_dir,
                f"{self.game.file_prefix}_DATA=rotary_P{p.index}={p.pid}_TRIAL={self.trial_index()}.csv",
            )
            logger.info("saving rotary timestamp data for %s", p)
            if os.path.exists(rotary_filepath):
                logger.warning(
                    "overwriting rotary timestamp data file %s", rotary_filepath
                )
            with open(rotary_filepath, "w") as f:
                for dt in p.rotary_dts:
                    f.write(f'"{str(dt)}"\n')
            logger.info("rotary timestamp data saved to %s", rotary_filepath)
        st.MOTOR_EXCEL_0 = st.MOTOR_OFF #restarts the excel identifyer after every trial because avatar is teleported off of a motor if ended on an objcet in previous trial
        st.MOTOR_EXCEL_1 = st.MOTOR_OFF


class AfterTrial(Phase):

    player_qtypes: List[str] = []
    trial_qtypes: List[str] = ["experience"]

    def __init__(
        self, *args, trial_clicks: List[bool] = [False, False], training=None, **kwargs
    ):
        assert training in self.training_types
        self.trial_clicks = trial_clicks
        self.experiences = [None, None]
        self.training = training
        super().__init__(*args, **kwargs)

    def questionnaires_data(self):
        return {
            "experience": {
                "p0": self.experiences[0] is not None,
                "p1": self.experiences[1] is not None,
            },
        }

    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
            "training": self.training,
            "next_phase": {
                "type": camel_to_snake(self.next_phase_cls.__name__),
                "training": self.next_phase_props.get("training"),
            },
            "preceding_trial_clicks": {
                "p0": self.trial_clicks[0],
                "p1": self.trial_clicks[1],
            },
            "questionnaires": self.questionnaires_data(),
        }

    def handle_trial_experience(self, player, answers):
        logger.debug("AfterTrial: got experience for %s", player)

        # Check the answer is aligned with the preceding trial's click/no-click
        # situation
        click_presence = [
            a["answer"] for a in answers if a["question_id"] == "click_presence"
        ][0]
        click_confidence = [
            a["answer"] for a in answers if a["question_id"] == "click_confidence"
        ][0]
        if self.trial_clicks[player.index]:
            assert click_presence != 0 and click_confidence != 0, (
                f"player didn't click during the trial "
                "(trial_click = {self.trial_clicks[player.index]}), so click_presence "
                "(= {click_presence}) and click_confidence "
                "(= {click_confidence}) should both be 0"
            )
        else:
            assert click_presence == 0 and click_confidence == 0, (
                f"player clicked during the trial "
                "(trial_click = {self.trial_clicks[player.index]}), so click_presence "
                "(= {click_presence}) and click_confidence "
                "(= {click_confidence}) should NOT be 0"
            )

        # Save answers
        self.experiences[player.index] = answers

        if not self.training:
            trial_index = self.trial_index()
            filepath = os.path.join(
                self.game.trials_dir,
                f"{self.game.file_prefix}_DATA=experience_P{player.index}={player.pid}.csv",
            )
            logger.info("AfterTrial: saving experience questionnaire for %s", player)

            for answer in answers:
                assert "trial_id" not in answer
                answer["trial_id"] = trial_index

            save_csv(
                filepath,
                ["trial_id", "question_id", "question_text", "answer"],
                answers,
            )

        else:
            logger.info("AfterTrial: training trial, not saving data")

        if self.next_phase_cls == Trial and (
            self.training == self.next_phase_props.get("training")
        ):
            # The next phase is again a trial, so player is already ready
            logger.debug(
                "AfterTrial: %s filled questionnaire, next phase is a trial,"
                " and we are not transitioning to a different training state; "
                "so setting player to ready",
                player,
            )
            # FIXME: maybe turn off beep here
            player.longpress_callback()
            logger.debug("AfterTrial: %s is now ready: %s", player, player.ready)

    def start_tasks(self):
        pass

    def cleanup_tasks(self):
        pass

    def trial_index(self):
        # The trial_index of the trial preceding us is equal to the number of
        # non-training trials preceding us in the phase sequence, minus 1.
        preceding_phases = self.game.sequence[: self.index]
        trial_index = (
            sum(
                [
                    phase_cls == Trial and not args.get("training")
                    for phase_cls, args in preceding_phases
                ]
            )
            - 1
        )
        assert trial_index >= 0
        return trial_index

    def can_become_ready(self, player):
        if (not st.TRAINING_TRIAL_HAS_QUESTIONNAIRES) and (self.training is not None):
            # Training trial questionnaires are deactivated, and we're in training mode
            return True
        else:
            return self.experiences[player.index] is not None

    @property
    def done(self):
        qdone = all([px_true(q) for q in self.questionnaires_data().values()])
        if (not st.TRAINING_TRIAL_HAS_QUESTIONNAIRES) and (self.training is not None):
            # Training trial questionnaires are deactivated, and we're in training mode
            return all([p.ready for p in self.players])
        else:
            return qdone and all([p.ready for p in self.players])


class AfterResting(Phase):
    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
        }

    def start_tasks(self):
        pass

    def cleanup_tasks(self):
        pass

    def can_become_ready(self, player):
        return True

    @property
    def done(self):
        return all([p.ready for p in self.players])


class AfterExperiment(Phase):

    player_qtypes: List[str] = ["strategy", "personality_after", "partner_traits"]
    trial_qtypes: List[str] = []

    def questionnaires_data(self):
        return {
            "strategy": {
                "p0": self.players[0].strategy is not None,
                "p1": self.players[1].strategy is not None,
            },
            "personality_after": {
                "p0": (not st.PERSONALITY_QUESTIONS_AFTER) or (self.players[0].personality_after is not None),
                "p1": (not st.PERSONALITY_QUESTIONS_AFTER) or (self.players[1].personality_after is not None),
            },
            "partner_traits": {
                "p0": (not st.PARTNER_TRAITS) or (self.players[0].partner_traits is not None),
                "p1": (not st.PARTNER_TRAITS) or (self.players[1].partner_traits is not None),
            },
        }

    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
            "questionnaires": self.questionnaires_data(),
            "personality_questions_limit": st.GLOBAL["PERSONALITY_QUESTIONS_LIMIT"],
        }

    def start_tasks(self):
        pass

    def cleanup_tasks(self):
        pass

    def can_become_ready(self, player):
        return False

    @property
    def done(self):
        qdone = all([px_true(q) for q in self.questionnaires_data().values()])
        return qdone


class End(Phase):
    def event_data(self):
        return {
            "phase": camel_to_snake(type(self).__name__),
        }

    def start_tasks(self):
        pass

    def cleanup_tasks(self):
        pass

    def can_become_ready(self, player):
        return False

    @property
    def done(self):
        return True
