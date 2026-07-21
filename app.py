"""
DELIMIT Sample Registration - entry point
------------------------------------------
This is the file Streamlit Cloud (and `streamlit run app.py` locally)
actually runs. It only sets page config and routes between the two
real pages via st.navigation, which is also what lets each page have
a proper sidebar title ("Register a sample" / "Log an action") instead
of Streamlit's default filename-derived label.

Questions or issues? Contact sunanda@exsitu.bio
"""

import streamlit as st

st.set_page_config(
    page_title="DELIMIT Sample Registration",
    page_icon=None,
    layout="centered",
)

pg = st.navigation([
    st.Page("registration.py", title="Register a sample", default=True),
    st.Page("pages/1_Log_an_action.py", title="Log an action"),
])
pg.run()
