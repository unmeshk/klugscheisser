FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy the application code
COPY . .

# Set Python path to include src directory
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/src"

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["python", "src/app.py"]