FROM python:3.12-slim-bullseye

# Set the working directory in the container to /app
WORKDIR /app

# Install system dependencies including curl
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000
EXPOSE 5000

# Run the Uvicorn server when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload", "--port", "5000"]