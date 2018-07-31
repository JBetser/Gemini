# Use an official Python runtime as a parent image
FROM python:3.6-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

RUN apt-get update
RUN apt-get upgrade
RUN apt-get -y install gcc
RUN apt-get -y install libssl-dev

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r DockerRequirements.txt

RUN python setup.py install

# Make port 80 available to the world outside this container
EXPOSE 80 8080 443

# Define environment variable
ENV NAME World

# Run server when the container launches
CMD ["python", "main.py"]