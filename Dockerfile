
FROM python:3.11.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc

# Install Python dependencies
RUN pip3 install -r requirements.txt
RUN pip3 install python-dotenv

# Download spaCy model
RUN python3 -m spacy download en_core_web_sm

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
