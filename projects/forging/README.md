# Forging Project

by Fabio Plunser & Cedric Sillaber

## Introduction
This project demonstrates three critical vulnerabilities in DSA implementations that allow certificate forgery without access to the private key. These attacks highlight the importance of proper nonce generation and secure hash functions in digital signature schemes.

# Case 1 
In this case the nonce is the same for both messages. This flaw can be used to calculate the secret $x_a$ and therefore forge the certificate.

The two different messages are $m_1$ and $m_2$, and their corresponding hashes $H(m_1)$ and $H(m_2)$. <br/>

The parameters $(r_1, s_1), (r_2, s_2)$ are known, both can be calculated by using the equation defined in the slides:

$r_i = (g^k \pmod p) \pmod q$

From the above equation it follows that $r_1 = r_2$
We will refer to this common value as $r$. This is confirmed in the code with the assertion r1 == r2.


The equations for $s_1$ and $s_2$ are:<br/>
\[
s_i = \frac{1}{k}(H(m_i) + x_a r) \pmod q
\]
\[
\Leftrightarrow  k = \frac{H(m_i) + x_a \cdot r}{s_i} \pmod q
\]

Setting $k = k$:
\[
0 = k - k = \frac{H(m_1) + x_a r}{s_1} - \frac{H(m_2) + x_a r}{s_2} \pmod q
\]

Multiplying through by $s_1 s_2$:
\[
0 = s_2(H(m_1) + x_a r) - s_1(H(m_2) + x_a r) \pmod q
\]
\[
0 = s_2 H(m_1) + x_a r s_2 - s_1 H(m_2) - x_a r s_1 \pmod q
\]

\[
0 = s_2 H(m_1) - s_1 H(m_2) + x_a r(s_2 - s_1) \pmod q
\]

Rearranging:
\[
x_a r(s_1 - s_2) = s_2 H(m_1) - s_1 H(m_2) \pmod q
\]

\[
x_a = \frac{s_2 H(m_1) - s_1 H(m_2)}{r(s_1 - s_2)} \pmod q
\]


This formula corresponds to the Python code:<br/>
```python
x_a = ((s2 * intMESSAGE1 - s1 * intMESSAGE2) * pow(r * (s1 - s2), -1, public_key["q"])) % public_key["q"]
```


# Case 2

In this scenario the nonce for the second message is derived from the nonce of the first message in a deterministic manner.
This allows us to exploit the relationship between the two nonces to derive the private key.


The formula for the new nonce 
\[
    k_2 = 3k_1 + 5 \pmod q
    \Leftrightarrow k_1 = \frac{k_2-5 } {3} \pmod{q}
\]

Here the rationale for the attack is similar to case 1. 
From $s₁ = k_1^{-1}(H(m_1) + x_a r_1) \pmod q$, we get:
\[
k_1 = (H(m_1) + x_a r_1)/s_1 \pmod q
\]
Therefore:
\[
\frac{k_2 - 5}{3} = \frac{H(m_1) + x_a r_1}{s_1} \pmod{q}
\]

<!-- We denote all the variables the same as in case 1, except the key, as we have two different keys $k, k'$ here. -->
Given the deterministic relationship $k_2 = 3k_1 + 5$, we can eliminate the unknown nonces and solve for x_a:

\[
\frac{1}{3}\left(s_2^{-1}(H(m_2) + x_a r_2) - 5\right) - (H(m_1) + x_a r_1)s_1^{-1} \pmod q = 0
\]

\[
\frac{(H(m_2) + x_a r_2) - 5s_2}{3s_2} - \frac{H(m_1) + x_a r_1}{s_1} \pmod q = 0
\]

\[
\frac{((H(m_2) + x_a r_2) - 5s_2)s_1 - 3s_2(H(m_1) + x_a r_1)}{3s_2 s_1} \pmod q= 0
\]

\[
H(m_2)s_1 + x_a r_2 s_1 - 5s_2 s_1 - 3s_2 H(m_1) - 3s_2 x_a r_1 \pmod q = 0
\]

\[
\frac{H(m_2)s_1 - 5s_2 s_1 - 3s_2 H(m_1)}{3s_2 r_1 - r_2 s_1} \pmod q = x_a
\]

\[
x_a = \frac{s_1 H(m_2) - 5s_2 s_1 - 3s_2 H(m_1)}{3s_2 r_1 - r_2 s_1} \pmod q
\]


This corresponds to the private key that can therefore be used to forge a certificate for the public key.



# Case 3
The hash function is vulnerable. Cert can be created from the public key which passes verification.
This attack exploits the reversible hash function implementation. Instead of breaking the private key, we forge a signature by:
1. Choosing random values $u_1, u_2$
2. Computing a valid $(r', s')$ pair
3. Finding a message that produces the required hash


Our approach is to guess randomly generate $u_1, u_2$. 
Then we calculate:

\[
r' = (g^{u_1} y^{u_2} \pmod p) \pmod q
\]
\[
s' = (r' \cdot u_2^{-1}) \pmod q
\]

Using those values and the known `IV` we compute the new `target_hash` 
$\text{targethash} = (u_1 \cdot s') \pmod q$

As the website has length of under 16 bytes, we can simply decrypt using the `IV`. 

```python
verified = False
forged_message = None
attempts = 0
while forged_message is Nonenpm installnpm installnpm install:
    r_new = 0
    s_new = 0
    u1 = 0
    u2 = 0
    # attempts += 1

    while r_new == 0 or s_new == 0:
        u1 = random.randint(1, q - 1)
        u2 = random.randint(1, q - 1)

        # (g^u1 * y^u2 mod p) mod q
        term1 = pow(g, u1, p)
        term2 = pow(y, u2, p)
        r_new = (term1 * term2 % p) % q

        if r_new == 0:
            continue

        # r * u2^-1 mod q
        s_new = (r_new * pow(u2, -1, q)) % q


    target_hash = (u1 * s_new) % q
    target_hash_bytes = long_to_bytes(target_hash, AES.block_size)

    IV = b"this_is_the_iv02"
    cipher_new = AES.new(IV, AES.MODE_ECB).decrypt(target_hash_bytes)

    try:
        forged_message = unpad(cipher_new, AES.block_size)
    except ValueError:
        continue

```

# Optional 
The optional part of the project is to implement a solution that is not susceptible to the attacks described above. 

Because Case 3 has already solved the nonce issue by using random nonces but with a problematic hash function, we took the 
code from Case 3 and changed the hash function to SHA256.



