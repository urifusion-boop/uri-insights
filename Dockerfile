# Stage 1: Build the application
FROM python:3.13.0-bullseye AS build

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create and set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Stage 2: Production container
FROM python:3.13.0-bullseye AS production

# Create and set the working directory
WORKDIR /app

# Install Uvicorn directly in the production image
RUN pip install uvicorn

# Copy the Python environment and application code from the build stage
COPY --from=build /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=build /app /app

# Expose ports for the application
EXPOSE 80
EXPOSE 443

# Copy the Google service account JSON file
COPY --from=build /app/app/uri-creative-805581062eaa.json /app/app/uri-creative-805581062eaa.json

# Set environment variables
# ENV SSL_CERT_PATH=/https/fullchain.pem \
#     SSL_KEY_PATH=/https/privkey.pem \
#     GOOGLE_APPLICATION_CREDENTIALS=/app/uri-creative-805581062eaa.json \
#     ENV=Production

# Set the entrypoint to run the FastAPI application with Uvicorn and SSL
CMD ["python", "app/main.py"]
