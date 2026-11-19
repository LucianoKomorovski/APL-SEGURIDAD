#!/usr/bin/env bash
set -euo pipefail
# Free no ofrece pre-deploy ni shell. Una sola instancia, migraciones antes de servir.
python backend/manage.py migrate --noinput
exec gunicorn --chdir backend sgca_backend.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 2 --timeout 60 --access-logfile -
