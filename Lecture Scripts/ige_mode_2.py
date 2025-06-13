from pwn import xor
from Crypto.Util.Padding import pad, unpad
from Crypto.Cipher import AES
import os

# def byte_xor(a,b):
#     return b''.join([(a_i^b_i).to_bytes(byteorder='big') for a_i,b_i in zip(a,b)])

def aes_encrypt(block, key):
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(block)

def aes_decrypt(block, key):
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.decrypt(block)


def ige_mode_encrypt(plaintext, key):
    iv1 = os.urandom(16)
    iv2 = os.urandom(16)
    iv1_copy = iv1
    iv2_copy = iv2
    padded_plaintext = pad(plaintext, AES.block_size)
    plaintext_blocks = [ padded_plaintext[i:i+16] for i in range(0, len(padded_plaintext), 16)]

    ciphertexts = []

    for block in plaintext_blocks:
        p1 = xor(block, iv1)
        p1 = aes_encrypt(p1, key)
        c1 = xor(p1, iv2)
        ciphertexts.append(c1)
        iv1 = c1
        iv2 = block
    
    return iv1_copy + iv2_copy + b''.join(ciphertexts)
    

def ige_mode_decrypt(ciphertext, key):
    iv1 = ciphertext[:16]
    iv2 = ciphertext[16:32]
    ciphertext = ciphertext[32:]

    ciphertext_blocks = [ ciphertext[i:i+16] for i in range(0, len(ciphertext), 16)]

    plaintexts = []

    for block in ciphertext_blocks:
        c1 = xor(block, iv2)
        c1 = aes_decrypt(c1, key)
        p1 = xor(c1, iv1)
        plaintexts.append(p1)
        iv2 = p1
        iv1 = block

    plaintext = b''.join(plaintexts)
    unpadded_plaintext = unpad(plaintext, AES.block_size)

    return unpadded_plaintext
    


message = os.urandom(100)
key = os.urandom(16)
assert ige_mode_decrypt(ige_mode_encrypt(message, key), key)