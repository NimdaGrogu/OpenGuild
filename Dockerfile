FROM python:3.13
LABEL authors="jonathan angeles"
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the model during the image build process
RUN python -m spacy download en_core_web_sm

COPY src/ ./src

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# --server.address=0.0.0.0 is CRITICAL for Docker networking
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]