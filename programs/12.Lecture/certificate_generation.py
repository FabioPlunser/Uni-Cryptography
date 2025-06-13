from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives import serialization
from Crypto.PublicKey import RSA
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.hashes import SHA256
from datetime import datetime, timedelta, timezone

key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

key = RSA.generate(2048)

with open("myprivatekey.pem", "wb") as f:

    data = key.export_key()

    f.write(data)

key2 = ec.generate_private_key(
    curve=ec.SECP256K1
)

subject = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "IT"),
    x509.NameAttribute(NameOID.EMAIL_ADDRESS, "luca.campa@uibk.ac.at")
])


issuer = subject


certificate = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)).not_valid_after(datetime.now(timezone.utc) + timedelta(days=30)).sign(key2, SHA256())


print(certificate.public_bytes(serialization.Encoding.PEM).decode())
