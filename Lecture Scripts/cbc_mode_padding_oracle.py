import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from pwn import xor


class EncryptionService:
    def __init__(self):
        self.key = os.urandom(16)

    def give_me_an_encrypted_message(self):
        ### CBC Padding Oracle
        message = b'We are showing the padding oracle attack'
        iv = os.urandom(16)
        padded_message = pad(message, AES.block_size, style='pkcs7')

        print(f"Our target plaintext will be: {padded_message}")

        cipher = AES.new(self.key, AES.MODE_CBC, iv=iv )
        encrypted_message = cipher.encrypt(padded_message)
        return iv + encrypted_message # we return iv and ciphertext

    def decrypt(self, ciphertext, debug=False):
        iv = ciphertext[:16]
        ciphertext = ciphertext[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv=iv )
        padded_plaintext = cipher.decrypt(ciphertext)

        if debug:
            print(f"The result padded plaintext is: {padded_plaintext}")
        
        unpadded_plaintext = unpad(padded_plaintext, AES.block_size, style='pkcs7') # if the padding is wrong it raises an Exception
        return unpadded_plaintext

        

service = EncryptionService()


# The service gives us the ciphertext
ciphertext = service.give_me_an_encrypted_message()
print(f"The ciphertext is: {ciphertext}")

# divide it into blocks 
blocks_encrypted_message = [ ciphertext[i:i+16] for i in range(0, len(ciphertext), 16)]
n = len(blocks_encrypted_message)

# plaintext = b''


# Before decryption, we must flip the last byte of the (n-1)th ciphertext block. We want to obtain a valid padding of 1 byte. Hence, we must force the decrypted plaintext to end with 0x01.  

### 'a' is the last byte of the intermediate block after the AES decryption of the last ciphertext block (recall what we wrote on the board)

### 'b' is the last byte of the (n-1)th ciphertext block

### 'c' is the last character of the original padded plaintext

### We want to obtain 0x01 at the end. Originally we have 
# 'a' xor 'b' = 'c'    We modify this equation to obtain 0x01 on the right side.
# '0x01 xor 'a' xor 'b' = 'c' xor 0x01
# c xor 0x01 xor 'a' xor 'b' = 'c' xor 0x01 xor 'c'
# c xor 0x01 xor 'a' xor 'b' =  0x01

### We don't know the exact value of 'c'. Recall that our objective is to find that 'c'.
### 'b' comes from the (n-1)th ciphertext block, therefore we have full control on it.
### 'a' comes from the AES decryption, therefore we have NOT control over it.
### 'c' can be bruteforced (exhaustive searched). How many possibilities? 2^8 = 256
### The above equation can be written in the following way:
### (c xor 0x01 xor 'b') xor 'a' =  0x01
### The last byte of the (n-1)th ciphertext block will assume the value in the parenthesis


print("EXAMPLE WITH 1 BYTE")
# EXAMPLE with 1 byte
# why we are not considering the value 0? Because it will always work if we are searching for the last byte of the entire padded plaintext. 

# why we should skip the value 1, because otherwise we get 'b' again as before. Hence, it will always work if we are searching for the last byte of the entire padded plaintext. 
for c in range(2, 256):
    desired_padding = b'\x01'
    
    C = c.to_bytes(byteorder='big')
    B = blocks_encrypted_message[n-2][15].to_bytes(byteorder='big') # in python if you extract a single byte it is considered as an integer
    new_value = xor(xor(C,B), desired_padding) # the value in the parenthesis 
    new_block = blocks_encrypted_message[n-2][:15] + new_value

    try:    
        unpadded_plaintext = service.decrypt(b''.join(blocks_encrypted_message[:n-2]+[new_block]+blocks_encrypted_message[n-1:]), debug=False)
        print(f"Successfull! The original value of the last plaintext byte is {C}")
        break
    except:
        continue # this means that the padding was WRONG



print()
print("COMPLETE PADDING ORACLE ATTACK")
# The same can be extended to recover all the plaintext. 
# Notice that at each time, we are taking into consideration only 2 ciphertext blocks. 
complete_plaintext = b''


for i in range(0, n-1):
    block1 = blocks_encrypted_message[i] # the one we will modify (previously it was the (n-1)th)
    block2 = blocks_encrypted_message[i+1]

    current_plaintext = b''

    for _ in range(16): # the number of bytes you are searching for in each block
        start_index = 0
        if i == n-2:
            start_index = 2 # recall what we have said before about why we are skipping certain values at the end

        for c in range(start_index, 256):
            desired_padding = ((len(current_plaintext)+1).to_bytes(byteorder='big'))*(len(current_plaintext)+1)

            # in this case we have to consider also that already discovered bytes
            C = c.to_bytes(byteorder='big')+current_plaintext
            B = block1[-(len(current_plaintext)+1):]

            new_value = xor(xor(C,B), desired_padding) # the value in the parenthesis 
            new_block = block1[:-(len(current_plaintext)+1)] + new_value

            try:    
                unpadded_plaintext = service.decrypt(b''.join([new_block, block2]), debug=False)
                # print(f"Successfull! The original value of the last plaintext byte is {C}")
                current_plaintext = C
                break
            except:
                continue # this means that the padding was WRONG

    complete_plaintext += current_plaintext

recovered_padded_plaintext = complete_plaintext
print(f"The resulting plaintext is {unpad(recovered_padded_plaintext, AES.block_size, style='pkcs7')}")

