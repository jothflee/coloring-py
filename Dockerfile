# Use an official Python runtime as a parent image
FROM python:3

RUN pip install --upgrade pip

RUN pip install gunicorn
RUN mkdir -p /certs && \
    openssl req -x509 -newkey rsa:4096 -nodes -out /certs/server.pem -keyout /certs/server.key -days 365 -subj "/CN=localhost"
# Set the working directory to /app

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org --no-cache-dir -r requirements.txt

COPY . .

CMD "./start.sh"