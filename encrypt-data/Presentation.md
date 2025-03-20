---
marp: true
class: invert
---

# Ecnrypting and Decrypting Folder

--- 
## Encryption
Generate a key with a password first navie approach
```python 
  def __generate_key(self, pwd: str) -> tuple[bytes, bytes]:
        """Generates a key, IV, and salt from a password using PBKDF2HMAC."""
        hashed_pwd = hashlib.sha256(pwd.encode()).digest()
        key = os.urandom(hashed_pwd)
        iv = os.urandom(16)

        return key, iv
```
This is unsecure


---

## Encryption 
Better password encryption implementation 
```python 
  def __generate_key(self, pwd: str) -> tuple[bytes, bytes]:
        """Generates a key, IV, and salt from a password using PBKDF2HMAC."""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(pwd.encode())
        iv = os.urandom(16)

        return key, iv, salt
```