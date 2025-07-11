# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY rag-pipeline.py .

# Expose the port that Streamlit runs on
EXPOSE 8501

# Set the health check to ensure the container is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Provide a sane default for local testing; Cloud Run will override this
ENV PORT=8501

# Run via shell so that $PORT is expanded
CMD ["sh", "-c", "streamlit run rag-pipeline.py --server.port $PORT --server.enableCORS false"]