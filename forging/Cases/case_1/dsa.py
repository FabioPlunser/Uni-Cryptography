import random
from Crypto.Util.number import getPrime, GCD, bytes_to_long, isPrime




#### Basic implementation
class DSA:
    """
    It generates the necessary parameters
    """
    def __init__(self): 
        self.p = 0
        while not isPrime(self.p):
            self.q = getPrime(128)
            self.p = 2*self.q + 1

        self.h = 2
        self.g = pow(self.h, (self.p-1)//self.q, self.p)

        while self.g == 1: 
            self.h = random.randint(2, self.p-2)
            self.g = pow(self.h, (self.p-1)//self.q, self.p)
    


    """
    It generates the public and private key
    """
    def keygen(self):
        self.x = random.randint(1, self.q-1) # private key
        self.y = pow(self.g, self.x, self.p) # public key
        

    """
    It signs a message
    """
    def sign(self, message, k,  f):

        assert GCD(k, self.q) == 1

        r = pow(self.g, k, self.p) % self.q

        hashed_message = bytes_to_long(f(message))

        s = ((hashed_message + self.x*r)*pow(k, -1, self.q)) % (self.q)

       
        assert s != 0
        return r, s

    """
    It verifies a message
    """
    def verify(self, message, signature, f):

        r, s = signature
        assert s != 0
        
        hashed_message = bytes_to_long(f(message))

        temp = pow(s, -1, self.q)

        eq1 = (hashed_message*temp) % self.q
        eq2 = (r*temp) % self.q

        v = ((pow(self.g, eq1, self.p)*pow(self.y, eq2, self.p)) % self.p) % self.q

        return v == r
        

