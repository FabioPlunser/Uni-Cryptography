# Import the bisect module
import bisect 

# Call the module and provide the array and the target value

from toy_double_enc import *

def search_key(T1_texts, element):
    index = bisect.bisect_left(T1_texts, element) 
    return index


m,c = get_plaintext_ciphertext_couple()

T1 = []
T1_only_texts = []
# adding elements to the table T1
for i in range(2**(8*KEY_LENGTH)):
    key = bytes.fromhex(hex(i)[2:].zfill(2*KEY_LENGTH))
    encrypted = encrypt(m,key)
    T1.append((encrypted, key))
    T1_only_texts.append(encrypted)

print("Sorting T1...")
T1.sort(key=lambda x: x[0])
T1_only_texts.sort()

print("Running the attack...")
T1_len = len(T1)

for i in range(2**(8*KEY_LENGTH)):
    key = bytes.fromhex(hex(i)[2:].zfill(2*KEY_LENGTH))
    value = decrypt(c, key)
    index = search_key(T1_only_texts, value)
    if index < T1_len and T1[index][0] == value:
        key1 = T1[index][1] + key
        found_key = key1
        break

print(found_key)
assert encrypt(encrypt(m, found_key[:KEY_LENGTH]), found_key[KEY_LENGTH:]) == c

print(found_key)
