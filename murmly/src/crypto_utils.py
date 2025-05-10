from typing import Tuple, Optional
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.asymmetric.dh import (
    DHParameters,
    DHPrivateKey,
    DHPublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    ParameterFormat,
)
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key,
    load_pem_parameters,
)

# for aes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import PRIME_BITS, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


def generate_dh_parameters():
    # the parameters are shared by both parties.
    # this is Z modulo nZ: a galois field with large prime.
    # `key_size` param  specifies a prime number with approx. length of `key_size` bits.
    # the generator element is 2.
    parameters: DHParameters = dh.generate_parameters(generator=2, key_size=PRIME_BITS)
    return parameters


def generate_pair(parameters: DHParameters) -> Tuple[DHPrivateKey, DHPublicKey]:
    priv_key: DHPrivateKey = parameters.generate_private_key()
    pub_key: DHPublicKey = priv_key.public_key()

    return priv_key, pub_key


def exchange_and_derive(priv_key: DHPrivateKey, peer_pub_key: DHPublicKey) -> bytes:
    # the peer_pub_key is B= g^{peer_private_key} mod p
    # the shared key is A=B^{priv_key} mod p
    shared_key: bytes = priv_key.exchange(peer_public_key=peer_pub_key)

    # as stated in documentatiobut n https://cryptography.io/en/latest/hazmat/primitives/asymmetric/dh/#cryptography.hazmat.primitives.asymmetric.dh.DHPrivateKey
    # derive the key again to streghten the key
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"handshake data",
    ).derive(shared_key)

    return derived_key


def encrypt_aes_gcm(key: bytes, data: bytes, associated_data: bytes = None) -> bytes:

    nonce = os.urandom(12)
    aesgcm = AESGCM(key)

    ct = aesgcm.encrypt(
        nonce=nonce,
        data=data,
        associated_data=associated_data,
    )
    return nonce + ct


def decrypt_aes_gcm(key: bytes, data: bytes, associated_data: bytes = None) -> bytes:

    nonce = data[:12]
    aesgcm = AESGCM(key)

    pt = aesgcm.decrypt(
        nonce=nonce,
        data=data[12:],
        associated_data=associated_data,
    )
    return pt


def encrypt(key: bytes, text: str) -> bytes:
    text_enc = text.encode("utf-8")
    # associated_data = b""     # when needed
    ct = encrypt_aes_gcm(key, text_enc, nonce=nonce)
    return ct


def decrypt(key: bytes, ct: bytes) -> str:
    # associated_data = b""     # when needed
    pt = decrypt_aes_gcm(key, ct)
    text = pt.decode("utf-8")
    return text


def serialize_pub_key(pub_key: DHPublicKey) -> bytes:
    """serializes public key to bytes"""
    serialized_pub: bytes = pub_key.public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    )

    return serialized_pub


def deserialize_pub_key(serialized_pub: bytes) -> DHPublicKey:
    pub_key: DHPublicKey = load_pem_public_key(serialized_pub)

    return pub_key


def get_dh_params_as_hex(dh_parameters_obj):
    numbers = dh_parameters_obj.parameter_numbers()
    p_hex = hex(numbers.p)[2:]
    g_hex = hex(numbers.g)[2:]
    return {"p_hex": p_hex, "g_hex": g_hex}


def serialize_parameters(params: DHParameters) -> bytes:
    return params.parameter_bytes(encoding=Encoding.PEM, format=ParameterFormat.PKCS3)


def deserialize_parameters(serialized_params: bytes) -> DHParameters:
    return load_pem_parameters(serialized_params)


def derive_next_key(current_key: bytes, salt: bytes = None) -> bytes:
    """
    Derive the next key for forward secrecy using HKDF.
    This ensures that even if an attacker compromises the current key,
    they cannot derive previous keys.
    """
    if salt is None:
        salt = os.urandom(32)  # Generate a random salt if not provided
    
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"forward_secrecy_rotation",
    ).derive(current_key)
    
    return derived_key, salt


def derive_previous_key(current_key: bytes, salt: bytes) -> bytes:
    """
    Derive the previous key for backward secrecy using HKDF.
    This ensures that even if an attacker compromises the current key,
    they cannot derive future keys.
    """
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"backward_secrecy_rotation",
    ).derive(current_key)
    
    return derived_key


class KeyRotationManager:
    def __init__(self, initial_key: bytes):
        self.current_key = initial_key
        self.key_history = []  # List of (key, salt) tuples
        self.message_counter = 0
        self.ROTATION_THRESHOLD = 100  # Rotate key after 100 messages
        
    def get_current_key(self) -> bytes:
        return self.current_key
    
    def rotate_key(self) -> tuple[bytes, bytes]:
        """
        Rotate the key for forward secrecy.
        Returns the new key and salt.
        """
        new_key, salt = derive_next_key(self.current_key)
        self.key_history.append((self.current_key, salt))
        self.current_key = new_key
        self.message_counter = 0
        return new_key, salt
    
    def increment_counter(self):
        """
        Increment message counter and rotate key if threshold is reached.
        Returns True if key was rotated, False otherwise.
        """
        self.message_counter += 1
        if self.message_counter >= self.ROTATION_THRESHOLD:
            self.rotate_key()
            return True
        return False
    
    def get_key_for_message(self, message_number: int) -> bytes:
        """
        Get the key that was used for a specific message number.
        This is used for backward secrecy - to decrypt old messages.
        """
        if message_number >= len(self.key_history):
            return self.current_key
        
        return self.key_history[message_number][0]


def main():
    parameters = generate_dh_parameters()
    bob_pair = generate_pair(parameters)
    alice_pair = generate_pair(parameters)

    bob_pub_key = bob_pair[1]
    alice_pub_key = alice_pair[1]

    derived_key_bob = exchange_and_derive(bob_pair[0], alice_pub_key)
    derived_key_alice = exchange_and_derive(alice_pair[0], bob_pub_key)

    assert derived_key_bob == derived_key_alice, "Derived keys do not match!"


if __name__ == "__main__":
    main()
