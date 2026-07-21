FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py registration.py odr_common.py ./
COPY pages/ ./pages/
COPY static/ ./static/
COPY brand/ ./brand/
COPY .streamlit/config.toml ./.streamlit/config.toml

# Cloud Run injects $PORT (defaults to 8080) - the container must listen
# on it, not a hardcoded port.
ENV STREAMLIT_SERVER_HEADLESS=true
EXPOSE 8080

CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
