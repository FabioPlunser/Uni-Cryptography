from Crypto.Cipher import AES
import json
from Crypto.Hash import SHA256
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

def gen_certificate(username:str, website_name:str, expiration_date:str):
    cert = {
        'name': username,
        'website': website_name,
        'expdate': expiration_date
    }
    return json.dumps(cert)


def sign_certificate_v1(signature_scheme: ElGamal, certificate:str, nonce):
    cert = json.loads(certificate)
    r,s = signature_scheme.sign(certificate.encode(), nonce, lambda m: hash(m))
    cert['r'] = r
    cert['s'] = s

    return json.dumps(cert) 



def hash(message):
    h = SHA256.new(message).digest()
    return h




sig_scheme = gen_keys()
nonce = random.randint(2, sig_scheme.q-2)
assert GCD(nonce, sig_scheme.q-1) == 1

cert1 = gen_certificate('lucacampa', 'https://project3topic1.com', '01/01/2026')
cert1 = sign_certificate_v1(sig_scheme, cert1, nonce)

cert2 = gen_certificate('lucacampa', 'https://project2topic2.com', '01/01/2027')
cert2 = sign_certificate_v1(sig_scheme, cert2, nonce)


with open('certificate_1.txt', 'w') as file:
    file.write(cert1)
    file.close()

with open('certificate_2.txt', 'w') as file:
    file.write(cert2)
    file.close()


