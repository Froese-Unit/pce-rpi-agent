# settings.py -- all the experiment's tunable config, in ONE place. Not a
# script you run (no main()) -- every other file in pce/ does
# `from pce import settings as st` and reads values off it (e.g.
# st.AGENT_TAU_SECS, st.ENV_WIDTH). Nothing here executes any experiment
# logic itself; it just defines numbers/strings/switches that main.py,
# phase.py, player.py, game.py etc. all read from.
#
# How it fits the whole experiment: this is the "control panel." If you want
# to change how long a trial lasts, which agent condition runs, how fast the
# agent moves, how big the ring is, etc., you change a value here rather than
# editing the logic in phase.py/player.py.
#
# Roughly top-to-bottom: timing/refresh rates -> global experiment/test
# config (trial counts, training) -> GPIO pin numbers -> the virtual
# environment's geometry (ring width, avatar/object sizes/positions) ->
# the AGENT settings (the block you've been reading through with me --
# condition, tau, threshold, speeds, the 2023 replay pool).
#
# A few module-level side effects live here too (e.g. `import random` +
# `random.randint(...)` at line ~89, used once to help pick a static
# object's starting position) -- these run once, at import time, not
# per-trial.
import glob  # AGENT 20260816: for AGENT_REPLAY_CONTACT_POOL below

# REFRESH RATES
REFRESH_RATE_DATA = 1000 #Frequency Changes go here, 100 is original, 10 made the motor skip - too low
REFRESH_RATE_VISUAL = 15


# GLOBAL SETTINGS
EXPERIMENT = {
    "NUM_TRIALS": [6, 6, 6],
    # 20260721 AH: resting shortened for testing (3 min was too long). The frontend needs the
    # resting phase to exist, so we keep it but use a short duration. Swap back to 3*60 for real runs.
    "DURATION_SECS": {"trial": 60, "resting": 3}, #quick testing (original was "resting": 3 * 60)
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
# 20260904 AH: PCE-AI doesn't use the Big-5/personality or partner-traits
# questionnaires (the pre-experiment one is already separately hardcoded off
# in phase.py's PreExperiment.questionnaires_data(), 20260721). These 3
# switches turn off the rest: the per-trial "experience"/PAS questionnaire
# during PRACTICE trials only (main trials are unaffected -- PAS still runs
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
# - reducing ROTARy_INCREMENT
# - increasing the size of objects (these two can be computed, given the maximum
#   rotation speed people can reach)
# - always buzz for a minimum time (the duration needed to start resonance), even if the
#   activation period is shorter than a time step (probably the best option)
ROTARY_INCREMENT = .46875 #0.07 # 600 / 1280 = 1:1, one rotation on screen is 600, device is 1280, not 1024. #Push/Pull Test
ROTARY_MAX_STEPS = 500
READINESS_PRESS_DURATION_SECS = 1

# 20260813 AH -- KEYBOARD TESTING ONLY (--tui with --mockpins), no effect on the
# real rotary encoder. Rotary ticks applied per arrow-key press in game.py's
# Tui.action_move(). At the original 10, one press = 4.7 units, so a ~15/s key
# repeat gives ~70 units/s vs. the agent's AGENT_EXPLORE_SPEED of 280 -- you can
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
# KERNEL AGENT -- 3 conditions (proposal.md §5.2)   20260807 AH
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
# Movement generation is identical in all three -- equally lifelike by
# construction (proposal.md §5.2 addendum 2026-07-30).
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
# Memory length tau, in seconds. Range 1-2s is set by the data (gaps between
# contacts are ~0.5s, and V must not decay away across a normal gap or the
# agent will flip explore/engage every ~0.75s cycle) -- see proposal.md §5.1
# addendum (c) and lab-notebook.md 2026-07-30/08-03.

# PLACEHOLDER -- the threshold is an OPEN design question, not yet decided
# (proposal.md §5.1 addendum (d); lab-notebook.md 2026-08-07 "still to
# decide"). V's ceiling is only ~0.2-0.4 and is person-specific, so a fixed
# threshold is a known confound, not just a tuning detail. Using a fixed
# placeholder here to get all three conditions running end to end; revisit
# before piloting (calibrate per participant, or normalise V instead).
AGENT_V_THRESHOLD = 0.15

# PLACEHOLDER -- no data yet on explore-mode sweep DIRECTION (still on the
# "still to decide" list). But the SPEED SCALE itself is not arbitrary: it is
# set from real movement in pair_02_trial_2.csv (median |speed| while actually
# moving is ~278 units/s, 90th pct ~290 units/s -- computed 2026-08-07).
# An earlier placeholder of 1.0 units/s was ~300x too slow -- on the
# 600-unit ring that took ~10 minutes per sweep, which is what looked like
# "the agent doesn't move" during both training and real trials (agent_step()
# runs identically in both -- see phase.py/main.py, no training-specific
# branch exists).
AGENT_EXPLORE_SPEED = 280      # units/second while sweeping

# PLACEHOLDER 20260907 AH -- explore-mode never changed direction at all
# (constant one-way sweep, so it visibly loops in a circle -- most obvious in
# the baseline condition, which spends 100% of the trial in explore). This is
# a rough placeholder, NOT derived from the 2023 data's real direction-change
# frequency during non-contact stretches (that analysis hasn't been done yet
# -- discussed 2026-09-07, deferred). Applies identically to all 3 conditions
# (player.py's explore branch has no condition-specific code) -- revisit by
# measuring real reversal timing before piloting, same as AGENT_EXPLORE_SPEED
# itself was derived from real recorded speeds, not guessed.
AGENT_EXPLORE_REVERSAL_MEAN_SECS = 3.0  # average seconds between direction reversals while exploring

# Fraction of AGENT_EXPLORE_SPEED used while "holding" (engaged and touching).
# This value (0.3) lets a participant "tow" the agent by matching its speed --
# found 2026-08-13, still unresolved. Three fixes tried and reverted 08-16
# (0.0 fully stationary -- froze for 20-30s; 0.03 slow crawl -- still an
# obvious steady drift; random jitter -- buggy); see player.py's hold branch.
AGENT_ENGAGE_SLOWDOWN = 0.3    # fraction of AGENT_EXPLORE_SPEED while overlapping ("hold")
AGENT_RETURN_SPEED = 280       # units/second while heading back to x_last_contact

# OLD (single fixed recording) -- superseded 20260816 by AGENT_REPLAY_CONTACT_POOL below.
# AGENT_REPLAY_CONTACT_CSV = "../../sample-data/pce02230809/trials/pair_02_trial_2.csv"

# Pool of 2023 recordings feeding Condition 2 (non-contingent). player.py
# draws a different one per trial, without replacement (see init_motion()),
# instead of always the same file -- the previous behaviour was learnable
# ("regular = machine", lab-notebook.md 2026-08-16).
#
# Only trial_2 of each session is used -- never trial_1: trial 1 of every
# session has the buzz-stuck-on recording bug (module-level MOTOR_EXCEL_0/1
# globals not reset between trials; proposal.md §5.2 addendum 2026-07-30), so
# restricting to trial_2 avoids the bad data by construction rather than
# filtering it out after the fact. One trial_2 file per 2023 session
# (pair_NN_trial_2.csv, NN = 01..32) -- 32 candidates.
AGENT_REPLAY_CONTACT_POOL = sorted(
    glob.glob("../../sample-data/pce*/trials/pair_*_trial_2.csv")
)

# 20260813 AH -- how often (seconds) player.py logs the agent's V and
# explore/engage mode during a trial. The mode switch is otherwise hard to
# observe: while you chase the agent you match its speed, so the slowdown is
# invisible. Set to 0 to turn the logging off (do that for real data collection;
# at 1.0 a 60 s trial adds ~60 lines).
AGENT_DEBUG_LOG_SECS = 1.0

# Placeholder pid for the agent slot, used only in saved filenames
# (e.g. ..._P0=1234_P1=AGENT_TRIAL=0.csv) so agent runs are obvious on disk
# and never collide with a real participant id. The agent has no uuid and
# never registers through the web frontend -- see player.py __init__.
AGENT_PID = "AGENT"