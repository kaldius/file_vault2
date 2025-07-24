FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        gcc \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Expose port
EXPOSE 8000

# Create a script to wait for database and run migrations
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Set Django settings module\n\
export DJANGO_SETTINGS_MODULE=file_vault.settings\n\
\n\
# Wait for database to be ready\n\
echo "Waiting for database..."\n\
while ! python -c "import os; os.environ.setdefault(\"DJANGO_SETTINGS_MODULE\", \"file_vault.settings\"); import django; django.setup(); from django.db import connection; connection.ensure_connection()"; do\n\
  echo "Database not ready, waiting..."\n\
  sleep 2\n\
done\n\
\n\
echo "Database is ready!"\n\
python manage.py migrate\n\
python manage.py runserver 0.0.0.0:8000\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run the start script
CMD ["/app/start.sh"] 