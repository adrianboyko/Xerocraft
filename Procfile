web: gunicorn bzw_ops.wsgi:application --log-file -
worker: python3 bzw_ops/worker.py
release: python3 manage.py migrate
