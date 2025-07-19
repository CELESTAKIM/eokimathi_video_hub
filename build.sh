#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input

# Optional: Install FFmpeg (Render might have it by default, but good to ensure if moviepy has issues)
# apt-get update && apt-get install -y ffmpeg