# Use an official Python runtime as a parent image
FROM python:3.10-slim

RUN pip install --upgrade pip
RUN pip install gunicorn

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org --no-cache-dir -r requirements.txt

COPY . .

CMD "./start.sh"