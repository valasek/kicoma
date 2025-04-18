

# Stage 1: Base build stage
# Make sure PYTHON_VERSION matches the Python version in .python-version
ARG PYTHON_VERSION=3.13.3
FROM python:$PYTHON_VERSION-slim AS builder

# Set the working directory in docker
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Upgrade pip and install dependencies
RUN pip install --upgrade pip 

# Copy the dependencies file to the working directory
COPY ./requirements/base.txt .
COPY ./requirements/production.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r production.txt

# Stage 2: Production stage
FROM python:$PYTHON_VERSION-slim

# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set runtime variables
ENV WEB_CONCURRENCY=4
ENV PYTHONHASHSEED=random
ENV LANG=en_US.UTF-8

# Set Django environment variables
ENV DJANGO_ALLOWED_HOSTS=kicoma.stanislavvalasek.com
ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV DJANGO_DEBUG=False
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
ENV DATABASE_URL=sqlite:////storage/kicoma.sqlite3
ENV DJANGO_ADMIN_URL=${DJANGO_ADMIN_URL}
ENV MAILGUN_API_KEY=${MAILGUN_API_KEY}
ENV MAILGUN_SMTP_PORT=587
ENV MAILGUN_PUBLIC_KEY=${MAILGUN_PUBLIC_KEY}
ENV MAILGUN_DOMAIN=stanislavvalasek.com
ENV MAILGUN_SMTP_LOGIN=${MAILGUN_SMTP_LOGIN}
ENV MAILGUN_SMTP_SERVER=smtp.mailgun.org
ENV MAILGUN_SMTP_PASSWORD=${MAILGUN_SMTP_PASSWORD}
# ENV FORWARDED_ALLOW_IPS=*
# ENV REDIS_URL=redis://redis:6379/0

# Set the working directory in docker
WORKDIR /app

# Copy the content of the local src directory to the working directory
COPY . .

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Compile traslations
# TODO: remove this from final image, when it will be deployed onto production
# https://stackoverflow.com/questions/52032712/django-cannot-compilemessages-in-alpine
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends gettext
### Generate message files for a desired language
RUN python ./manage.py makemessages -l cs_CZ --ignore=venv/*
 
### After adding translations to the .po files, compile the messages
RUN python manage.py compilemessages

# Collect static files
RUN python manage.py collectstatic --noinput

# Create /storage folder
RUN mkdir -p /storage && chmod 777 /storage

# Run migrations
RUN python manage.py migrate

# Create super users admim/admin
#echo "Creating super user"
# RUN DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin \
# python manage.py createsuperuser --email=admin@admin.com --noinput

# Expose the application port
EXPOSE 8000 

# Start the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
