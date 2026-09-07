#!/usr/bin/env sh
set -eu
docker compose run --rm backend pytest -q
docker compose run --rm prolog swipl -q -s tests/tests.pl -g run_tests -t halt
docker compose run --rm frontend npm test

