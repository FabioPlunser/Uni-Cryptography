import time
from base64 import b64decode
from toy_double_enc import KEY_LENGTH, encrypt, get_plaintext_ciphertext_couple

KEY_PART_BITS = KEY_LENGTH * 8  # 2 * 8 = 16 bits
TOTAL_KEY_SPACE_PER_PART = 1 << KEY_PART_BITS  # 2^16 = 65536


def xor_bytes(data, key):
    """Helper function for XORing byte strings."""
    if not key:
        return data

    if isinstance(key, str):
        key = key.encode("utf-8")
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])


def perform_mitm_attack(m, c2):
    """
    Performs MITM attack using the imported encrypt function.

    Args:
        m: Known plaintext (bytes).
        c2: Known final ciphertext (bytes).

    Returns:
        The found full key K (bytes) or None if not found.
    """
    forward_map = {}  # Stores {c1_candidate: K1}

    print(f"\nStarting MITM Attack...")
    print(f"Key part size: {KEY_LENGTH} bytes ({KEY_PART_BITS} bits)")
    print(f"Keyspace per part: {TOTAL_KEY_SPACE_PER_PART}")

    # --- Step 1: Forward Pass (Plaintext -> Middle c1) ---
    # Calculate c1 = encrypt(m, K1) for all possible K1
    print("Running Forward Step (using encrypt(m, K1))...")
    start_time_fwd = time.time()
    for i in range(TOTAL_KEY_SPACE_PER_PART):
        k1_candidate = i.to_bytes(KEY_LENGTH, "big")  # K1 guess (bytes)
        # Use the imported encrypt function
        c1_candidate = encrypt(m, k1_candidate)
        forward_map[c1_candidate] = k1_candidate  # Store: c1 -> K1

    end_time_fwd = time.time()
    print(f"Forward step completed in {end_time_fwd - start_time_fwd:.2f} seconds.")
    print(f"Stored {len(forward_map)} intermediate ciphertexts (c1 candidates).")

    # --- Step 2 & 3: Backward Pass and Matching (Ciphertext -> Middle c1) ---
    # Calculate c1_target = XOR(b64decode(c2), K2) for all possible K2
    # and check if c1_target is in forward_map
    print("Running Backward Step (reversing encrypt(c1, K2) and checking map)...")
    start_time_bwd = time.time()
    try:
        # Need the result *before* base64 encoding in the second step
        intermediate2 = b64decode(c2)
    except Exception as e:
        print(f"Error: Could not Base64 decode the final ciphertext c2: {e}")
        return None

    for i in range(TOTAL_KEY_SPACE_PER_PART):
        k2_candidate = i.to_bytes(KEY_LENGTH, "big")  # K2 guess (bytes)

        # Reverse the second encryption step: c2 = encrypt(c1, K2)
        # encrypt does XOR then Base64. So c2 = B64(XOR(c1, K2))
        # Reversing: intermediate2 = b64decode(c2) = XOR(c1, K2)
        # Therefore: c1_target = XOR(intermediate2, K2)
        c1_target = xor_bytes(intermediate2, k2_candidate)

        # Check if this calculated c1_target exists in our forward map
        if c1_target in forward_map:
            k1_found = forward_map[c1_target]
            found_key = k1_found + k2_candidate  # Combine K1 and K2
            end_time_bwd = time.time()
            print(f"\n>>> Match Found! <<<")
            print(
                f"Backward step found match in {end_time_bwd - start_time_bwd:.2f} seconds."
            )
            print(f"  K1 (from forward map): {k1_found.hex()}")
            print(f"  K2 (from backward step): {k2_candidate.hex()}")
            print(f"  Full Key K: {found_key.hex()}")
            return found_key

    end_time_bwd = time.time()
    print(
        f"\nBackward step completed in {end_time_bwd - start_time_bwd:.2f} seconds. No match found."
    )
    return None


# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 40)
    print("Generating known plaintext-ciphertext pair using provided functions...")
    # Use the imported function to get a test case
    plaintext, ciphertext = get_plaintext_ciphertext_couple()
    print("=" * 40)

    # Run the attack
    attack_start_time = time.time()
    found_key = perform_mitm_attack(plaintext, ciphertext)
    attack_end_time = time.time()
    print("=" * 40)

    # Report results
    if found_key:
        print(
            f"Attack successful! Total time: {attack_end_time - attack_start_time:.2f} seconds."
        )
        print(f"Found Key: {found_key.hex()}")

        print("\nVerifying found key by re-encrypting...")
        k1_check = found_key[:KEY_LENGTH]
        k2_check = found_key[KEY_LENGTH:]
        c1_reencrypt = encrypt(plaintext, k1_check)
        c2_reencrypt = encrypt(c1_reencrypt, k2_check)

        if c2_reencrypt == ciphertext:
            print("Verification successful: Re-encryption yields original ciphertext.")
        else:
            print(
                "Verification FAILED: Re-encryption did not yield original ciphertext."
            )
            print(f"  Expected c2: {ciphertext}")
            print(f"  Calculated c2: {c2_reencrypt}")
    else:
        print(
            f"Attack failed after {attack_end_time - attack_start_time:.2f} seconds. Key not found."
        )
    print("=" * 40)
