# Use an official Python runtime as a parent image
FROM python:3.11

# Sets the working directory in the docker image
WORKDIR /app

# Copies the requirements.txt into the container
COPY requirements.txt .

# Installs any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copies the rest of your bot application source code from your local machine into the docker image
COPY . .

# Run the bot script when the container launches
CMD ["python", "-u", "main.py"]
