from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Your PEM private key
pem_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAxoINivhkH/RG4L1rgotLyVj3YWBGh11M4Z8MdtNAGgzNwnH2
lBwOJ6K1O5R0mmo5vTSkx21TTTz4b7ealAEzpLHyXShUsdQey2CUv4X6rdHpn29O
E622mImYw4Ni7uJkhdWl3JxpLIu9ya/ZpsKy75W91eV8HyscLz3/zjekPv2y4hNU
du9unhGLGBXYrdEhA310tgHyHgHizmgPohPedReeTHIRQEr/epYFwORyioK2yOHC
6nKniWSioXjrmFziw/vHhl4rtB7ZxLs+M+csAVEr2EcyUb9HhMz4stPyCGDomXSh
gwIZsmJsdsA0tBDJkbx03+qyQfZ5V1XPdIMZUwIDAQABAoIBADE3QFVStTxI66O/
wt54W79da+P8IzBffPa5YLU7NfrfbspFSA27kPTZvdY6Pdik+pDC8xGwtMUDF1NX
cZ89Vwj/x2e6XplCTqo81VRQyvB6iVIqnfB6Ernp73KV6hrxDVwzNq6mJttRACp3
i15xijylYw4bmfT+UrwRwpDlsbad7sItqPF6m8cQ1qPmUw1IWKJpZtnnM0CeW1Zd
ZvPsMgGcXS0RCBkiCESUDftEB7JpTNmtCoMRai4CFKLlluU+C2NQ/F9mAOodHG5c
3iSDnos/KS2CtyZ4MGseSZ+Pe9+tbHgA9x6EHaE6WzFb95L+vQHlYcPD4cWn6g+M
rd/c3PECgYEA0f6CnyHKir81U9D68aZtbRBlQy2CMfO6czWQcijVkekfwdacFYn1
4yRyHCe4htvo5rzUvgQ0A5ggeuGMIRXUowXH1BPfjKjwYGCi78YYvmeQM++r9hVb
SJaMePJUZ7prLDqAhmgBzvXVnEmh1lJOI40RvLfBNClLNUWTR/6EKYMCgYEA8f9X
2HT0B2VgjKDbEA/V/kFhzFD8Ap+1nw5voAle2b+x5S6USfdaP5xhVWYfzCobTytJ
lmHSkiXmjP5eFzeb3L8qfqu4Rdnf+wapS1/PwCsZ4HI/Enc3Ln+7r5hmNvLVnch7
y+Vf0GQltDEB9oH9ouWFOB5+b8o6clfgBDHp1/ECgYA7Phspu8XBWOo5iDaToAk1
ALAgwKD/aKxMPmtO2ZhO/r7X16zXIsG84BZVPRuA6F+PYOx/4v2tmehn4mO/HcKM
b2ANw8GIlEykU/8DuBZY+SykilQwK5xCIT7mDC+lx+DebG6//G2uLoqh+d/vb+7d
drnvTMPz7EZsdAF2CSbN8wKBgBRom2j23AmvpAfYHQFqxHpP20aW4dn6zB9g4UsW
3zfv8bnJRtpCEQtiTdcc6LuYJXt0xBz5nP+UULA9V4QPvYZNXPEX3E+Pw1LxSd/A
cc3cFK+YEvektDOotBRn/t7NdfR7ju0wJ/d0KrXamDbI2bIeNzD3aWRWIr236X2R
FA6RAoGBAII5fdIo7oq8D2PIOnw6w+njz90PMzEdcMmXYb42hkaZBCk4CmxYaf6+
M8CAZ+HPyXARsan09Pvc6bviH2DuBtBNUYkumqbYwkGG+SUDEX7tujiA/xHfrzAC
m2vtOcWmt5eEtm/FabxSSnr2kCNNkXuvz+jT3JUG7X0760Ugk4+f
-----END RSA PRIVATE KEY-----"""

private_key = serialization.load_pem_private_key(pem_key.encode("utf-8"), password=None)

private_numbers = private_key.private_numbers()

p = private_numbers.p
q = private_numbers.q

p_hex = hex(p)[2:]
q_hex = hex(q)[2:]

print(f"p in hex: {p_hex}")
print(f"q in hex: {q_hex}")

n = private_key.key_size // 8
public_numbers = private_key.public_key().public_numbers()
n = public_numbers.n

p_hardcoded = "d1fe829f21ca8abf3553d0faf1a66d6d1065432d8231f3ba7335907228d591e91fc1d69c1589f5e324721c27b886dbe8e6bcd4be04340398207ae18c2115d4a305c7d413df8ca8f06060a2efc618be679033efabf6155b48968c78f25467ba6b2c3a80866801cef5d59c49a1d6524e238d11bcb7c134294b35459347fe842983"

q_hardcoded = "f1ff57d874f40765608ca0db100fd5fe4161cc50fc029fb59f0e6fa0095ed9bfb1e52e9449f75a3f9c6155661fcc2a1b4f2b499661d29225e68cfe5e17379bdcbf2a7eabb845d9dffb06a94b5fcfc02b19e0723f1277372e7fbbaf986636f2d59dc87bcbe55fd06425b43101f681fda2e585381e7e6fca3a7257e00431e9d7f1"

p_match = p_hex.lower() == p_hardcoded.lower()
q_match = q_hex.lower() == q_hardcoded.lower()

assert p_match, "p does not match the hardcoded value"
assert q_match, "q does not match the hardcoded value"
