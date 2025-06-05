from Crypto.Cipher import AES as PyCryptoAES
from Crypto.Util.Padding import pad, unpad

import os

from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives import padding

# Common parameters
header = b"header"
message = os.urandom(20)
key = os.urandom(16)
nonce = os.urandom(12)

# PyCryptodome implementation
pycrypto_padded_message = pad(message, block_size=PyCryptoAES.block_size)
pycrypto_cipher = PyCryptoAES.new(key, PyCryptoAES.MODE_GCM, nonce=nonce)
pycrypto_cipher.update(header)  # AAD
ciphertext = pycrypto_cipher.encrypt(pycrypto_padded_message)
tag = pycrypto_cipher.digest()

# Decryption with PyCryptodome
pycrypto_decrypt = PyCryptoAES.new(key, PyCryptoAES.MODE_GCM, nonce=nonce)
pycrypto_decrypt.update(header)  # AAD
plaintext_padded = pycrypto_decrypt.decrypt_and_verify(ciphertext, tag)
plaintext = unpad(plaintext_padded, block_size=PyCryptoAES.block_size)

# Cryptography hazmat implementation
padder = padding.PKCS7(128).padder()  # AES block size is 128 bits (16 bytes)
hazmat_padded_message = padder.update(message) + padder.finalize()

hazmat_cipher = Cipher(AES(key), modes.GCM(nonce))
encryptor = hazmat_cipher.encryptor()
encryptor.authenticate_additional_data(header)
ct = encryptor.update(hazmat_padded_message) + encryptor.finalize()
tag = encryptor.tag

print(ct.hex())
print(tag.hex())

# Decryption with hazmat
hazmat_decrypt = Cipher(AES(key), modes.GCM(nonce, tag)).decryptor()
hazmat_decrypt.authenticate_additional_data(header)
padded_pt = hazmat_decrypt.update(ct) + hazmat_decrypt.finalize()

unpadder = padding.PKCS7(128).unpadder()
pt = unpadder.update(padded_pt) + unpadder.finalize()

# Verify the result
assert pt == message
print("Success! The message was correctly encrypted and decrypted.")


import json
import xor

my_data = '{"admin: false, "name": "Fabio}'

message = my_data.encode()
key = os.urandom(16)
iv = os.urandom

cipher = AES.new(key, AES.MODE_CBC, iv)
ecncrypted_token = cipher.encrypt(pad(message, AES.block_size))

print(iv.hex())
print(ecncrypted_token.hex())

cipher = AES.new(key, AES.MODE_CBC, iv)
padded_plain = cipher.decrypt(ecncrypted_token)

loaded_token = json.loads(unpad(padded_plain, AES.block_size).decode())

print(loaded_token)


new_iv = (iv ^ (b'{ "admin": true}' ^ b'{"admin: false}')