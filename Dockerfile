FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py registration.py odr_common.py log_an_action.py ./
COPY static/ ./static/
COPY brand/ ./brand/

# No .streamlit/config.toml baked into the image on purpose - see the
# CMD below. static/fonts/ is still needed regardless (the printed
# label PNG loads those .ttf files directly via PIL, unrelated to
# Streamlit's own theme system).

# Cloud Run injects $PORT (defaults to 8080) - the container must listen
# on it, not a hardcoded port.
ENV STREAMLIT_SERVER_HEADLESS=true
EXPOSE 8080

# Secrets mount directly at .streamlit/secrets.toml (its natural path -
# safe now that nothing else needs to live in .streamlit/ in the image).
# An earlier version baked config.toml into that same directory and
# copied the mounted secret in at startup, but every copy approach
# (cp, cat) failed with filesystem errors specific to Cloud Run's
# sandboxed runtime when writing into a directory that pre-existed in
# the built image - confirmed via two separate failed deploys. Theme
# is set via CLI flags instead (an officially supported Streamlit
# config source, same precedence tier as environment variables) so no
# config.toml file is needed at all. Font *faces* (the custom bundled
# IBM Plex Sans / Space Mono) aren't expressible via CLI flags, so the
# on-screen web UI falls back to a default sans-serif font in this
# deployed version - only the on-screen font is affected, not the
# printed label, which uses the bundled fonts directly either way.
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --theme.base=light --theme.primaryColor=#557399 --theme.backgroundColor=#FAF8F4 --theme.secondaryBackgroundColor=#F1EEE8 --theme.textColor=#1A1815"]
