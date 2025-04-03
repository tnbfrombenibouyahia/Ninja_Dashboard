import streamlit as st

try:
    import streamlit_authenticator as stauth
    st.write("✅ Version de streamlit-authenticator :", stauth.__version__)
except ImportError:
    st.error("❌ streamlit-authenticator n'est pas installé.")
