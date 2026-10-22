release: python backend/manage.py migrate
web: gunicorn --chdir backend config.wsgi --timeout 60 --log-file -
