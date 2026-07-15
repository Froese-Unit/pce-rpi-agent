import argparse
import logging
import os
from datetime import datetime
from itertools import chain
from pprint import pformat
from subprocess import check_output

import gpiozero  # type: ignore
from aiohttp import web
from gpiozero.pins import mock  # type: ignore

from pce import server
from pce import settings as st
from pce.game import Game
from pce.utils import public_variables

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

    # Log settings, arguments and current git commits
    logger.info("Settings: %s", pformat(public_variables(st)))
    logger.info("Cli args: %s", pformat(args))
    logger.info(
        "git revision: %s",
        check_output(["git", "rev-parse", "HEAD"]).strip().decode("ascii"),
    )
    logger.info(
        "Web elm.js sha256 sum: %s",
        check_output(["sha256sum", os.path.join(st.WEBVIZ_PATH, "assets", "elm.js")])
        .strip()
        .decode("ascii)"),
    )

    # Set up pin factory
    if args.mockpins:
        gpiozero.Device.pin_factory = mock.MockFactory(pin_class=mock.MockPWMPin)
    else:
        # Use the pigpio pin factory for much  better performance
        gpiozero.Device.pin_factory = gpiozero.pins.pigpio.PiGPIOFactory()

    sequence = (
        [
            (phase.PreExperiment, {}),
            (phase.PreFirstResting, {}),
            (phase.Resting, {}),
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
        + list(
            chain(
                *[
                    [(phase.Trial, {}), (phase.AfterTrial, {})] * ntrials
                    + [(phase.Resting, {}), (phase.AfterResting, {})]
                    for ntrials in st.GLOBAL["NUM_TRIALS"]
                ]
            )
        )[:-1]
        + [(phase.AfterExperiment, {}), (phase.End, {})]
    )

    game = Game(args, sequence, stream_handler, trials_dir, log_dir, file_prefix)
    webapp = server.make_app(game)
    web.run_app(webapp)


if __name__ == "__main__":
    main()
