PCE on Raspberry Pi
===================

> **Branch: `psychophysics`** (created 2026-10-07 from `main`)
>
> A variant of the human-agent experiment with a psychophysics-style trial
> structure: **the trial ends when the participant clicks**, instead of always
> running its full duration.
>
> Why: on `main` (and in 2023) the PAS rating lands up to a minute after the
> decision it asks about, which makes it a retrospective rating rather than a
> test of H2 -- see `lab-notebook.md` 2026-10-03, "Design question". Here the
> rating follows the decision immediately, and because trials end early, more
> of them fit in a session.
>
> | | `main` | `psychophysics` |
> |---|---|---|
> | trial ends | always at the full duration | at the click, else at the cap |
> | `NUM_TRIALS` | `[6, 6, 6]` = 18 (6/condition) | `[12, 12, 12]` = 36 (12/condition) |
> | `DURATION_SECS["trial"]` | 60 s, a fixed length | 30 s, a **cap** |
> | saved columns | | adds `trial_ended_on`, `click_secs` |
>
> The three agent conditions, the contact-memory kernel, the geometry and the
> questionnaire schedule are all unchanged -- the PAS still runs after every
> main trial. The knobs are at the end of `pce/settings.py`
> (`TRIAL_ENDS_ON_CLICK`, `TRIAL_END_MIN_PRESS_SECS`,
> `TRIAL_END_POST_CLICK_SECS`); setting `TRIAL_ENDS_ON_CLICK = False` restores
> `main`'s behavior exactly.
>
> This is a `git worktree` of the `pce-rpi` checkout, not a separate clone, so
> both can run side by side. It has no `.venv` of its own -- see below.

Setup
-----

The environment setup is somewhat different between the Raspberry Pi and other machines used for development, which leads to a little mess at this point:

- On the RPi, building scipy and pandas seems to regularly fail, so we rely on several system-level packages
- On Ubuntu x86_64, building scipy and pandas to the same versions as the ones available through Raspbian on RPi also fails, so we use the latest wheels from PyPi
- Finally, Python on the RPi is 3.9, while on an up-to-date Ubuntu it's currently 3.10, and Pipenv doesn't work with different python versions

To manage this there are two Pipfile/Pipfile.lock pairs, one for RPi, and one for Ubuntu on x86_64. (This should be solved using Guix for creating a common dev/prod environment.)

### Web visualiser on both Ubuntu-x86_64 and Raspberry Pi

As a first step, follow the `web/README.md` setup instructions, to make sure the web server is built.

### Python dependencies setup

Then set up Python for your main computer or for Raspberry Pi:

#### On Ubuntu-x86_64

``` sh
ln -s Pipfile-x86_64 Pipfile
pipenv install
```

#### On Raspberry Pi

``` sh
ln -s Pipfile-rpi-bullseye Pipfile
sudo apt install python3-pandas python3-scipy python3-gpiozero python3-pigpio
pipenv --three --site-packages
pipenv install
```

### Running the server on both Ubuntu-x86_64 and Raspberry Pi

``` sh
pipenv run python -m pce.main --mockpins --loglevel=debug --tui <data-folder-name>
```

`<data-folder-name>` can be simply `test` when developing.

Once the shell is running, open [localhost:8080](http://localhost:8080/).

When using mockpins, you can simulate the user controllers with keyboard presses in the shell UI:

- `←` and `→`: move player 0 around the circle
- `↑` and `↓`: move player 1 around the circle
- `0`: short press player 0's button
- `9`: long press player 0's button
- `1`: short press player 1's button
- `2`: long press player 1's button

Formatting
----------

Use `black` and `isort` for formatting all python code. These are well integrated in most editors to format-on-save.
