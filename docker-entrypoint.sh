#!/bin/bash
set -e

echo "Waiting for MySQL..."
until nc -z db 3306 2>/dev/null; do
  echo "MySQL is unavailable - sleeping"
  sleep 2
done
echo "MySQL started"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser if needed..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    print('Creating admin user...')
    User.objects.create_superuser('admin', 'admin@pixera.com', 'changeme123')
    print('Admin created: admin / changeme123')
else:
    print('Admin user already exists')
END

echo "Starting application..."
exec "$@"
