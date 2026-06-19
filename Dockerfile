# Use Python base with Node installed
FROM python:3.12-slim

WORKDIR /app

# Install Node.js for building the frontend
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project
COPY . .

# Build the frontend
RUN cd frontend && npm install && npm run build

# Expose the port
EXPOSE 8000

# Run the backend (it serves the built frontend too)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
