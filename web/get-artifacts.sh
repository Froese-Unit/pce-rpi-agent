#!/usr/bin/env bash
set -e

SCRIPT="$(readlink -f "$0")"
INITIAL_FOLDER="$(pwd)"

cd "$(dirname "$SCRIPT")"
HASH="$(git rev-parse HEAD)"
REPO="$(git remote -v | grep fetch | awk '{print $2}' | sed 's/^.*gitlab.com[:|\/]//' | sed 's/\.git//')"

mkdir -p assets/translations
printf "\n\nGetting elm.js from current commit artifacts (hash %s)\n\n\n" "$HASH"
wget -O assets/elm.js "https://gitlab.com/$REPO/-/jobs/artifacts/$HASH/raw/web/assets/elm.js?job=build"
printf "\n\nGetting translations from current commit artifacts (hash %s)\n\n\n" "$HASH"
for language in $(ls translations); do
    wget -O assets/translations/$language "https://gitlab.com/$REPO/-/jobs/artifacts/$HASH/raw/web/assets/translations/${language}?job=build"
done
cd "$INITIAL_FOLDER"
