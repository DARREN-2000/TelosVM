# Use official slim python image for small footprint
FROM python:3.11-slim as builder

# Set env vars for better python behavior
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for security (Senior best practice)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Copy application source code
COPY src/ /app/src/

# Expose the FastAPI port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
