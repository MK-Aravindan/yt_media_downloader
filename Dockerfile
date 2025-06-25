# Use a lightweight official Python image based on your specified version (3.11)
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system-level dependencies from packages.txt
# This ensures ffmpeg is available for yt-dlp's post-processing
COPY packages.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends \
    $(cat packages.txt | tr '\n' ' ') \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt file first to leverage Docker cache
# If only your app code changes, but requirements don't, Docker won't re-install dependencies.
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
# Ensure main.py and any other necessary project files are included.
COPY . .

# Expose the port that Streamlit runs on (default is 8501)
EXPOSE 8501

# Command to run your Streamlit application
# The --server.port and --server.address options are crucial for deployments
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]