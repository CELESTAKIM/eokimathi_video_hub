# Use an official Python runtime as a parent image
FROM python:3.13-slim-buster

# Install FFmpeg and other build essentials
RUN apt-get update && apt-get install -y ffmpeg libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code to the working directory
COPY . .

# Define environment variable for Django settings (if not already set in Render)
ENV DJANGO_SETTINGS_MODULE=eokimathi_video_hub.settings

# Expose the port your Gunicorn server will listen on
EXPOSE 8000

# Run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "eokimathi_video_hub.wsgi:application"]