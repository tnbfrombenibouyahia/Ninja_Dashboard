import bcrypt

plaintext = "yumi"
salt = bcrypt.gensalt(rounds=12)  # 12 ou plus
hashed = bcrypt.hashpw(plaintext.encode(), salt)
hashed_str = hashed.decode()

print(hashed_str)