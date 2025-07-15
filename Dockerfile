# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy modular application code
COPY app/ ./app/
COPY app_modular.py .

# Expose the port that Streamlit runs on
EXPOSE 8501

# Set the health check to ensure the container is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Provide a sane default for local testing; Cloud Run will override this
ENV PORT=8501

# Run via shell so that $PORT is expanded (using modular entry point)
CMD ["sh", "-c", "streamlit run app_modular.py --server.port $PORT --server.enableCORS false"]