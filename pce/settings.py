# REFRESH RATES
REFRESH_RATE_DATA = 1000 #Frequency Changes go here, 100 is original, 10 made the motor skip - too low
REFRESH_RATE_VISUAL = 15


# GLOBAL SETTINGS
EXPERIMENT = {
    "NUM_TRIALS": [6, 6, 6],
    #"DURATION_SECS": {"trial": 60, "resting": 3}, #quick testing
    "DURATION_SECS": {"trial": 60, "resting": 3 * 60}, #original
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
TRAINING_TRIAL_HAS_QUESTIONNAIRES = True
PERSONALITY_QUESTIONS_AFTER = True
PARTNER_TRAITS = True
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


# =====================================================================
# NON-CONTINGENT REPLAY AGENT  (Condition 1)                20260716 AH
# ---------------------------------------------------------------------
# Turns one player slot into a "replay agent": instead of a live human on
# the rotary controller, that avatar plays back a REAL participant's
# recorded movements from a 2023 human-human PCE trial. It moves on its
# own and does NOT react to the live participant -> the non-contingent
# baseline (cf. Barone et al. 2020, "human offline").
#
# Recording used below: pair/session pce02230809 (recorded 2023-08-09),
# participants P0=9874 & P1=8057, trial 0. We replay P1's trajectory.
# Playback lives in player.py -> agent_step(); it is driven each tick from
# phase.py -> Trial.step().
#
# NOTE: player.py reads the "pos1" column (i.e. player 1). That is coupled
# to AGENT_PLAYER_INDEX = 1 below. If you ever make player 0 the agent,
# also change the column read in player.py from "pos1" to "pos0".
# =====================================================================
AGENT_ENABLED = True          # master switch: turn the replay agent on/off for this run
AGENT_PLAYER_INDEX = 1        # which slot is the agent: 1 = controller 2 / red avatar (player 0 stays the live human)
AGENT_REPLAY_CSV = "sample_data/pce02230809/trials/DT=2023-08-09_03-33-28_DATA=controllers_P0=9874_P1=8057_TRIAL=0.csv"  # the one 2023 trial to replay