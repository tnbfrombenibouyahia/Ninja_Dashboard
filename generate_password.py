import streamlit_authenticator as stauth

hashed = stauth.Hasher(['boomer']).generate()
print(hashed)
