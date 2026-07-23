"""
DELIMIT Sample Registration - entry point
------------------------------------------
This is the file Streamlit Cloud (and `streamlit run app.py` locally)
actually runs. It gates access behind a shared team password, then
routes between the two real pages via st.navigation, which is also
what lets each page have a proper sidebar title ("Register a sample" /
"Log an action") instead of Streamlit's default filename-derived label.

Why a shared password instead of Google-account-based auth (IAP): IAP
was tried (twice, actually) but proved unreliable in ways that
couldn't be root-caused even after extensive troubleshooting (IAM
bindings, org policy, OAuth consent screen config, and IAP
re-provisioning all checked out fine, yet some correctly-granted
external accounts still couldn't get in - see ACCESS_CONTROL_HISTORY.md
for the full troubleshooting trail). Real per-person attribution already happens at the data layer (every
registration/event captures the actual person's name/email), so this
login's only real job is keeping random passersby off the URL, which a
shared password does fine for that purpose - and unlike IAP, it just
works for everyone regardless of which institution's Google account
setup they have (or don't have).

Login has basic brute-force protection: a short delay on every attempt,
plus a per-IP lockout after too many wrong guesses in a row (see
_check_login below). This lives in memory on whatever Cloud Run
instance handles the request - not persistent, and not shared across
instances if the service ever scales beyond one - but that's fine for
the actual threat model here (a casual/scripted guesser hitting a
single instance), not a resilience guarantee against a determined
distributed attacker.

Questions or issues? Contact sunanda@exsitu.bio
"""

import time

import streamlit as st

from odr_common import render_svg_logo, ACCENT

st.set_page_config(
    page_title="DELIMIT Sample Registration",
    page_icon=None,
    layout="centered",
)

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


@st.cache_resource
def _login_attempts():
    """Shared across all sessions on this instance - a plain dict, not
    per-session state, so refreshing the page doesn't reset the count."""
    return {}


def _client_ip():
    try:
        fwd = st.context.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or "unknown"
    except Exception:
        return "unknown"


def _check_login(password):
    attempts = _login_attempts()
    ip = _client_ip()
    count, locked_until = attempts.get(ip, (0, 0))

    if time.time() < locked_until:
        wait_min = int((locked_until - time.time()) // 60) + 1
        st.error(f"Too many incorrect attempts. Try again in about {wait_min} minute(s).")
        return False

    time.sleep(1)  # cheap friction against automated guessing
    if password == st.secrets["auth"]["password"]:
        attempts.pop(ip, None)
        return True

    count += 1
    if count >= MAX_ATTEMPTS:
        attempts[ip] = (0, time.time() + LOCKOUT_SECONDS)
        st.error(f"Too many incorrect attempts. Locked out for {LOCKOUT_SECONDS // 60} minutes.")
    else:
        attempts[ip] = (count, 0)
        st.error(f"Incorrect password. {MAX_ATTEMPTS - count} attempt(s) left before a lockout.")
    return False


if not st.session_state.get("authenticated"):
    st.markdown(render_svg_logo("brand/logo_lockup_light.svg", width=380), unsafe_allow_html=True)
    st.markdown(f'<hr style="border: none; border-top: 2px solid {ACCENT}; margin: 0.5rem 0 1.25rem;">',
                unsafe_allow_html=True)
    st.caption("Enter the team password to continue.")
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter", type="primary", use_container_width=True)
    if submitted:
        if _check_login(password):
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

pg = st.navigation([
    st.Page("registration.py", title="Register a sample", default=True),
    st.Page("log_an_action.py", title="Log an action"),
])
pg.run()
