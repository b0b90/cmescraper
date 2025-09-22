# Use Playwright's official base image with Python + browsers preinstalled
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for Cloud Run
EXPOSE 8080

# Use Gunicorn to run the app
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]

