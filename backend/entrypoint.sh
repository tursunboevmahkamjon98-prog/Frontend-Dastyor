#!/bin/sh
# The only thing standing between "git pull && docker compose up -d --build"
# and a database that's missing a column the new code expects to write.
# No step here is optional and no step is a step the user ever has to
# remember to run by hand — see app/db_bootstrap.py for what each of the
# two possible outcomes (stamp vs. upgrade) actually does.
set -e

python -m app.db_bootstrap

exec "$@"
