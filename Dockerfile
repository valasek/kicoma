# Stage 1: Base build stage
ARG PYTHON_VERSION=3.13.7
FROM python:$PYTHON_VERSION-slim-bookworm AS builder

WORKDIR /app

# Copy uv from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy the dependencies file to the working directory
# COPY ./requirements/base.txt .
# COPY ./requirements/production.txt .

# Copy the pyproject.toml and README.md files to the working directory
COPY pyproject.toml README.md ./

# Install any dependencies
# RUN uv pip install --system --no-cache-dir -r production.txt

# Install dependencies using uv (creates .venv but that's fine in Docker)
RUN uv sync --extra prod --no-cache --no-install-project

# Make the virtual environment the default Python environment
ENV PATH="/app/.venv/bin:$PATH"


# Stage 2: Production stage
FROM python:$PYTHON_VERSION-slim

# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Install locale dependencies
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        gettext \
        locales && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    sed -i '/cs_CZ.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set locale environment variables
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

# Set environment variables
ENV WEB_CONCURRENCY=4
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Set Django environment variables
ENV DJANGO_ALLOWED_HOSTS=kicoma.stanislavvalasek.com
ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV DJANGO_DEBUG=False
ENV DATABASE_URL=sqlite:////storage/kicoma.sqlite3
ENV MAILGUN_DOMAIN=stanislavvalasek.com
ENV MAILGUN_SMTP_PORT=587
ENV MAILGUN_SMTP_SERVER=smtp.mailgun.org

# Set dummy build-time environment variables due to need to compile messages at build time
ENV DJANGO_SECRET_KEY=dummy-build-key-not-used-in-production
ENV DJANGO_ADMIN_URL=admin/
ENV MAILGUN_API_KEY=dummy-key
ENV MAILGUN_PUBLIC_KEY=dummy-key
ENV MAILGUN_SMTP_LOGIN=dummy-login
ENV MAILGUN_SMTP_PASSWORD=dummy-password

# Set the working directory
WORKDIR /app

# Copy the application code
COPY . .

# Create /storage folder
RUN mkdir -p /storage && chmod 777 /storage

# Generate and compile messages at build time
RUN python ./manage.py makemessages -l cs --ignore=.venv
RUN python ./manage.py makemessages -l en --ignore=.venv
RUN python manage.py compilemessages --ignore=.venv

# Collect static files at build time
RUN python manage.py collectstatic --noinput

# Expose the application port
EXPOSE 8000 

# Simple entrypoint that just runs migrations and starts the server
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
