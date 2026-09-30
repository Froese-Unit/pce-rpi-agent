# Standalone hardware check -- bypasses ALL game logic (no rotary, no
# overlaps, no phases). Just drives each player's buzzer motor directly off
# PINS_CONTROLLERS, one at a time, so you can physically feel which unit
# responds to which index, independent of everything else.
#
# MUST run on the real Pi (not mockpins -- gpiozero needs real GPIO).
# Usage: ./.venv/bin/python diagnose_buzzers.py
#
# Ctrl+C to stop at any time.

import time

from gpiozero import TonalBuzzer

from pce import settings as st

buzzers = [
    TonalBuzzer(st.PINS_CONTROLLERS[i]["buzzer"]) for i in range(2)
]

print("Starting buzzer hardware check. Ctrl+C to stop.")
try:
    while True:
        for i, buzzer in enumerate(buzzers):
            print(f"Buzzing index {i} (pin {st.PINS_CONTROLLERS[i]['buzzer']}) for 2s...")
            buzzer.play(st.BUZZER_FREQ)
            time.sleep(2)
            buzzer.stop()
            time.sleep(1)
except KeyboardInterrupt:
    for buzzer in buzzers:
        buzzer.stop()
    print("\nStopped.")
