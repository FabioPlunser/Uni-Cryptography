import random
from Crypto.Util.number import getPrime, GCD, bytes_to_long, isPrime


class DSA:
    """
    It generates the necessary parameters
    """

    def __init__(self):
        self.p = 0
        while not isPrime(self.p):
            self.q = getPrime(128)
            self.p = 2 * self.q + 1

        self.h = 2
        self.g = pow(self.h, (self.p - 1) // self.q, self.p)

        while self.g == 1:
            self.h = random.randint(2, self.p - 2)
            self.g = pow(self.h, (self.p - 1) // self.q, self.p)
        self.x = None
        self.y = None

    """
    It generates the public and private key
    """

    def keygen(self):
        self.x = random.randint(1, self.q - 1)
        self.y = pow(self.g, self.x, self.p)

    """
    It signs a message
    """

    def sign(self, message, k, f):
        assert GCD(k, self.q) == 1
        r = pow(self.g, k, self.p) % self.q
        if r == 0:  # Recalculate k if r is 0, very rare
            # This basic retry might not be robust enough for all edge cases
            # but fits "simple" and "touch as little as possible"
            new_k = random.randint(1, self.q - 1)
            while GCD(new_k, self.q) != 1 or new_k == 0:
                new_k = random.randint(1, self.q - 1)
            return self.sign(message, new_k, f)

        hashed_message_long = bytes_to_long(
            f(bytes.fromhex(message["name"] + message["website"] + message["expdate"]))
        )

        try:
            k_inv = pow(k, -1, self.q)
        except (
            ValueError
        ):  # k is not invertible mod q (should not happen if GCD check passed and q is prime)
            new_k = random.randint(1, self.q - 1)
            while GCD(new_k, self.q) != 1 or new_k == 0:
                new_k = random.randint(1, self.q - 1)
            return self.sign(message, new_k, f)

        s = ((hashed_message_long + self.x * r) * k_inv) % (self.q)
        if s == 0:  # Recalculate k if s is 0
            new_k = random.randint(1, self.q - 1)
            while GCD(new_k, self.q) != 1 or new_k == 0:
                new_k = random.randint(1, self.q - 1)
            return self.sign(message, new_k, f)

        assert s != 0
        return r, s

    """
    It verifies a message
    """

    def verify(self, message, signature, f):
        r, s = signature
        if not (0 < r < self.q and 0 < s < self.q):
            return False

        hashed_message_long = bytes_to_long(
            f(bytes.fromhex(message["name"] + message["website"] + message["expdate"]))
        )

        try:
            s_inv = pow(s, -1, self.q)
        except ValueError:  # s is not invertible mod q
            return False

        u1 = (hashed_message_long * s_inv) % self.q
        u2 = (r * s_inv) % self.q

        v = ((pow(self.g, u1, self.p) * pow(self.y, u2, self.p)) % self.p) % self.q

        return v == r
