import json
from Crypto.Hash import SHA256
from Crypto.Util.number import bytes_to_long
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from dsa import DSA

dsa = DSA()


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

r1, s1 = cert1["r"], cert1["s"]
r2, s2 = cert2["r"], cert2["s"]

m1 = {"name": cert1["name"], "website": cert1["website"], "expdate": cert1["expdate"]}
m2 = {"name": cert2["name"], "website": cert2["website"], "expdate": cert2["expdate"]}

print("m1:", m1)

message1 = json.dumps(m1).encode()
message2 = json.dumps(m2).encode()

hashMessage1 = SHA256.new(message1).digest()
hashMessage2 = SHA256.new(message2).digest()

hm1 = bytes_to_long(hashMessage1)
hm2 = bytes_to_long(hashMessage2)

u1 = 1
u2 = 1

# We know IV
IV = b"this_is_the_iv02"


def decrypt_hash(hash_value):
    cipher = AES.new(IV, AES.MODE_ECB)
    decrypted = cipher.decrypt(hash_value)
    return decrypted


def custom_hash(message):
    IV = b"this_is_the_iv02"
    m = pad(message, AES.block_size)
    message_blocks = [m[i : i + 16] for i in range(0, len(m), 16)]
    hash = (AES.new(IV, AES.MODE_ECB)).encrypt(message_blocks[0])
    for i in range(1, len(message_blocks)):
        hash = (AES.new(message_blocks[i], AES.MODE_ECB)).encrypt(hash)
    return hash


# dsa.verify(m1, (r1, s1), custom_hash)
