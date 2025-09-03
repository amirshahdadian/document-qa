FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Configure Streamlit
RUN mkdir -p .streamlit
RUN echo '[server]\nheadless = true\nport = 8501\nenableCORS = false\nenableXsrfProtection = false\n\n[browser]\ngatherUsageStats = false\n\n[logger]\nlevel = "warning"' > .streamlit/config.toml

# Copy application code
COPY app/ ./app/
COPY app.py .

# Create ChromaDB persistence directory
RUN mkdir -p /app/chroma_db

# Set environment variables
ENV PORT=8501
ENV PYTHONPATH=/app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8501

# Run Streamlit application
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.fileWatcherType", "none"]
