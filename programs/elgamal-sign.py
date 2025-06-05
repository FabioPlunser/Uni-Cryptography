import random 
from Crypto.Util.number import getPrime, GCD, bytes_to_long
from hashlib import sha256

class ElGamal: 
    def __init__(self, BITS_PRIME):
        self.q = getPrime(BITS_PRIME)
        self.g = random.randint(2, self.q - 1)
        self.x = random.randint(2, self.q - 1)
        self.h = pow(self.g, self.x, self.q)
    
    def sign(self, message):
      y = random.randint(2, self.q - 1)
      while GCD(y, self.q - 1) != 1:
        y = random.randint(2, self.q - 1)

      y_inv = pow(y, -1, self.q - 1)    
      sigma_1 = pow(self.g, y, self.q)
      hashed_message = bytes_to_long(sha256(message.encode()).digest())
      sigma_2 = (hashed_message - self.x * sigma_1) * y_inv % (self.q - 1)

      assert sigma_2 != 0
      return sigma_1, sigma_2

    def verify(self, message, signature):
        sigma_1, sigma_2 = signature
        H = sha256(message.encode()).digest()
        H = bytes_to_long(H)

        eq1 = pow(self.h, sigma_1, self.q) * pow(sigma_1, sigma_2, self.q) % self.q
        eq2 = pow(self.g, H, self.q)

        return eq1 == eq2
  
if __name__ == "__main__":    
    elgamal = ElGamal(512)
    
    message = "Hello, this is a test message!"
    
    signature = elgamal.sign(message)
    
    print(f"Message: {message}")
    print(f"Signature: {signature}")
    print(f"Verification: {elgamal.verify(message, signature)}")