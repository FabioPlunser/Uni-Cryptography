import random
from Crypto.Util.number import getPrime, GCD, bytes_to_long


BITS_PRIME = 1024


#### Basic implementation
class ElGamal:
    """
    It generates the necessary parameters
    """
    def __init__(self): 
        self.q = getPrime(BITS_PRIME)
        self.g = 3

    

    """
    It generates the public and private key
    """
    def keygen(self):
        self.x = random.randint(1, self.q-1) # private key
        self.h = pow(self.g, self.x, self.q)
        

    """
    It signs a message
    """
    def sign(self, message, y,  f):
        # y = random.randint(1, self.q-2)
        # while GCD(y, self.q-1) != 1 or y == 0:
        #     y = random.randint(1, self.q-2)
        assert GCD(y, self.q-1) == 1

        sigma_1 = pow(self.g, y, self.q)
        hashed_message = bytes_to_long(f(bytes.fromhex(message['name']+message['website']+message['expdate'])))
        sigma_2 = ((hashed_message - self.x*sigma_1)*pow(y, -1, self.q -1)) % (self.q-1)

        assert sigma_2 != 0
        return sigma_1, sigma_2

    """
    It verifies a message
    """
    def verify(self, message, signature, f):

        sigma_1, sigma_2 = signature
        assert sigma_2 != 0
        
        hashed_message = bytes_to_long(f(bytes.fromhex(message['name']+message['website']+message['expdate'])))


        eq1 = (pow(self.h, sigma_1, self.q) * pow(sigma_1, sigma_2, self.q)) % self.q

        eq2 = pow(self.g, hashed_message, self.q)

        return eq1 == eq2
        

