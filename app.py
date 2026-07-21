"""
DELIMIT Sample Registration - entry point
------------------------------------------
This is the file Streamlit Cloud (and `streamlit run app.py` locally)
actually runs. It only sets page config, gates access behind a shared
team password (see the note below on why - not IAP), and routes
between the two real pages via st.navigation, which is also what lets
each page have a proper sidebar title ("Register a sample" / "Log an
action") instead of Streamlit's default filename-derived label.

Why a shared password instead of Google-account-based auth (IAP): the
~20 people who need access span several institutions (NASA, Carnegie,
Howard, Purdue, Rutgers, ex situ bio) and Google account coverage is
inconsistent/unknown across them - IAP would leave some people locked
out. Real per-person attribution already happens at the data layer
(every registration/event captures the actual person's name/email), so
this login's only job is keeping random passersby off the URL, which a
shared password does fine for that purpose.

Questions or issues? Contact sunanda@exsitu.bio
"""

import streamlit as st

st.set_page_config(
    page_title="DELIMIT Sample Registration",
    page_icon=None,
    layout="centered",
)

if not st.session_state.get("authenticated"):
    st.title("DELIMIT Sample Registration")
    st.caption("Enter the team password to continue.")
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter", type="primary")
    if submitted:
        if password == st.secrets["auth"]["password"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

pg = st.navigation([
    st.Page("registration.py", title="Register a sample", default=True),
    st.Page("pages/1_Log_an_action.py", title="Log an action"),
])
pg.run()
