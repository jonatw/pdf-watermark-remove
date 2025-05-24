# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the web server port (Flask default: 5566)
EXPOSE 5566

# Define mountable directories
VOLUME ["/app/data"]

# Run server.py when the container launches
CMD ["python", "server.py"]
