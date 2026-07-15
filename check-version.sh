#!/usr/bin/env bash

HOSTNAME="$(hostname)"
# git branch --show-current is only available with git 2.22.0+, not available on Debian 10
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

echo "Checking PCE RPi branch version against hostname"
echo "Current git branch is '$BRANCH'"
echo

# if test "$BRANCH" = "$HOSTNAME"
# then
#     echo -e "\e[32mCurrent git branch name equals the hostname\e[0m"
# else
#     echo -e "\e[31mCurrent git branch differs from hostname ($HOSTNAME)\e[0m"
#     echo -e "\e[31mDon't run any experiment!\e[0m"
#     exit 1
# fi

echo
echo "Pulling git branch to latest version"
echo
git pull --force
status=$?
echo
if test $status -ne 0
then
    echo -e "\e[31mError pulling git branch to lastest version\e[0m"
    echo -e "\e[31mDon't run any experiment!\e[0m"
    exit 1
fi

echo
echo "Getting latest web page artifact"
echo
web/get-artifacts.sh
status=$?
echo
if test $status -ne 0
then
    echo -e "\e[31mError getting latest web page artifact\e[0m"
    echo -e "\e[31mDon't run any experiment!\e[0m"
    exit 1
fi

echo -e "\e[32mAll good, you can move to the next steps in the checklist\e[0m"
