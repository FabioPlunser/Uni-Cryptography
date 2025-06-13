import time
import bisect # For binary search
from base64 import b64decode

# Assuming the encryption scheme is in 'toy_double_enc.py'
from toy_double_enc import KEY_LENGTH, encrypt, get_plaintext_ciphertext_couple

# --- Constants ---
KEY_PART_BITS = KEY_LENGTH * 8
TOTAL_KEY_SPACE_PER_PART = 1 << KEY_PART_BITS

# --- Helper Function (remains the same) ---
def xor_bytes(data, key):
    """Helper function for XORing byte strings."""
    if not key: return data
    if isinstance(key, str): key = key.encode("utf-8")
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])

# --- MITM Attack Function using Sorting and Binary Search ---

def perform_mitm_attack_binary_search(m, c2):
    """
    Performs MITM attack using sorting and binary search on one list.

    Args:
        m: Known plaintext (bytes).
        c2: Known final ciphertext (bytes).

    Returns:
        The found full key K (bytes) or None if not found.
    """
    forward_list = [] # Stores (c1_candidate, K1) tuples

    print(f"\nStarting MITM Attack (Sort & Binary Search)...")
    print(f"Key part size: {KEY_LENGTH} bytes ({KEY_PART_BITS} bits)")
    print(f"Keyspace per part: {TOTAL_KEY_SPACE_PER_PART}")

    # --- Step 1: Forward Pass (Plaintext -> Middle c1) ---
    print("Running Forward Step (populating list)...")
    start_time_fwd = time.time()
    for i in range(TOTAL_KEY_SPACE_PER_PART):
        k1_candidate = i.to_bytes(KEY_LENGTH, "big")
        c1_candidate = encrypt(m, k1_candidate)
        forward_list.append((c1_candidate, k1_candidate)) # Store tuple

    end_time_fwd = time.time()
    print(f"Forward list populated in {end_time_fwd - start_time_fwd:.2f} seconds.")
    print(f"List contains {len(forward_list)} intermediate states.")

    # --- Step 2: Sort the list based on c1 ---
    print("Sorting forward list...")
    start_time_sort = time.time()
    # Sort by the first element of the tuple (c1_candidate)
    forward_list.sort(key=lambda item: item[0])
    end_time_sort = time.time()
    print(f"Sorting completed in {end_time_sort - start_time_sort:.2f} seconds.")

    # --- Step 3: Backward Pass and Matching (Binary Search) ---
    print("Running Backward Step (binary searching sorted list)...")
    start_time_bwd = time.time()
    try:
        intermediate2 = b64decode(c2)
    except Exception as e:
        print(f"Error: Could not Base64 decode final ciphertext c2: {e}")
        return None

    found_key = None
    for i in range(TOTAL_KEY_SPACE_PER_PART):
        k2_candidate = i.to_bytes(KEY_LENGTH, "big")
        c1_target = xor_bytes(intermediate2, k2_candidate)

        # Perform binary search for c1_target in the sorted list
        # We search for a tuple starting with c1_target.
        # bisect_left finds the insertion point.
        index = bisect.bisect_left(forward_list, (c1_target, b'')) # Search based on c1

        # Check if the item at the found index actually matches our target c1
        if index < len(forward_list) and forward_list[index][0] == c1_target:
            # Match found!
            k1_found = forward_list[index][1] # Get the K1 from the tuple
            found_key = k1_found + k2_candidate
            end_time_bwd = time.time()
            print(f"\n>>> Match Found! <<<")
            print(f"Backward step found match in {end_time_bwd - start_time_bwd:.2f} seconds.")
            print(f"  K1 (from sorted list): {k1_found.hex()}")
            print(f"  K2 (from backward step): {k2_candidate.hex()}")
            print(f"  Full Key K: {found_key.hex()}")
            return found_key # Exit after first match

    # If loop finishes without finding a match
    end_time_bwd = time.time()
    print(f"Backward step completed in {end_time_bwd - start_time_bwd:.2f} seconds. No match found.")
    return None


# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 40)
    print("Generating known plaintext-ciphertext pair...")
    plaintext, ciphertext = get_plaintext_ciphertext_couple()
    print("=" * 40)

    # Run the attack
    attack_start_time = time.time()
    found_key = perform_mitm_attack_binary_search(plaintext, ciphertext)
    attack_end_time = time.time()
    print("=" * 40)

    # Report results (same as before)
    if found_key:
        print(f"Attack successful! Total time: {attack_end_time - attack_start_time:.2f} seconds.")
        print(f"Found Key: {found_key.hex()}")

        print("\nVerifying found key by re-encrypting...")
        k1_check = found_key[:KEY_LENGTH]
        k2_check = found_key[KEY_LENGTH:]
        c1_reencrypt = encrypt(plaintext, k1_check)
        c2_reencrypt = encrypt(c1_reencrypt, k2_check)

        if c2_reencrypt == ciphertext:
            print("Verification successful: Re-encryption yields original ciphertext.")
        else:
            print("Verification FAILED: Re-encryption did not yield original ciphertext.")
            print(f"  Expected c2: {ciphertext}")
            print(f"  Calculated c2: {c2_reencrypt}")
    else:
        print(f"Attack failed after {attack_end_time - attack_start_time:.2f} seconds. Key not found.")
    print("=" * 40)
