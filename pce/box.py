import logging

from gpiozero import Button, DigitalOutputDevice  # type: ignore

from pce import settings as st

logger = logging.getLogger(__name__)


class Signaller:
    def __init__(self, pin_trial, pin_standby):
        self._trial = DigitalOutputDevice(pin_trial)
        self._standby = DigitalOutputDevice(pin_standby)

    def trial(self):
        self._trial.blink(on_time=st.SIGNAL_DURATION_SECS, n=1)

    def standby(self):
        self._standby.blink(on_time=st.SIGNAL_DURATION_SECS, n=1)


class ModalitySwitch:
    def __init__(self, pin_sound_on, pin_vibration_on):
        self._sound_only = Button(pin_sound_on, bounce_time=0.01)
        self._vibration_only = Button(pin_vibration_on, bounce_time=0.01)

        self._sound_only.when_activated = self.log_state
        self._sound_only.when_deactivated = self.log_state
        self._vibration_only.when_activated = self.log_state
        self._vibration_only.when_deactivated = self.log_state

    def log_state(self):
        logger.info("sound is %s, vibration is %s", self.sound, self.vibration)

    @property
    def sound(self):
        return bool(self._sound_only.is_pressed) or not bool(
            self._vibration_only.is_pressed
        )

    @property
    def vibration(self):
        return bool(self._vibration_only.is_pressed) or not bool(
            self._sound_only.is_pressed
        )


class Box:
    def __init__(self):
        self.signal = Signaller(st.PIN_SIGNAL_TRIAL, st.PIN_SIGNAL_STANDBY)
        self.modality = ModalitySwitch(
            st.PIN_MODALITY_SOUND_ONLY, st.PIN_MODALITY_VIBRATION_ONLY
        )
