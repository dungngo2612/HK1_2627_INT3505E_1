#!/bin/sh
set -eu

flask --app product_api:create_app db upgrade
exec gunicorn -c gunicorn.conf.py wsgi:app
