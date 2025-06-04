from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import json
from elgamal import *


def gen_keys():
    signature_scheme = ElGamal()
    signature_scheme.keygen()
    public_key = { 
        'q': signature_scheme.q,
        'g': signature_scheme.g,
        'h': signature_scheme.h
    }   

    private_key = { 
        'q': signature_scheme.q,
        'g': signature_scheme.g,
        'x': signature_scheme.x
    }  

    with open('public_key.txt', 'w') as pk:
        pk.write(json.dumps(public_key))
        pk.close()

    with open('private_key.txt', 'w') as sk:
        sk.write(json.dumps(private_key))
        sk.close()

    return signature_scheme

def gen_certificate(username:bytes, website_name:bytes, expiration_date:bytes):
    cert = {
        'name': username.hex(),
        'website': website_name.hex(),
        'expdate': expiration_date.hex()
    }
    return json.dumps(cert)



def sign_certificate_v3(signature_scheme, certificate:str):
    cert = json.loads(certificate)
    nonce = random.randint(1, signature_scheme.q-2)
    while GCD(nonce, signature_scheme.q-1) != 1 or nonce == 0:
        nonce = random.randint(1, signature_scheme.q-2)
    r,s = signature_scheme.sign(cert, nonce, lambda m: custom_hash(m))
    cert['r'] = r
    cert['s'] = s

    return json.dumps(cert) 




def custom_hash(message):
    IV = b'this_is_the_iv02'
    m = pad(message, AES.block_size)
    message_blocks = [m[i:i+16] for i in range(0, len(m), 16)]
    hash = IV
    for el in message_blocks:
        hash = (AES.new(el, AES.MODE_ECB)).encrypt(hash)
    
    return hash


sig_scheme = gen_keys()
cert1 = gen_certificate(b'lucacampa', b'https://project3topic1.com', b'01/01/2026')
print(cert1)
cert1 = sign_certificate_v3(sig_scheme, cert1)


cert2 = gen_certificate(b'lucacampa', b'https://project2topic2.com', b'01/01/2027')
cert2 = sign_certificate_v3(sig_scheme, cert2)


with open('certificate_1.txt', 'w') as file:
    file.write(cert1)
    file.close()

with open('certificate_2.txt', 'w') as file:
    file.write(cert2)
    file.close()


