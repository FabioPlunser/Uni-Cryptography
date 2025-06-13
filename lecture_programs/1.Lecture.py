from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

import os

key = os.urandom(16)

message = b"Hello World Crypto"

# cipher = AES.new(key, AES.MODE_ECB)
# encryptedMessage = cipher.encrypt(pad(message, AES.block_size))
# print(encryptedMessage.hex())

# decryptedMessage = cipher.decrypt(encryptedMessage)

# print(decryptedMessage)
# unpadded = unpad(decryptedMessage, AES.block_size)

# print(unpadded)
# assert unpadded == message

from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives import padding

cipher = Cipher(AES(key), modes.CBC(os.urandom(16)))
encryptor = cipher.encryptor()

padder = padding.PKCS7(AES.block_size).padder()
unpadder = padding.PKCS7(AES.block_size).unpadder()

message = padder.update(message) + padder.finalize()
ct = encryptor.update(message) + encryptor.finalize()
print(ct.hex())

decryptor = cipher.decryptor()
pt = decryptor.update(ct) + decryptor.finalize()
pt = unpadder.update(pt) + unpadder.finalize()
print(pt)


