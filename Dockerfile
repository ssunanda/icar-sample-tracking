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

# The Secret Manager volume for secrets.toml is mounted at /secrets (NOT
# directly into .streamlit/) and copied into place here at startup -
# mounting it straight into .streamlit/secrets.toml would make Cloud Run
# replace the whole .streamlit/ directory with the mounted volume,
# silently wiping out the config.toml baked into the image above.
# Uses `cat` rather than `cp` - Cloud Run's secret mount is a symlink
# that can atomically swap targets, which trips cp's "file replaced
# while being copied" safety check (confirmed via a real failed
# deploy); cat has no such guard and just reads+writes the bytes.
CMD ["sh", "-c", "mkdir -p .streamlit && cat /secrets/secrets.toml > .streamlit/secrets.toml && streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
