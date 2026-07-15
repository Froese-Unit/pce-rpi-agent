PCE Web visualiser
==================

Setup
-----

- Install [Elm](https://elm-lang.org/) 0.19.1
- Build the web app from inside this `web` folder: `elm make --debug src/Main.elm --output=assets/elm.js`

Usage
-----

Back in the root `pce-rpi` folder (and after following the main `README.md` for setting up dependencies), you can run the full python+web server with mockpins:
``` sh
pipenv run python -m pce.main --mockpins --loglevel=debug --tui test
```

Then open [localhost:8080](http://localhost:8080/).

Development
-----------

After setup and trying out the usage instructions above, you can continuously build the web app upon any changes. From inside the `web` folder, run:
```
inotifywait -m -e close_write -r src | while read line; elm make --debug src/Main.elm --output=assets/elm.js; end
```
