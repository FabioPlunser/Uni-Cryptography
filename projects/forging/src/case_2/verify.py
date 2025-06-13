import json
from Crypto.Hash import SHA256
from Crypto.Util.number import getPrime, GCD, bytes_to_long, isPrime

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


message1 = json.dumps(m1).encode()
message2 = json.dumps(m2).encode()

hashMessage1 = SHA256.new(message1).digest()
hashMessage2 = SHA256.new(message2).digest()

hm1 = bytes_to_long(hashMessage1)
hm2 = bytes_to_long(hashMessage2)

print("Hash of message 1:", hashMessage1.hex())
print("Hash of message 2:", hashMessage2.hex())

a = 3
b = 5

zaheler = hm2 * s1 - b * s2 * s1 - a * s2 * hm1
nenner = a * s2 * r1 - r2 * s1

x = (zaheler * pow(nenner, -1, q)) % q


print("The derived private key x is:", x)
print("The original private key x is:", private_key["x"])

assert x == private_key["x"]
