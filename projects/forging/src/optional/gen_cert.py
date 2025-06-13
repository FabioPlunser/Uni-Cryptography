import json
import random
from Crypto.Hash import SHA256
from Crypto.Util.number import GCD  # For nonce generation

# Import the DSA class from the separate file
from dsa import DSA


def gen_keys_secure():
    signature_scheme = DSA()
    signature_scheme.keygen()
    public_key = {
        "q": signature_scheme.q,
        "p": signature_scheme.p,
        "g": signature_scheme.g,
        "y": signature_scheme.y,
    }

    private_key = {
        "q": signature_scheme.q,
        "p": signature_scheme.p,
        "g": signature_scheme.g,
        "x": signature_scheme.x,
    }

    with open("public_key_secure.txt", "w") as pk_file:
        json.dump(public_key, pk_file)

    with open("private_key_secure.txt", "w") as sk_file:
        json.dump(private_key, sk_file)

    return signature_scheme


def gen_certificate_data_secure(
    username: bytes, website_name: bytes, expiration_date: bytes
):
    cert_data = {
        "name": username.hex(),
        "website": website_name.hex(),
        "expdate": expiration_date.hex(),
    }
    return cert_data


def sign_certificate_secure(signature_scheme: DSA, original_cert_data: dict):
    canonical_json_bytes = json.dumps(
        original_cert_data, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    hex_encoded_canonical_json = canonical_json_bytes.hex()

    data_for_dsa_sign_method = {
        "name": hex_encoded_canonical_json,
        "website": "",
        "expdate": "",
    }

    nonce = random.randint(1, signature_scheme.q - 1)
    while GCD(nonce, signature_scheme.q) != 1 or nonce == 0:
        nonce = random.randint(1, signature_scheme.q - 1)

    hash_wrapper = lambda data_bytes: SHA256.new(data_bytes).digest()

    r, s = signature_scheme.sign(data_for_dsa_sign_method, nonce, hash_wrapper)

    signed_cert = original_cert_data.copy()
    signed_cert["r"] = r
    signed_cert["s"] = s

    return json.dumps(signed_cert)


def verify_certificate_secure(public_params: dict, signed_certificate_json: str):
    signed_cert_dict = json.loads(signed_certificate_json)

    r = signed_cert_dict.pop("r")
    s = signed_cert_dict.pop("s")
    original_cert_data = signed_cert_dict

    canonical_json_bytes = json.dumps(
        original_cert_data, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    hex_encoded_canonical_json = canonical_json_bytes.hex()
    data_for_dsa_verify_method = {
        "name": hex_encoded_canonical_json,
        "website": "",
        "expdate": "",
    }

    hash_wrapper = lambda data_bytes: SHA256.new(data_bytes).digest()

    verifier = DSA()
    verifier.p = public_params["p"]
    verifier.q = public_params["q"]
    verifier.g = public_params["g"]
    verifier.y = public_params["y"]

    return verifier.verify(data_for_dsa_verify_method, (r, s), hash_wrapper)


if __name__ == "__main__":
    print("Generating new secure keys...")
    sig_scheme = gen_keys_secure()
    print(f"Keys generated. Public key y: {sig_scheme.y}, q: {sig_scheme.q}")

    print("\nGenerating and signing certificate 1 (securely)...")
    cert_data1 = gen_certificate_data_secure(
        b"alice_secure", b"https://alice-secure.com", b"01/01/2028"
    )
    signed_cert1_json = sign_certificate_secure(sig_scheme, cert_data1)
    print(f"Signed Certificate 1: {signed_cert1_json}")

    with open("certificate_secure_1.txt", "w") as f:
        f.write(signed_cert1_json)

    print("\nGenerating and signing certificate 2 (securely)...")
    cert_data2 = gen_certificate_data_secure(
        b"bob_secure", b"https://bob-secure.org", b"06/15/2029"
    )
    signed_cert2_json = sign_certificate_secure(sig_scheme, cert_data2)
    print(f"Signed Certificate 2: {signed_cert2_json}")

    with open("certificate_secure_2.txt", "w") as f:
        f.write(signed_cert2_json)

    # --- Verification Example ---
    print("\nVerifying certificate 1...")
    with open("public_key_secure.txt", "r") as pk_file:
        public_params_loaded = json.load(pk_file)

    is_valid1 = verify_certificate_secure(public_params_loaded, signed_cert1_json)
    print(f"Certificate 1 verification result: {is_valid1}")

    print("\nVerifying certificate 2...")
    is_valid2 = verify_certificate_secure(public_params_loaded, signed_cert2_json)
    print(f"Certificate 2 verification result: {is_valid2}")

    # Tamper attempt (should fail verification)
    print("\nAttempting to verify a tampered certificate...")
    tampered_cert_dict = json.loads(signed_cert1_json)
    original_name_hex = tampered_cert_dict["name"]
    tampered_cert_dict["name"] = b"mallory_hacker".hex()  # Change name
    tampered_cert_json = json.dumps(tampered_cert_dict)

    is_tampered_valid = verify_certificate_secure(
        public_params_loaded, tampered_cert_json
    )
    print(f"Tampered certificate verification result: {is_tampered_valid}")

    # Restore original name for another test
    tampered_cert_dict["name"] = original_name_hex
    # Tamper signature
    tampered_cert_dict["s"] = (tampered_cert_dict["s"] + 1) % sig_scheme.q
    if tampered_cert_dict["s"] == 0:
        tampered_cert_dict["s"] = 1  # ensure s !=0
    tampered_sig_json = json.dumps(tampered_cert_dict)
    print("\nAttempting to verify a certificate with tampered signature...")
    is_tampered_sig_valid = verify_certificate_secure(
        public_params_loaded, tampered_sig_json
    )
    print(f"Tampered signature verification result: {is_tampered_sig_valid}")
