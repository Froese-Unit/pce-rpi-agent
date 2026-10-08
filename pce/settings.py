# settings.py is the experiment's tunable parameters. Every other file in pce/ does
# `from pce import settings as st` and reads values off it (e.g. st.AGENT_TAU_SECS, st.ENV_WIDTH).
# This script defines numbers/strings/switches that main.py, 
# phase.py, player.py, game.py etc. all read from.

# This script is kind of like a control panel. If you want
# to change how long a trial lasts, which agent condition runs, how fast the
# agent moves, how big the ring is, etc., you change a value here rather than
# editing the logic in phase.py/player.py.

import glob  # AGENT 20260816: for AGENT_REPLAY_CONTACT_POOL below

# REFRESH RATES
REFRESH_RATE_DATA = 1000 #Frequency Changes go here, 100 is original, 10 made the motor skip - too low
REFRESH_RATE_VISUAL = 15

# GLOBAL SETTINGS
EXPERIMENT = {
    # PSYCHOPHYSICS 20261007: 36 main trials in 3 blocks (12 per condition,
    # was [6, 6, 6] = 18). Affordable because trials now end on the click
    # rather than running the full duration -- see TRIAL_ENDS_ON_CLICK below.
    "NUM_TRIALS": [12, 12, 12],
    # 20260721 AH: resting shortened for testing (3 min was too long). The frontend needs the
    # resting phase to exist, so we keep it but use a short duration. Swap back to 3*60 for real runs.
    # PSYCHOPHYSICS 20261007: "trial" 60 -> 30. This is now a CAP, not a
    # duration: it is how long a trial runs if the participant never clicks.
    # 30 s sits just past the 2023 median first click (29.9 s), which was
    # measured without a click-ends-trial rule, so most trials should end on a
    # decision rather than on the cap.
    "DURATION_SECS": {"trial": 30, "resting": 3}, #quick testing (original was "resting": 3 * 60)
    #"DURATION_SECS": {"trial": 60, "resting": 3 * 60}, #original
    #"PERSONALITY_QUESTIONS_LIMIT": 2, #quick testing
    "PERSONALITY_QUESTIONS_LIMIT": None, #original
}
TEST = {
    "NUM_TRIALS": [2, 2],
    # "trial" setting is set over CLI argument
    "DURATION_SECS": {"resting": 3},
    "PERSONALITY_QUESTIONS_LIMIT": 2,
}
LANGUAGE = "en"
PERSONALITY_QUESTIONS_LIMIT = None
# PERSONALITY_QUESTIONS_LIMIT = 3
# 20260904 AH: This PCE-agent project doesn't use the Big-5/personality or partner-traits
# questionnaires (the pre-experiment one is already separately hardcoded off
# in phase.py's PreExperiment.questionnaires_data(), 20260721). These 3
# switches turn off the rest: the per-trial "experience"/PAS questionnaire
# during PRACTICE trials only (main trials are unaffected: PAS still runs
# after every main trial, see phase.py AfterTrial.can_become_ready/done),
# the post-experiment personality questionnaire, and the post-experiment
# partner-traits questionnaire.
TRAINING_TRIAL_HAS_QUESTIONNAIRES = False
PERSONALITY_QUESTIONS_AFTER = False
PARTNER_TRAITS = False
NUM_TRAINING_TRIALS = {
    "visible": 2,
    "hidden": 1,
}

# --- PSYCHOPHYSICS 20261007: trial ends on the participant's click ----------
# The 2023 design (and pce-rpi `main`) runs every trial for its full duration
# regardless of the button, so the PAS rating lands up to 30 s after the
# decision it is meant to be about -- a retrospective rating, not a clean test
# of H2 (lab-notebook.md 2026-10-03, "Design question"). On this branch the
# trial ends at the click instead, psychophysics-style, so rating follows
# decision immediately and more trials fit in the same session.
#
# DURATION_SECS["trial"] above becomes the CAP: what happens when no click
# comes. It must stay finite -- 11% of 2023 participant-trials had no click at
# all, and those trials would otherwise never end.
TRIAL_ENDS_ON_CLICK = True

# How long the button must be held continuously before it counts as a click.
# 0 = end on the first registered press, which is the right default:
#
#   - Bounce is already handled in hardware. controller.py builds the Button
#     with bounce_time=0.005, so gpiozero filters noise before we see it; a
#     second threshold here guards against nothing.
#   - A non-zero value CANNOT be satisfied under --tui. The TUI's button
#     (game.py action_press) calls log_button_press(), which sets a flag that
#     record_button_press() reads and clears, so the button reads as pressed
#     for exactly ONE tick. Requiring a continuous hold made the trial
#     unendable on the keyboard -- found 20261007 running the variant on
#     mockpins.
#
# Raise it only if real sessions show accidental brushes ending trials, and
# remember that doing so disables click-to-end on the TUI.
TRIAL_END_MIN_PRESS_SECS = 0.0

# Seconds to keep running after the click is registered, before ending.
# 0.9 s (20261008): ending dead on the press leaves no post-decision data at
# all, so every trial's last sample IS the decision and there is nothing to
# check it against -- no way to see what the agent did next, and no margin if
# the press timestamp is off by a sample. Half a second is enough to be
# analysable without being long enough to feel like the trial continues.
# The cap still applies, so this can never extend a trial past its maximum.
TRIAL_END_POST_CLICK_SECS = 0.9
LOGGING_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# INPUT/OUPUT SETTINGS
MOTOR_EXCEL_0 = 0
MOTOR_EXCEL_1 = 0
MOTOR_ON = 1
MOTOR_OFF = 0
DATA_PATH = "data"
WEBVIZ_PATH = "web"
BUZZER_FREQ = 220
AUDIO_FREQ = 300
AUDIO_FREQ_HIGH = 600
LED_PULSE_SLOW_FREQ = 1 / 6
SHORT_BEEP_SECS = 0.1
# FIXME: if ROTARY_INCREMENT is large (>= .1), moving fast over a buzz point leads to no buzz,
# i.e. the buzz goes on then off too fast to be turned on by the runtime, or too fast to properly
# start vibrating. Solutions are:
# - reducing ROTARY_INCREMENT
# - increasing the size of objects (these two can be computed, given the maximum
#   rotation speed people can reach)
# - always buzz for a minimum time (the duration needed to start resonance), even if the
#   activation period is shorter than a time step (probably the best option)
ROTARY_INCREMENT = .46875 #0.07 # 600 / 1280 = 1:1, one rotation on screen is 600, device is 1280, not 1024. #Push/Pull Test
ROTARY_MAX_STEPS = 500
READINESS_PRESS_DURATION_SECS = 1

# 20260813 AH -- KEYBOARD TESTING ONLY (--tui with --mockpins), no effect on the
# real rotary encoder. Rotary ticks applied per keyboard press in game.py's
# Tui.action_move(). At the original 10, one press = 4.7 units, so a ~15/s key
# repeat gives ~70 units/s vs. the agent's AGENT_EXPLORE_SPEED of 280, you can
# never keep up, never hold contact, and the agent never engages. 40 gives
# ~18.8 units/press (~280 units/s at 15 presses/s), i.e. parity with the agent.
TUI_MOVE_TICKS = 40

# PIN SETTINGS
PINS_CONTROLLERS = (
    {"rotaryA": 21, "rotaryB": 20, "button": 16, "buzzer": 12, "audio": 19, "led": 26},
    {"rotaryA": 25, "rotaryB": 24, "button": 23, "buzzer": 18, "audio": 5, "led": 6},
)
PIN_SIGNAL_TRIAL = 3  # Pulled down
PIN_SIGNAL_STANDBY = 2  # Pulled down
SIGNAL_DURATION_SECS = 0.01
# This pin is the one grounded by the sound icon side of the switch. Pulled-up.
PIN_MODALITY_VIBRATION_ONLY = 17
# This pin is the one grounded by the vibration icon side of the switch. Pulled-up.
PIN_MODALITY_SOUND_ONLY = 4

# ENVIRONMENT SETTINGS
ENV_WIDTH = 600  # WIDTH of the environment

OBJ_LOCATION_ZERO = 0
OBJ_LOCATION_ONE = 0
import random
STATIC_ONE = random.randint(50,250) # creating a variable to decide the starting location of static object number 1
STATIC_TWO = STATIC_ONE + (ENV_WIDTH / 2)

AVATAR_STARTX_RANGES = (
    [0,0],
    [300,300],
    #[-100, 100],
    #[ENV_WIDTH / 2 - 100, ENV_WIDTH / 2 + 100],
)  # ranges for players x starting position
AVATAR_WIDTH = 20 # ratio used 4/.07 = x/.46875 # width/the rotary increment # 4  # width of players (and their ghosts)
STATIC_X = (
    [50,250],
    [350,550],
) #(STATIC_ONE,STATIC_TWO)#setting the objects, and making object 2 180 degrees away#(ENV_WIDTH / 4, 3 * ENV_WIDTH / 4)  # objects x positions
STATIC_WIDTH = 20 # ratio used 4/.07 = x/.46875 # width/the rotary increment # 4  # width of objects
SHADOW_DELTA_RANGE = [150, 150] #[100, 250]  # range of distances between player and shadow


AGENT_ENABLED = True    # master switch: turn the agent on/off for this run
AGENT_PLAYER_INDEX = 1  # which slot is the agent (1 = controller 2 / red avatar; player 0 stays the live human)

# OLD (20260716) position-replay prototype -- superseded 20260807 by the
# contact-memory kernel below; path is also stale after the 07-30 re-import.
# AGENT_REPLAY_CSV = "../../sample-data/pce02230809/trials/DT=2023-08-09_03-33-28_DATA=controllers_P0=9874_P1=8057_TRIAL=0.csv"

# =====================================================================
# THE AGENTS (proposal.md §5.2)
# 3rd condition (baseline) added 20260904 AH
# ---------------------------------------------------------------------
# All three conditions run the SAME mechanism (player.py -> agent_step(),
# the 5-step loop in proposal.md §5.1 addendum (a)): a contact-memory V,
# a threshold-driven explore/engage switch, and x_last_contact to return
# to. They differ ONLY in the SOURCE of c_t (step 1), set by AGENT_CONDITION:
#   - "baseline"       -> Condition 1: c_t fixed at 0 for the whole trial
#     (contact input disconnected; V never rises, agent stays in explore).
#   - "non_contingent" -> Condition 2: c_t read from a recorded 2023 trial
#     (AGENT_REPLAY_CONTACT_POOL below), indexed by elapsed time.
#   - "contingent"     -> Condition 3: c_t is the agent's own LIVE contact
#     flag this tick.
# Movement generation is identical in all three
# (proposal.md §5.2 addendum 2026-07-30).
# =====================================================================
AGENT_CONDITION = "non_contingent"  # "baseline" | "non_contingent" | "contingent"
# Default/fallback only -- used for training/practice trials and whenever a
# specific condition isn't assigned. Each MAIN trial gets its own condition
# instead (main.py generates a randomized, counterbalanced sequence and
# assigns one per trial -- see utils.generate_agent_condition_sequence() and
# phase.py Trial's `condition` kwarg). 20260904 AH.

# Max allowed consecutive main trials with the SAME condition, when main.py
# generates the randomized sequence (proposal.md §5: "constrain against long
# runs of the same condition"). 20260904 AH.
AGENT_CONDITION_MAX_RUN = 2

AGENT_TAU_SECS = 1.5
# Memory length tau, in seconds. Verified against the FULL 2023 dataset (all
# 64 participants, not one trial) in data-simulations/2-Agent_Parameter_
# Justification.ipynb (20260916): real median gap = 0.457s; retention e^(-gap/
# tau) is 16% at tau=0.25s (too short, V collapses every gap) vs. 74% at
# tau=1.5s (comfortable margin). The EWMA FORM (not this value) follows
# serial-choice-history psychophysics literature (proposal.md §5.1:
# jov.arvojournals.org/article.aspx?articleid=2194025, nature.com/articles/
# ncomms14637); 1.5s itself is our own data fit, not from those papers.

# Still an OPEN design question (proposal.md §5.1 addendum (d)). V is an EWMA
# of a 0/1 signal, so its long-run ceiling is roughly the fraction of time in
# contact. Verified across all 64 participants (2-Agent_Parameter_
# Justification.ipynb, 20260916): median 0.321, 25th/75th pct 0.251/0.412 --
# but a 10x spread person to person (0.098 to 0.945), which is the actual
# evidence a single fixed threshold is a known confound, not just a guess
# that it might be. Fixed placeholder for now; revisit via calibration.
AGENT_V_THRESHOLD = 0.15

# Computed as |position change| / |time change| per tick, excluding near-
# stationary ticks. Originally from one trial only (median ~278 units/s,
# 90th pct ~290) -- redone across the FULL dataset, all 64 participants,
# 20260916 (2-Agent_Parameter_Justification.ipynb): median 275.1 units/s
# (barely moved, 280 still holds up) but 90th pct 360.8 (the one-trial
# estimate understated the real spread -- don't cite ~290 as the 90th pct
# figure going forward, use 361).
AGENT_EXPLORE_SPEED = 280      # units/second while sweeping

# 20260907 AH so the explore-mode never changed direction at all
# (constant one-way sweep, so it visibly loops in a circle -- most obvious in
# the baseline condition, which spends 100% of the trial in explore). This is
# a rough placeholder, NOT derived from the 2023 data's real direction-change
# frequency during non-contact stretches.
# Randomized, not a fixed period -- see player.py agent_step() (~line 291), a
# fresh weighted coin-flip every tick, so reversals space out unpredictably
# around this average, not like clockwork.
AGENT_EXPLORE_REVERSAL_MEAN_SECS = 3.0

# OLD (found 2026-08-13, superseded 20260915) -- constant crawl-forward speed
# while "holding". This WAS the towing bug: a participant could match this
# fixed speed and lead the agent around indefinitely -- confirmed on real
# hardware 09-15 (one hold measured at 8.99s vs. the ~0.25s target, 36x too
# long). Replaced by AGENT_HOLD_JITTER below (bounded jitter, no constant
# speed to match) -- see player.py's hold branch.
# AGENT_ENGAGE_SLOWDOWN = 0.3

# How far (+/- units) the agent wobbles around a fixed spot while holding,
# instead of crawling or freezing. Placeholder, not measured from data.
# Both direction and step size are randomized -- see player.py agent_step()
# (~line 274), a fresh uniform(-6, 6) draw every tick, not a fixed pattern.
AGENT_HOLD_JITTER = 6
AGENT_RETURN_SPEED = 280  # units/second while heading back to x_last_contact -- reuses AGENT_EXPLORE_SPEED's real-data-derived value

# Caps how long the agent can linger with you in one hold before giving up
# (AGENT_MAX_HOLD_SECS), and how long it must then explore before it's
# allowed to hold again (AGENT_HOLD_COOLDOWN_SECS). "Cooldown" = a forced
# waiting period after an action, before it's allowed to happen again. Both
# match the real 2023 contact/gap rhythm (~0.25s / ~0.5s), not pilot data.
AGENT_MAX_HOLD_SECS = 0.5       # ~2x the real median contact duration
AGENT_HOLD_COOLDOWN_SECS = 0.5  # matches the real median gap duration

# OLD (single fixed recording) -- superseded 20260816 by AGENT_REPLAY_CONTACT_POOL below.
# AGENT_REPLAY_CONTACT_CSV = "../../sample-data/pce02230809/trials/pair_02_trial_2.csv"

# Real 2023 recordings for the non_contingent condition; a different one drawn
# per trial, no repeats (player.py). Lives inside this repo so `git clone` gets it.
#
# Only trial_2: trial_1 of every 2023 session has a known buzz-recording bug.
#
# Screened 20261007 -- 32 available, 31 used. A recording is excluded if one
# contact takes up more than a third of the trial, which means the person
# stopped searching and sat on something. Only pair_30 does (41 s of a 60 s
# trial; next highest is 18%). Screening and reasoning:
#   0-preliminaries/agent-conditions/20261007-replay-pool-screening.ipynb
AGENT_REPLAY_POOL_EXCLUDE = ["pair_30"]

AGENT_REPLAY_CONTACT_POOL = sorted(
    f for f in glob.glob("sample-data/pce*/trials/pair_*_trial_2.csv")
    if not any(f.endswith(f"{pair}_trial_2.csv") for pair in AGENT_REPLAY_POOL_EXCLUDE)
)

# Fail at startup, not mid-session. A typo in the exclude list above matches
# nothing and silently leaves the recording in the pool; a wrong working
# directory makes the glob empty, which only crashes at the first
# non_contingent trial, with a participant already sitting there.
AGENT_REPLAY_POOL_EXPECTED = 31  # 32 recordings, minus AGENT_REPLAY_POOL_EXCLUDE
assert len(AGENT_REPLAY_CONTACT_POOL) == AGENT_REPLAY_POOL_EXPECTED, (
    f"replay pool is {len(AGENT_REPLAY_CONTACT_POOL)}, expected "
    f"{AGENT_REPLAY_POOL_EXPECTED}. Run from the pce-rpi root, and check the "
    f"names in AGENT_REPLAY_POOL_EXCLUDE = {AGENT_REPLAY_POOL_EXCLUDE}."
)

# How often (seconds) the terminal prints the agent's V/mode while testing.
# Set to 0 to turn off (do this for real data collection).
AGENT_DEBUG_LOG_SECS = 1.0

# Placeholder ID for the agent slot, used only in saved filenames.
AGENT_PID = "AGENT"