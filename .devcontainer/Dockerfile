# Use the official Python image from the DockerHub
# Make sure PYTHON_VERSION matches the Python version in .python-version
ARG PYTHON_VERSION=3.13.3
FROM python:$PYTHON_VERSION-slim

# Create the dev-user with appropriate permissions
RUN groupadd --gid 1000 dev-user \
    && useradd --uid 1000 --gid 1000 -m dev-user \
    && apt-get update \
    && apt-get install -y sudo \
    && echo dev-user ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/dev-user \
    && chmod 0440 /etc/sudoers.d/dev-user

# Install Ruby and required dependencies
RUN apt-get update && apt-get install -y \
    ruby \
    ruby-dev \
    build-essential \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install Kamal gem
RUN gem install kamal

# Set the working directory in docker
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements/base.txt .
COPY requirements/local.txt .

# Copy uv from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install any dependencies
RUN uv pip install --system --no-cache-dir -r local.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Compile traslations
# TODO: remove this from final image, when it will be deployed onto production
# https://stackoverflow.com/questions/52032712/django-cannot-compilemessages-in-alpine
# RUN apt-get update && apt-get upgrade -y
# RUN apt-get install -y --no-install-recommends gettext
### Generate message files for a desired language
RUN python ./manage.py makemessages -l cs_CZ --ignore=venv/*
 
### After adding translations to the .po files, compile the messages
RUN python manage.py compilemessages

# Specify the command to run on container start
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
COPY .devcontainer/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]