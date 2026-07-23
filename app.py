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
external accounts still couldn't get in - see setup.md "ODR setup" /
git history around 2026-07-22 for the full troubleshooting trail).
Real per-person attribution already happens at the data layer (every
registration/event captures the actual person's name/email), so this
login's only real job is keeping random passersby off the URL, which a
shared password does fine for that purpose - and unlike IAP, it just
works for everyone regardless of which institution's Google account
setup they have (or don't have).

Questions or issues? Contact sunanda@exsitu.bio
"""

import streamlit as st

from odr_common import render_svg_logo, ACCENT

st.set_page_config(
    page_title="DELIMIT Sample Registration",
    page_icon=None,
    layout="centered",
)

if not st.session_state.get("authenticated"):
    st.markdown(render_svg_logo("brand/logo_lockup_light.svg", width=380), unsafe_allow_html=True)
    st.markdown(f'<hr style="border: none; border-top: 2px solid {ACCENT}; margin: 0.5rem 0 1.25rem;">',
                unsafe_allow_html=True)
    st.caption("Enter the team password to continue.")
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter", type="primary", use_container_width=True)
    if submitted:
        if password == st.secrets["auth"]["password"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

pg = st.navigation([
    st.Page("registration.py", title="Register a sample", default=True),
    st.Page("log_an_action.py", title="Log an action"),
])
pg.run()
