import asyncio
from typing import List

from gpiozero import PWMLED, Button, RotaryEncoder, TonalBuzzer  # type: ignore

from pce import settings as st
from pce.utils import create_task

class Controller:
    pins_keys = set(["rotaryA", "rotaryB", "button", "buzzer", "audio", "led"])

    def __init__(self, index, box, rotary_callback, longpress_callback):
        pins = st.PINS_CONTROLLERS[index]
        assert set(pins.keys()) == self.pins_keys
        self.box = box

        self.rotary = RotaryEncoder(
            pins["rotaryA"], pins["rotaryB"], max_steps=st.ROTARY_MAX_STEPS, wrap=True
        )

        # NOTE: maybe directly use the RotaryEncoder.steps variable?
        self.rotary.when_rotated_clockwise = lambda: rotary_callback(1)
        self.rotary.when_rotated_counter_clockwise = lambda: rotary_callback(-1)
        # NOTE: if problems, maybe use a bounce time
        self.clear_button_press()
        self.button = Button(
            pins["button"],
            hold_time=st.READINESS_PRESS_DURATION_SECS,
            bounce_time=0.005,
        )
        self.button.when_held = longpress_callback
        self.button.when_pressed = self.log_button_press

        self.led = PWMLED(pins["led"])
        self.audio = TonalBuzzer(pins["audio"])
        self.buzzer = TonalBuzzer(pins["buzzer"])
        self._feedback = False


    def clear_button_press(self):
        self._button_was_pressed = False

    def log_button_press(self):
        self._button_was_pressed = True

    @property
    def button_pressed(self):
        return self.button.is_pressed or self._button_was_pressed

    def clear_button_pressed_memory(self):
        self.button_pressed_memory = False

    def record_button_press(self, history: List[int]):
        # Get press status and reset immediately
        button_pressed = self.button_pressed
        self.clear_button_press()
        # Save to live button_pressed_memory if button was pressed just now
        self.button_pressed_memory = self.button_pressed_memory or button_pressed
        # Record same information to history
        history.append(int(button_pressed))


    async def blink(self, schedule):
        for on_time, off_time, frequency in schedule:
            self.beep_on(frequency=frequency or st.AUDIO_FREQ)
            self.led_on()
            await asyncio.sleep(on_time)
            self.beep_off()
            self.led_off()
            await asyncio.sleep(off_time)

    def beep_on(self, frequency=st.AUDIO_FREQ):
        self.audio.play(frequency)

    def beep_off(self):
        self.audio.stop()

    def short_beep(self, loop=None) -> None:
        async def beep():
            self.beep_on()
            await asyncio.sleep(st.SHORT_BEEP_SECS)
            self.beep_off()

        create_task(beep(), loop=loop)

    def buzz_on(self):
        self.buzzer.play(st.BUZZER_FREQ)

    def buzz_off(self):
        self.buzzer.stop()

    def led_on(self, value=1):
        self.led.value = value

    def led_off(self):
        self.led.off()

    @property
    def feedback(self):
        return self._feedback

    @feedback.setter
    def feedback(self, active):
        # TODO: see if we can replace the "feedback_on" variable by checking on the actual output variables
        if active:
            if self._feedback:
                return  # already on
            if self.box.modality.sound:
                self.beep_on(frequency=st.AUDIO_FREQ_HIGH)
            if self.box.modality.vibration:
                self.buzz_on()
            self._feedback = True
        else:
            if not self._feedback:
                return  # already off
            self.beep_off()
            self.buzz_off()
            self._feedback = False
