import json
import random
from Crypto.Hash import SHA256
from Crypto.Util.number import bytes_to_long, long_to_bytes
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dsa import DSA

cert1 = None
cert2 = None
public_key = None
private_key = None


with open("certificate_1.txt", "r") as file:
    cert1 = json.loads(file.read())
    file.close()

with open("certificate_2.txt", "r") as file:
    cert2 = json.loads(file.read())
    file.close()

with open("public_key.txt", "r") as file:
    public_key = json.loads(file.read())
    file.close()

with open("private_key.txt", "r") as file:
    private_key = json.loads(file.read())
    file.close()

q = public_key["q"]
p = public_key["p"]
g = public_key["g"]
y = public_key["y"]

r1, s1 = cert1["r"], cert1["s"]
r2, s2 = cert2["r"], cert2["s"]

m1 = {"name": cert1["name"], "website": cert1["website"], "expdate": cert1["expdate"]}
m2 = {"name": cert2["name"], "website": cert2["website"], "expdate": cert2["expdate"]}


def custom_hash(message):
    IV = b"this_is_the_iv02"
    m = pad(message, AES.block_size)
    message_blocks = [m[i : i + 16] for i in range(0, len(m), 16)]
    hash = (AES.new(IV, AES.MODE_ECB)).encrypt(message_blocks[0])
    for i in range(1, len(message_blocks)):
        hash = (AES.new(message_blocks[i], AES.MODE_ECB)).encrypt(hash)
    return hash


verified = False
forged_message = None
attempts = 0
while forged_message is None:
    r_new = 0
    s_new = 0
    u1 = 0
    u2 = 0
    attempts += 1

    # print("=" * 60)
    # print("Attempting to forge a new signature...")
    while r_new == 0 or s_new == 0:
        u1 = random.randint(1, q - 1)
        u2 = random.randint(1, q - 1)

        # (g^u1 * y^u2 mod p) mod q
        term1 = pow(g, u1, p)
        term2 = pow(y, u2, p)
        r_new = (term1 * term2 % p) % q

        if r_new == 0:
            continue

        # r * u2^-1 mod q
        s_new = (r_new * pow(u2, -1, q)) % q

    # print(f"Forged r: {r_new}")
    # print(f"Forged s: {s_new}")

    target_hash = (u1 * s_new) % q
    # print(f"Target H(m) as integer: {target_hash}")
    target_hash_bytes = long_to_bytes(target_hash, AES.block_size)

    IV = b"this_is_the_iv02"
    cipher_new = AES.new(IV, AES.MODE_ECB).decrypt(target_hash_bytes)

    try:
        forged_message = unpad(cipher_new, AES.block_size)
    except ValueError:
        continue
        # print("Decryption failed, padding is incorrect.")

    # print("=" * 60)

print("=" * 60)
print("Forged message successfully created!")
print(f"Took {attempts} attempts to forge a aes padded valid signature.")
print(f"Forged message: {forged_message.hex()}")
forged_cert_dict = {
    "name": forged_message.hex(),
    "website": "",
    "expdate": "",
}

forged_cert_with_sig = {
    **forged_cert_dict,
    "r": r_new,
    "s": s_new,
}

with open("forged_certificate.txt", "w") as f:
    json.dump(forged_cert_with_sig, f, indent=4)

# ------------------------------------------------------------------------------
# Verifying the forged certificate
dsa = DSA()
dsa.y = y
dsa.p = p
dsa.q = q
dsa.g = g

signature = (r_new, s_new)

verified = dsa.verify(
    forged_cert_dict,
    signature,
    custom_hash,
)

print(f"Verification result: {verified}")
print("=" * 60)
