import streamlit_authenticator as stauth

hashed_password = stauth.Hasher().hash("boomer")
print(hashed_password)

