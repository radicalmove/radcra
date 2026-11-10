#!/bin/sh
set -eu
umask 077
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
exec /home/fldadmin/.venvs/beta-testing-app-20260722T053147Z/bin/python "$root/deploy/scripts/backup-native.py" \
  "$root/server" "$HOME/backups/beta-testing-app"
