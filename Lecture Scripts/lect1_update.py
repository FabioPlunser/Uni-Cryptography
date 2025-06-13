
"""
Basic commands
"""

# # exponentiation in Python
# 2**3

# # exponentiation in SageMath
# 2^3

# # XOR in python
# 2^3

# # XOR in SageMath
# 2^^3


# AND &
# OR |
# XOR ^ (in python), ^^ (in SageMath)
# NOT ~
# right-shift >> 
# left-shift <<


"""Encodings"""

message = b'hello'

###### HEX Encoding ######
print(message.hex())

###### Base64 Encoding ######
from base64 import b64encode, b64decode
encoded_message = b64encode(message)
assert b64decode(encoded_message) == message

##### Integer encoding of a bytes string #####
from Crypto.Util.number import bytes_to_long, long_to_bytes
encoded_message = bytes_to_long(message)
assert message == long_to_bytes(encoded_message)


"""
AES: Mode ECB

If you want to use DES, just import DES instead of AES.
Consider that the AES block size is 16 bytes (128 bits) and the DES block size is 8 bytes (64 bits)
"""
import os

###### With PyCryptodome ######
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

key = os.urandom(16)

message = b'hello world'

cipher = AES.new(key, AES.MODE_ECB)
encrypted_message = cipher.encrypt(pad(message, AES.block_size, style='pkcs7'))
print(encrypted_message.hex())
print(unpad(pad(message, AES.block_size, style='pkcs7'), AES.block_size))

decrypted_message = unpad(cipher.decrypt(encrypted_message), AES.block_size, style='pkcs7')
assert decrypted_message == message


##### With Cryptography Hazmat #####

from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives import padding


padder = padding.PKCS7(AES.block_size).padder()
unpadder = padding.PKCS7(AES.block_size).unpadder()

cipher = Cipher(AES(key), modes.ECB())
encryptor = cipher.encryptor()
decryptor = cipher.decryptor()

ciphertext = encryptor.update(padder.update(message)+padder.finalize()) + encryptor.finalize()
padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

assert plaintext == message


"""
AES: Mode CBC

If you want to use DES, just import DES instead of AES.
Consider that the AES block size is 16 bytes (128 bits) and the DES block size is 8 bytes (64 bits)
"""
import os

###### With PyCryptodome ######
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

key = os.urandom(16)
iv = os.urandom(16)

message = b'hello world'

cipher = AES.new(key, AES.MODE_CBC(iv))
encrypted_message = cipher.encrypt(pad(message, AES.block_size, style='pkcs7'))
print(encrypted_message.hex())
print(unpad(pad(message, AES.block_size, style='pkcs7'), AES.block_size))

cipher = AES.new(key, AES.MODE_CBC(iv)) # we MUST reinitialize the cipher when decrypting because the IV is automatically changed after every encryption 
decrypted_message = unpad(cipher.decrypt(encrypted_message), AES.block_size, style='pkcs7')
assert decrypted_message == message


##### With Cryptography Hazmat #####

from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives import padding


padder = padding.PKCS7(AES.block_size).padder()
unpadder = padding.PKCS7(AES.block_size).unpadder()

cipher = Cipher(AES(key), modes.CBC(iv))
encryptor = cipher.encryptor()
decryptor = cipher.decryptor()

ciphertext = encryptor.update(padder.update(message)+padder.finalize()) + encryptor.finalize()
padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

assert plaintext == message


# From the CBC construction you can notice the software development choices. 
# In PyCryptodome we have a single object which is used both for encryption and decryption. 
# Therefore they share the internal IV. This is the reason why we MUST reinitialize the cipher before decrypting.
# In Cryptography from a single object we generate a different object for encryption and decryption.
# Their idea (which I suggest to always adapt) is to satisfy the 'single responsibility principle' for the software development, meaning that you functions should do only one operation, not more. 
# In this case, the encryptor is responsible only for the encryption, the decryptor only for the decryption. 
# As a consequence, they are not sharing the internal value of IV, but each object (encryptor and decryptor) has its own attributes. 



"""
AES: Mode CBC

If you want to use DES, just import DES instead of AES.
Consider that the AES block size is 16 bytes (128 bits) and the DES block size is 8 bytes (64 bits)
"""
import os

###### With PyCryptodome ######
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

key = os.urandom(16)
iv = os.urandom(16)

message = b'hello world'

cipher = AES.new(key, AES.MODE_OFB(iv))
encrypted_message = cipher.encrypt(pad(message, AES.block_size, style='pkcs7'))
print(encrypted_message.hex())
print(unpad(pad(message, AES.block_size, style='pkcs7'), AES.block_size))

cipher = AES.new(key, AES.MODE_CBC(iv)) # we MUST reinitialize the cipher when decrypting because the IV is automatically changed after every encryption 
decrypted_message = unpad(cipher.decrypt(encrypted_message), AES.block_size, style='pkcs7')
assert decrypted_message == message


##### With Cryptography Hazmat #####

from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives import padding


padder = padding.PKCS7(AES.block_size).padder()
unpadder = padding.PKCS7(AES.block_size).unpadder()

cipher = Cipher(AES(key), modes.OFB(iv))
encryptor = cipher.encryptor()
decryptor = cipher.decryptor()

ciphertext = encryptor.update(padder.update(message)+padder.finalize()) + encryptor.finalize()
padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

assert plaintext == message



""" PADDING types
They add a necessary amount of bytes in order to make the message length a multiple of the block size """

# PKCS7 (STANDARD): suppose we must fill the message with 'n' bytes. PKCS7 adds 'n' bytes whose value is 'n' at the end of the message.

# ISO7816: adds the necessary number of bits to make the message length a multiple of the block size. The first bit after the message is '1', the remaining bits are all set to '0'

# x923: born for DES, extended to newer constructions, but almost never used. All the added bytes are '0' BYTES (not bits), except the last byte which is set to the length of the padding. 

#### PyCryptodome supports all the 3 padding types
#### Cryptography supports only PKCS7, the standard, and x923 for backward compatibility with DES. 



""" Next week I will upload the CTR Mode """
""" I'll not do this right now because I want to give you the possibility to play with it on your own """



"""
AES: Mode CTR

If you want to use DES, just import DES instead of AES.
Consider that the AES block size is 16 bytes (128 bits) and the DES block size is 8 bytes (64 bits)

In PyCryptodome you can choose among two possibilities:
- using the nonce (which is a value whose length is less than the block size). In this case the counter will be added at the end, e.g. NONCE||COUNTER, at the next block NONCE||(COUNTER+1) and so on...
- using an 'initial value' whose length is the block size and an empty nonce. Here the first block is IV, then IV+1, IV+2, etc...


In Hazmat cryptography:
- you can only choose the initial value whose length is the block size

"""
key = os.urandom(16)
message = os.urandom(20)

#### PyCryptodome with NONCE and NOT iv

nonce = os.urandom(11)
pycrypto_padded_message = pad(message, block_size=AES.block_size)
pycrypto_CIPHER = AES.new(key, AES.MODE_CTR, nonce=nonce)
ciphertext = pycrypto_CIPHER.encrypt(pycrypto_padded_message)
pycrypto_CIPHER = AES.new(key, AES.MODE_CTR, nonce=nonce)
plaintext = unpad(pycrypto_CIPHER.decrypt(ciphertext), AES.block_size)

assert plaintext == message


##################################################
######## The following two codes are equivalent:
##################################################

#### PyCryptodome with IV and empty NONCE
iv = os.urandom(16)
pycrypto_padded_message = pad(message, block_size=AES.block_size)
pycrypto_CIPHER = AES.new(key, AES.MODE_CTR, initial_value=iv, nonce=b'')
ciphertext = pycrypto_CIPHER.encrypt(pycrypto_padded_message)
pycrypto_CIPHER = AES.new(key, AES.MODE_CTR, initial_value=iv, nonce=b'')
plaintext = unpad(pycrypto_CIPHER.decrypt(ciphertext), AES.block_size)

assert plaintext == message


#### Hazmat cryptography
padder= padding.PKCS7(algorithms.AES.block_size).padder()
unpadder= padding.PKCS7(algorithms.AES.block_size).unpadder()
hazmat_padded_message = padder.update(message) + padder.finalize()

hazmat_cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
encrypt_functionality = hazmat_cipher.encryptor()
decrypt_functionality = hazmat_cipher.decryptor()


ct = encrypt_functionality.update(hazmat_padded_message) + encrypt_functionality.finalize()
padded_pt = decrypt_functionality.update(ct) + decrypt_functionality.finalize()
pt = unpadder.update(padded_pt)+unpadder.finalize()
assert pt == message
assert ct == ciphertext


#### REASON

# The cryptography library does not follow the definition of nonce for the CTR mode found in the NIST SP 800-38A standard, annex B2 (i.e. nonce = the fixed bytes in the initial counter block, which are never incremented as part of the counter) but rather inherits the meaning of nonce from the OpenSSL API (understandable, since cryptography is just a wrapper to OpenSSL).

# In PyCryptodome, there is a distinction made between the nonce and initial_value parameters, aligned with the NIST SP 800-38A.