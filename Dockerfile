# Base Python image
FROM python:3.12

# Set work directory
WORKDIR /app

# Install system dependencies (optional)
# RUN apt-get update && apt-get install -y --no-install-recommends <packages>

# Copy dependency list first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline code
COPY . .

# Default command 
CMD ["python", "/app/functions/01_master.py"]
