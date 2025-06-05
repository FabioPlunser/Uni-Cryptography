from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from pwn import xor
import os


def aes_ecnrypt(block: bytes, key: bytes) -> bytes:
    cipher = Cipher(AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(block) + encryptor.finalize()


def aes_decrypt(block: bytes, key: bytes) -> bytes:
    cipher = Cipher(AES(key), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(block) + decryptor.finalize()


def pad(plaintext: bytes) -> bytes:
    block_size = AES.block_size
    padder = padding.PKCS7(block_size * 8).padder()
    return padder.update(plaintext) + padder.finalize()


def unpadd(plaintext: bytes) -> bytes:
    block_size = AES.block_size
    unpadder = padding.PKCS7(block_size * 8).unpadder()
    return unpadder.update(plaintext) + unpadder.finalize()


def ige_mode_encrypt(plaintext: bytes, key: bytes) -> bytes:
    iv1 = os.urandom(16)
    iv2 = os.urandom(16)

    block_size = AES.block_size

    padded_plaintext = pad(plaintext)
    plaintext_blocks = [
        padded_plaintext[i : i + block_size]
        for i in range(0, len(padded_plaintext), block_size)
    ]

    ciphertext = b""
    prev_cipher = iv1
    prev_plain = iv2

    for block in plaintext_blocks:
        xor_input = xor(block, prev_cipher)
        encrypted = aes_ecnrypt(xor_input, key)
        c_block = xor(encrypted, prev_plain)

        ciphertext += c_block
        prev_cipher = c_block
        prev_plain = block

    return iv1 + iv2 + ciphertext


def ige_mode_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    iv1 = ciphertext[:16]
    iv2 = ciphertext[16:32]
    actual_ciphertext = ciphertext[32:]

    block_size = AES.block_size

    if len(actual_ciphertext) % block_size != 0:
        raise ValueError(
            "Ciphertext length must be a multiple of the block size (16 bytes)."
        )

    padded_plaintext = b""
    prev_cipher = iv1
    prev_plain = iv2

    for i in range(0, len(actual_ciphertext), block_size):
        c_block = actual_ciphertext[i : i + block_size]

        xor_input = xor(c_block, prev_plain)
        decrypted = aes_decrypt(xor_input, key)
        p_block = xor(decrypted, prev_cipher)

         += p_block
        prev_cipher = c_block
        prev_plain = p_block

    plaintext = unpadd(padded_plaintext)

    return plaintext


if __name__ == "__main__":
    key = os.urandom(16)
    plaintext = b"This is a secret message that needs to be encrypted securely."

    print("Original plaintext:", plaintext)

    encrypted = ige_mode_encrypt(plaintext, key)
    print("Encrypted (hex):", encrypted.hex())

    decrypted = ige_mode_decrypt(encrypted, key)
    print("Decrypted:", decrypted)

    assert decrypted == plaintext, "Decryption failed!"
    print("Encryption and decryption successful!")
