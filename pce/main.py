# main.py -- the experiment's entry point. Running `python3 main.py ...` starts here.
#
# What this script does, in order:
#   1. Reads the CLI flags (--mockpins, --tui, --condition, ...) and applies
#      them to settings.py's config (e.g. which agent condition to run).
#   2. Sets up logging and creates this run's data/log folders.
#   3. Wires up the GPIO pins (real, on the Pi -- or faked, via --mockpins).
#   4. Builds the phase sequence (practice -> training -> main trials ->
#      questionnaires -> end) and constructs the Game object that runs it.
#   5. Starts the aiohttp web server so the browser frontend (Elm) can
#      connect, display the ring/avatars live, and send back button presses.
#
# How it fits the whole experiment: this is the ONE script you actually run.
# Everything else in pce/ (settings.py, phase.py, player.py, game.py, ...) is
# imported and orchestrated from here -- main.py itself contains no experiment
# logic (no movement, no agent behavior), it only sets things up and starts
# the loop that phase.py/game.py then drive.

import argparse  # parses the --mockpins/--tui/--condition/etc. CLI flags
import logging  # writes the run's engine.log (and stream) output
import os  # builds/creates the data & log directory paths for this experiment run
from datetime import datetime  # timestamps the experiment folder/file names
from pprint import pformat  # pretty-prints the settings/CLI-args dump into the log
from subprocess import check_output  # reads the current git commit hash, logged for reproducibility

import gpiozero  # type: ignore  # controls the real GPIO pins (rotary encoders, buttons, buzzers) on the Pi
from aiohttp import web  # runs the async web server the Elm frontend talks to
from gpiozero.pins import mock  # type: ignore  # fakes GPIO pins so the experiment runs off the Pi, e.g. on a Mac (--mockpins)

from pce import server  # builds the aiohttp app (websocket + HTTP routes) for the frontend
from pce import settings as st  # experiment-wide config (trial counts, agent settings, pin numbers, ...)
from pce.game import Game  # the top-level object holding the players/environment and the phase sequence
from pce.utils import public_variables  # pulls out settings.py's own config values, for logging them
from pce.utils import generate_agent_condition_sequence  # AGENT 20260904: builds the randomized, counterbalanced per-trial condition sequence

logger = logging.getLogger(__name__)


def configure_logging(loglevel, log_file):
    root = logging.getLogger()
    root.setLevel(getattr(logging, loglevel.upper()))
    # Clean up handlers defined in previous imports
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    fileHandler = logging.FileHandler(log_file)
    fileHandler.setFormatter(logging.Formatter(st.LOGGING_FORMAT))
    root.addHandler(fileHandler)

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(logging.Formatter(st.LOGGING_FORMAT))
    root.addHandler(streamHandler)

    return streamHandler


def main():
    from pce import phase

    # Parse CLI args
    experiment_name_help = "Name of the experiment (where data will be saved)"
    parser = argparse.ArgumentParser(
        description="Main PCE web server and gpio handling."
    )
    parser.add_argument(
        "experiment_name",
        nargs="?",
        type=str,
        help=experiment_name_help,
    )
    parser.add_argument(
        "--test",
        metavar="TRIAL_SECONDS",
        type=int,
        help="Test run with TRIAL_SECONDS seconds for each trial",
    )
    parser.add_argument(
        "--mockpins",
        action="store_true",
        help="Mock GPIO pins to run off the Raspberry Pi",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Activate Text-UI for mocking button pushes",
    )
    # --- AGENT: force every main trial to ONE condition, 20260813 AH.
    # The 3rd condition (baseline) added 20260904 AH. Normally (this flag
    # omitted) main.py assigns each main trial its own condition from a
    # randomized, counterbalanced sequence (see generate_agent_condition_
    # sequence() below) -- this flag overrides that and pins every main
    # trial to the same condition instead, for testing one condition in
    # isolation (e.g. today's mockpins smoke tests).
    parser.add_argument(
        "--condition",
        type=int,
        choices=[1, 2, 3],
        help="Force ALL main trials to one agent condition instead of the "
        "randomized sequence: 1 = baseline (c_t fixed at 0), "
        "2 = non-contingent (replayed c_t), 3 = contingent (live c_t).",
    )
    parser.add_argument("--loglevel", default="info", help="Define logging level")
    args = parser.parse_args()

    while args.experiment_name is None:
        print("\n")
        name = input(f"Please enter the {experiment_name_help.lower()}: ")
        try:
            name.encode("ascii")
        except UnicodeEncodeError:
            print("\nPlease use only ascii characters (e.g. no accents)")
            continue
        if " " in name:
            print("\nPlease don't use any spaces")
            continue
        if len(name) < 3:
            print("\nPlease use at least 3 characters")
            continue
        args.experiment_name = name

    if args.test is None:
        st.GLOBAL = st.EXPERIMENT
    else:
        assert args.test > 0, "'--test' argument should be a positive integer"
        st.GLOBAL = st.TEST
        st.GLOBAL["DURATION_SECS"]["trial"] = args.test

    exp_dt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    exp_dir = os.path.join(st.DATA_PATH, args.experiment_name)
    trials_dir = os.path.join(exp_dir, "trials")
    os.makedirs(trials_dir, exist_ok=True)
    log_dir = os.path.join(exp_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_prefix = f"DT={exp_dt}"
    stream_handler = configure_logging(
        args.loglevel, os.path.join(log_dir, f"{file_prefix}_engine.log")
    )

    # --- AGENT 20260904: build this session's per-trial condition sequence --
    # One condition per MAIN trial (training trials are unaffected, see
    # phase.py Trial). Normally a randomized, counterbalanced sequence
    # (proposal.md §5, "Randomization"); --condition instead forces every
    # main trial to the same one, for isolated testing.
    n_main_trials = sum(st.GLOBAL["NUM_TRIALS"])
    if args.condition is not None:
        agent_condition_sequence = [
            {1: "baseline", 2: "non_contingent", 3: "contingent"}[args.condition]
        ] * n_main_trials
    else:
        agent_condition_sequence = generate_agent_condition_sequence(
            n_main_trials, max_run=st.AGENT_CONDITION_MAX_RUN
        )

    # AGENT 20260813: log the per-trial sequence on its own line, so which
    # conditions a saved session ran under are greppable in its engine.log.
    # 3rd condition (baseline) added 20260904 AH; logs the whole sequence
    # now that condition varies per trial instead of once per run.
    if st.AGENT_ENABLED:
        logger.info(
            "AGENT: player %s, %s main trials, condition sequence = %s, "
            "tau=%ss, V threshold=%s",
            st.AGENT_PLAYER_INDEX,
            n_main_trials,
            agent_condition_sequence,
            st.AGENT_TAU_SECS,
            st.AGENT_V_THRESHOLD,
        )

    # Log settings, arguments and current git commits
    logger.info("Settings: %s", pformat(public_variables(st)))
    logger.info("Cli args: %s", pformat(args))
    logger.info(
        "git revision: %s",
        check_output(["git", "rev-parse", "HEAD"]).strip().decode("ascii"),
    )
    logger.info("Web elm.js sha256 sum: %s", "skipped-dev-mode")
    ## edits 20260715 AH (replaced the check_output(["sha256sum", ...]) call (which fails on macOS) with a placeholder.)
    #logger.info(
    #    "Web elm.js sha256 sum: %s",
    #    check_output(["sha256sum", os.path.join(st.WEBVIZ_PATH, "assets", "elm.js")])
    #    .strip()
    #    .decode("ascii)"),
    #)

    # Set up pin factory
    if args.mockpins:
        gpiozero.Device.pin_factory = mock.MockFactory(pin_class=mock.MockPWMPin)
    else:
        # Use the pigpio pin factory for much  better performance
        gpiozero.Device.pin_factory = gpiozero.pins.pigpio.PiGPIOFactory()

    # --- RESTING PHASES REMOVED 20260813 AH ---------------------------------
    # The resting phases are an eyes-closed EEG baseline; PCE-AI records no EEG,
    # so they only add dead time. The Phase classes themselves are NOT deleted
    # (phase.PreFirstResting / Resting / AfterResting) -- only dropped from the
    # sequence, so restoring them is uncommenting the lines below.
    #
    # Note on the old `[:-1]`: each block appended (Resting, AfterResting), and
    # the slice dropped just the final AfterResting -- so the original sequence
    # ended on a trailing Resting before AfterExperiment. With the resting
    # phases gone there is nothing to trim, hence no slice below.
    #
    # ORIGINAL, kept for reference:
    #     [(phase.PreExperiment, {}),
    #      (phase.PreFirstResting, {}),
    #      (phase.Resting, {}),   # 20260721 AH: shortened via DURATION_SECS["resting"]
    #      (phase.PreTrials, {})]
    #     ... + list(chain(*[[(phase.Trial, {}), (phase.AfterTrial, {})] * ntrials
    #                        + [(phase.Resting, {}), (phase.AfterResting, {})]
    #                        for ntrials in st.GLOBAL["NUM_TRIALS"]]))[:-1]

    # AGENT 20260904: build the main-trial block with each Trial's OWN kwargs
    # dict, one per trial, consuming agent_condition_sequence in order. NOTE:
    # this can't be done with `[(phase.Trial, {})] * ntrials` (as the training
    # blocks below still do) -- list multiplication duplicates the SAME dict
    # object ntrials times, so writing a per-trial "condition" into it would
    # silently overwrite every trial in that block with the last value
    # written, not just one.
    main_trial_block = []
    _conditions_iter = iter(agent_condition_sequence)
    for ntrials in st.GLOBAL["NUM_TRIALS"]:
        for _ in range(ntrials):
            main_trial_block.append((phase.Trial, {"condition": next(_conditions_iter)}))
            main_trial_block.append((phase.AfterTrial, {}))

    sequence = (
        [
            (phase.PreExperiment, {}),
            (phase.PreTrials, {}),
        ]
        + [
            (phase.Trial, {"training": "visible"}),
            (phase.AfterTrial, {"training": "visible"}),
        ] * st.NUM_TRAINING_TRIALS["visible"]
        + [
            (phase.Trial, {"training": "hidden"}),
            (phase.AfterTrial, {"training": "hidden"}),
        ] * st.NUM_TRAINING_TRIALS["hidden"]
        + main_trial_block
        + [(phase.AfterExperiment, {}), (phase.End, {})]
    )

    game = Game(args, sequence, stream_handler, trials_dir, log_dir, file_prefix)
    webapp = server.make_app(game)
    web.run_app(webapp)


if __name__ == "__main__":
    main()
