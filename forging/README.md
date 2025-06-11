# Case 1 
Nonce is the same for both certificates. Can get the private key

Let's denote the two different messages as $m_1$ and $m_2$, and their corresponding hashes as $H(m_1)$ and $H(m_2)$. <br/>
Since the same private key $x_a$ and nonce $k$ are used, we get two different signatures, $(r_1, s_1)$ and $(r_2, s_2)$.

From the definition of $r$, we have:<br/>
$r_1 = (g^k \pmod p) \pmod q$<br/>
$r_2 = (g^k \pmod p) \pmod q$

Since $g$ and $k$ are the same for both signatures, it is necessary that $r_1 = r_2$. 

We will refer to this common value as $r$. This is confirmed in the code with the assertion r1 == r2.


The equations for $s_1$ and $s_2$ are:<br/>
$s_1 = k^{-1}(H(m_1) + x_a r) \pmod q$<br/>
$s_2 = k^{-1}(H(m_2) + x_a r) \pmod q$


1. Deriving the Nonce $k$
We can rearrange the equations for $s_1$ and $s_2$ by multiplying by $k$:<br/>
$k s_1 \equiv H(m_1) + x_a r \pmod q$<br/>
$k s_2 \equiv H(m_2) + x_a r \pmod q$<br/>
<br/>
Now we have a system of two linear equations with two unknowns, $k$ and $x_a$. <br/>
To find $k$, we can subtract the second equation from the first to eliminate $x_a$:<br/>
$k s_1 - k s_2 \equiv (H(m_1) + x_a r) - (H(m_2) + x_a r) \pmod q$<br/>
$k(s_1 - s_2) \equiv H(m_1) - H(m_2) \pmod q$<br/>
<br/>
<br/>
We can now solve for $k$ by multiplying by the modular multiplicative inverse of $(s_1 - s_2)$:<br/>
$k \equiv (H(m_1) - H(m_2))(s_1 - s_2)^{-1} \pmod q$
<br/>
This formula corresponds to the Python code:<br/>
```python
k = ((intMESSAGE1 - intMESSAGE2) * pow(s1 - s2, -1, public_key["q"])) % public_key["q"]
```

2. Deriving the Private Key $x_a$<br/>
To find the private key $x_a$, we can use the same system of equations. <br/>
This time, we will eliminate $k$. <br/>
We can achieve this by multiplying the first equation by $s_2$ and the second equation by $s_1$:<br/>
$k s_1 s_2 \equiv s_2(H(m_1) + x_a r) \pmod q$<br/>
$k s_2 s_1 \equiv s_1(H(m_2) + x_a r) \pmod q$<br/>
<br/>
Since the left-hand sides are identical, we can set the right-hand sides equal to each other:<br/>
$s_2(H(m_1) + x_a r) \equiv s_1(H(m_2) + x_a r) \pmod q$<br/>
$s_2 H(m_1) + s_2 x_a r \equiv s_1 H(m_2) + s_1 x_a r \pmod q$<br/>
<br/>
Now, we group the terms containing $x_a$ on one side and the remaining terms on the other:<br/>
$s_2 H(m_1) - s_1 H(m_2) \equiv s_1 x_a r - s_2 x_a r \pmod q$<br/>
$s_2 H(m_1) - s_1 H(m_2) \equiv x_a r (s_1 - s_2) \pmod q$<br/>
<br/>
Finally, we can solve for $x_a$ by multiplying by the modular multiplicative inverse of $r(s_1 - s_2)$:<br/>
$x_a \equiv \frac{s_2 H(m_1) - s_1 H(m_2)}{r(s_1 - s_2)} \pmod q$<br/>
$x_a \equiv (s_2 H(m_1) - s_1 H(m_2))(r(s_1 - s_2))^{-1} \pmod q$<br/>
<br/>
This formula corresponds to the Python code:<br/>
```python
x = ((s2 * intMESSAGE1 - s1 * intMESSAGE2) * pow(r1 * (s1 - s2), -1, public_key["q"])) % public_key["q"]
```

# Case 2 
- Nonce 2 is derived from the nonce 1 in a deterministic way. Can get the private key


$r_1 = (g^k_1 \pmod p) \pmod q$<br/>
$r_2 = (g^k_2 \pmod p) \pmod q$

Now $k_2$ is derived from $k_1$ in a deterministic way. 
$k_2 = ( a \cdot k_1 + b ) \pmod q$ with $a=3$ and $b=5$.

THerefore we can derivce from $s_1$ and $s_2$ the nonce $k_2$ by multiplying by $k_2$:<br/>

The equations for $s_1$ and $s_2$ are:<br/>
$s_1 = k_1^{-1}(H(m_1) + x_a r) \pmod q$<br/>
$s_2 = k_2^{-1}(H(m_2) + x_a r) \pmod q$

- $k_2 s_1 \equiv H(m_1) + x_a r \pmod q$ \\
- $k_2 s_2 \equiv H(m_2) + x_a r \pmod q$

# Case 3
- The hash function is vulnerable. Cert can be created from the public key which passes verification