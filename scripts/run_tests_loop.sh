#!/usr/bin/env bash
set -e
MAX_RETRIES=${MAX_RETRIES:-10}
SLEEP=${SLEEP:-5}
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
  echo "Run tests (attempt $((COUNT+1))/$MAX_RETRIES)"
  if pytest -q; then
    echo "Tests passed"
    exit 0
  else
    echo "Tests failed — retrying in ${SLEEP}s"
    COUNT=$((COUNT+1))
    sleep $SLEEP
  fi
done
echo "Tests did not pass after $MAX_RETRIES attempts"
exit 1
