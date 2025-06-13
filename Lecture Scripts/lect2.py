import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


from cryptography.hazmat.primitives.ciphers import algorithms, modes, Cipher
from cryptography.hazmat.primitives import padding

### AES GCM Mode
### Needed:
###     - a key of 16 bytes (the AES block size)
###     - a nonce (usually it is of 12 bytes. However, for interoperability it can be even of the same length as the block size)

## Both pycryptodome and hazmat are choosing by default a 16 bytes IV/NONCE


key = os.urandom(16)
nonce = os.urandom(12)
header = b'header' # why header? Recall what we have said during the lecture
message = os.urandom(20)


################# PyCryptodome
pycrypto_padded_message = pad(message, block_size=AES.block_size)
pycrypto_CIPHER = AES.new(key, AES.MODE_GCM, nonce=nonce)
pycrypto_CIPHER.update(header)
ciphertext, tag = pycrypto_CIPHER.encrypt_and_digest(pycrypto_padded_message)

pycrypto_CIPHER = AES.new(key, AES.MODE_GCM, nonce=nonce)
pycrypto_CIPHER.update(header)
plaintext = unpad(pycrypto_CIPHER.decrypt_and_verify(ciphertext, tag), AES.block_size)

print(ciphertext.hex())
print(tag.hex())
print()

assert plaintext == message


############## Hazmat cryptography
padder= padding.PKCS7(algorithms.AES.block_size).padder()
unpadder= padding.PKCS7(algorithms.AES.block_size).unpadder()
hazmat_padded_message = padder.update(message) + padder.finalize()

hazmat_cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
encrypt_functionality = hazmat_cipher.encryptor()
decrypt_functionality = hazmat_cipher.decryptor()

encrypt_functionality.authenticate_additional_data(header)
ct = encrypt_functionality.update(hazmat_padded_message) + encrypt_functionality.finalize() 
tag = encrypt_functionality.tag
print(ct.hex())
print(tag.hex())

hazmat_cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
decrypt_functionality = hazmat_cipher.decryptor()
decrypt_functionality.authenticate_additional_data(header)
padded_pt = decrypt_functionality.update(ct) + decrypt_functionality.finalize()
pt = unpadder.update(padded_pt)+unpadder.finalize()

assert pt == message
assert ct == ciphertext



""" KNOWN ATTACKS """
# if you want use this to xor bytes otherwise you can use the following method:
"""
def byte_xor(a, b):
    return bytes([a[i % len(a)] ^ b[i % len(b)] for i in range(max(len(a), len(b)))])

"""
from pwn import xor

############################### Bit Flipping
import json

my_data = '{"admin": false,"name": "Luca"}'


message = my_data.encode()
key = os.urandom(16)
iv = os.urandom(16)

cipher = AES.new(key, AES.MODE_CBC, iv=iv)
encrypted_token = cipher.encrypt(pad(message, AES.block_size))

print(iv.hex())
print(encrypted_token.hex())

cipher = AES.new(key, AES.MODE_CBC, iv=iv)
padded_plaintext = cipher.decrypt(encrypted_token)

loaded_token = json.loads( unpad(padded_plaintext, AES.block_size).decode() )
print(loaded_token)

new_iv = xor(iv, xor(b'{"admin": true ,', b'{"admin": false,'))
print(new_iv)

cipher = AES.new(key, AES.MODE_CBC, iv=new_iv)
padded_plaintext = cipher.decrypt(encrypted_token)
print(padded_plaintext)
loaded_token = json.loads( unpad(padded_plaintext, AES.block_size).decode() )
print(loaded_token)




########### Better to create two functions to avoid rewriting the same thing many times
def encrypt_m(message, iv, key):
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return cipher.encrypt(pad(message, AES.block_size))

def decrypt_m(ciphertext, iv, key):
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)




##################### SameIV
import random

iv = os.urandom(16)
key = os.urandom(16)
messages = [os.urandom(20) for _ in range(2)]

print("Messages:")
for i,m in enumerate(messages):
    print(f"{i} : {m.hex()}")

choice = random.randint(0,1)

print(f"Encrypted message: {encrypt_m(messages[choice], iv, key).hex()}")

# Now we send query to the encryption "oracle", that is we can encrypt whatever message except the two given messages

m0_prime = messages[0][:16]
print(f"Encrypted message bit: {encrypt_m(m0_prime, iv, key).hex()}")






##################### PredictableIV

from Crypto.Util.number import bytes_to_long, long_to_bytes

iv = os.urandom(16)
key = os.urandom(16)
messages = [os.urandom(20) for _ in range(2)]

print("Messages:")
for i,m in enumerate(messages):
    print(f"{i} : {m.hex()}")

choice = random.randint(0,1)

print(f"Encrypted message: {encrypt_m(messages[choice], iv, key).hex()}")

# Now we send query to the encryption "oracle", that is we can encrypt whatever message except the two given messages
old_iv = iv
iv = long_to_bytes(bytes_to_long(iv)+1)

m0_prime = xor(messages[0], xor(old_iv, iv))
print(f"Encrypted message bit: {encrypt_m(m0_prime, iv, key).hex()}")

