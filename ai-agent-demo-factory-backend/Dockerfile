FROM python:3.12-slim-bullseye

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements.txt file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir ensures that pip does not store a cache of downloaded packages
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 5000
EXPOSE 5000

# Run the Uvicorn server when the container launches
# --host 0.0.0.0 makes the server accessible from outside the container
# --port 5000 is the port FastAPI app listens on
# --reload is typically removed in production for performance
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload", "--port", "5000"]

