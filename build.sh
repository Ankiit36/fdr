#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput --settings=config.settings.prod
python manage.py migrate --noinput --settings=config.settings.prod
python manage.py seed_demo --settings=config.settings.prod
