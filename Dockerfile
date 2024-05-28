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

# Specify the command to run on container start
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]