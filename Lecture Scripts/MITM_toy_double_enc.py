import os
import string
import random
from base64 import b64encode, b64decode

KEY_LENGTH = 2

def encrypt(message, key):
    e1 = bytes([message[i] ^ key[i % len(key)] for i in range(len(message))])
    return b64encode(e1)

def decrypt(ciphertext, key):
    e1 = b64decode(ciphertext)
    return bytes([e1[i] ^ key[i % len(key)] for i in range(len(e1))])


def gen_key():
    alphabet = string.ascii_lowercase
    key = b''.join([ord(alphabet[i]) for i in random.choices(range(len(alphabet)), k=2*KEY_LENGTH)])
    return key
    
def cipher(m):
    K = os.urandom(2*KEY_LENGTH)
    print(K)
    c1 = encrypt(m, K[:KEY_LENGTH])
    c2 = encrypt(c1, K[KEY_LENGTH:])
    return c2

def get_plaintext_ciphertext_couple():
    m = b"Let's meet at the center"
    c2 = cipher(m)

    return m, c2




