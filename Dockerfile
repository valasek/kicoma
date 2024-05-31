# Use the official Python image from the DockerHub
FROM --platform=linux/amd64 python:3.10.4-slim

# Set the working directory in docker
WORKDIR /app

# Copy the dependencies file to the working directory
COPY ./requirements/base.txt .
COPY ./requirements/local.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r local.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Compile traslations
# TODO: remove this from final image, when it will be deployed onto production
# https://stackoverflow.com/questions/52032712/django-cannot-compilemessages-in-alpine
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends gettext
### Generate message files for a desired language
RUN python ./manage.py makemessages -l cs_CZ --ignore=venv/*
 
### After adding translations to the .po files, compile the messages
RUN python manage.py compilemessages

# Specify the command to run on container start
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]