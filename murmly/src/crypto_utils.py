from typing import Tuple, Optional
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.asymmetric.dh import ( 
    DHParameters, 
    DHPrivateKey,
    DHPublicKey
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, ParameterFormat
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key, 
    load_pem_parameters
)

# for aes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import *

def generate_dh_parameters():
# the parameters are shared by both parties. 
# this is Z modulo nZ: a galois field with large prime. 
# `key_size` param  specifies a prime number with approx. length of `key_size` bits.
# the generator element is 2. 
    parameters: DHParameters = dh.generate_parameters(
        generator=2, 
        key_size=PRIME_BITS
    )
    return parameters


def generate_pair(parameters: DHParameters) -> Tuple[DHPrivateKey, DHPublicKey]: 
    priv_key : DHPrivateKey = parameters.generate_private_key()
    pub_key: DHPublicKey    = priv_key.public_key()
    
    return priv_key, pub_key

def exchange_and_derive(priv_key: DHPrivateKey, peer_pub_key: DHPublicKey) ->  bytes:
    # the peer_pub_key is B= g^{peer_private_key} mod p
    # the shared key is A=B^{priv_key} mod p
    shared_key: bytes = priv_key.exchange(peer_public_key=peer_pub_key)
    
    # as stated in documentatiobut n https://cryptography.io/en/latest/hazmat/primitives/asymmetric/dh/#cryptography.hazmat.primitives.asymmetric.dh.DHPrivateKey
    # derive the key again to streghten the key
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_key)
    
    return derived_key


def encrypt_aes_gcm(
    key: bytes, 
    data: bytes, 
    associated_data: bytes=None, 
    nonce: bytes=None
) -> bytes:
    if nonce == None:
        # generate nonce, should not happen
        nonce = os.urandom(NONCE_SIZE)
    
    aesgcm = AESGCM(key)
    
    ct = aesgcm.encrypt(
        nonce=nonce, 
        data=data,
        associated_data=associated_data,
    )
    return nonce + ct

def decrypt_aes_gcm(key: bytes, data: bytes, associated_data: bytes=None) -> bytes:
    
    nonce = data[:12]
    aesgcm = AESGCM(key)
    
    pt = aesgcm.decrypt(
        nonce=nonce, 
        data=data[12:],
        associated_data=associated_data,
    )
    return pt 

def encrypt(key: bytes, text: str, nonce: bytes) -> bytes: 
    text_enc = text.encode('utf-8')
    # associated_data = b""     # when needed
    ct = encrypt_aes_gcm(key, text_enc, nonce=nonce)
    return ct

def decrypt(key: bytes, ct: bytes) -> str:
    # associated_data = b""     # when needed
    pt = decrypt_aes_gcm(key, ct)
    text = pt.decode('utf-8')
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

def serialize_parameters(params: DHParameters) -> bytes:
    return params.parameter_bytes(
        encoding=Encoding.PEM,
        format=ParameterFormat.PKCS3
    )

def deserialize_parameters(serialized_params: bytes) -> DHParameters:
    return load_pem_parameters(serialized_params)

def main(): 
    parameters = generate_dh_parameters()
    bob_pair = generate_pair(parameters)
    alice_pair = generate_pair(parameters)
    
    bob_pub_key = bob_pair[1]
    alice_pub_key = alice_pair[1]

    derived_key_bob = exchange_and_derive(bob_pair[0], alice_pub_key)
    derived_key_alice = exchange_and_derive(alice_pair[0], bob_pub_key)
    
    assert derived_key_bob == derived_key_alice, "Derived keys do not match!"
    print("works lol!")

if __name__ == '__main__':
    main()