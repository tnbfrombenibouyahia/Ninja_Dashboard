import streamlit_authenticator as stauth

passwords = ['boomer', 'yumi']
hashed_passwords = stauth.Hasher(passwords).generate()
print(hashed_passwords)
