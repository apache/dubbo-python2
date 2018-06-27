#!/usr/bin/env bash

basedir=$(dirname "$0")
cd "${basedir}/.."
echo -e "\033[33m${PWD}\033[0m"

python -m unittest tests.dubbo_test
python -m unittest tests.run_test
