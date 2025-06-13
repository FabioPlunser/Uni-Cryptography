from toy_double_enc import *

def search_key(T1, T2):
    for el_t1 in T1:
        for el_t2 in T2:
            if el_t1[0] == el_t2[0]:
                found_key = el_t1[1]+el_t2[1]
                print(f"Found key: {found_key}")
                return found_key
    
    print("Error")
            


m,c = get_plaintext_ciphertext_couple()

T1 = []
T2 = []

# adding elements to the tables
for i in range(2**(8*KEY_LENGTH)):
    key = bytes.fromhex(hex(i)[2:].zfill(2*KEY_LENGTH))

    T1.append((encrypt(m, key), key))
    T2.append((decrypt(c, key), key))

print("Running the attack...")
found_key = search_key(T1, T2)

assert encrypt(encrypt(m, found_key[:KEY_LENGTH]), found_key[KEY_LENGTH:]) == c

print(found_key)