#!/usr/bin/env bash
#set -x

inotifywait -m -e close_write -r src translations | while read -r line; do
    elm make --debug src/Main.elm --output=assets/elm.js
    cp -r translations assets/
done
