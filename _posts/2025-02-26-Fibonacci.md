---
title: 'Fibonacci and its generating function'
date: 2025-02-26
permalink: /posts/2025/02/Fibonacci/
tags:
  - Math
---

The Fibonacci function and its generating function.
===

$$
\mathscr F (z) = \sum_{i=0}^{\infty} F_i z^i = 0 + z + z^2 + 2z^3 + 3z^4 + 5z^5 + 8z^6 + \cdots
$$

1. Prove that the following equation holds for some $z$
    
    $$
    \mathscr F (z) = z + z \mathscr F (z) + z^2 \mathscr F(z)
    $$
    
    where $\phi = \frac{1+\sqrt{5}}{2}$ and $\hat \phi = \frac{1 - \sqrt{5}}{2}$.

    We know that 
    $$
    F_x = F_{x-1} + F_{x-2}, \forall x \geq 2, x \in N
    $$ 

    So:

    $$
    \begin{aligned}
    z + z\mathscr F (z) + z^2 \mathscr F(z) &= z + \sum_{i=0}^{\infty} F_i z^{i+1} + \sum_{i=0}^{\infty} F_i z^{i+2} \\
    &= z + \sum_{i=1}^{\infty} F_{i-1}z^i + \sum_{i=2}F_{i-2} z^i \\
    &= z + F_0 \cdot z + \sum_{i=2}^{\infty} (F_{i-1} + F_{i-2}) z^i \\
    &= z + \sum_{i=2}^{\infty} F_i z^i \\
    &= \mathscr F(z)
    \end{aligned}
    $$

2. Prove that
    $$
    \mathscr F (z) = \frac{z}{1 - z - z^2} = \frac{z}{(1 - \phi z)(1 - \hat\phi z)} = \frac{1}{\sqrt{5}} \left( \frac{1}{1 - \phi z} - \frac{1}{1 - \hat\phi z} \right)
    $$

    By working the equality in problem 1.

3. Prove that 
    
    $$
    \mathscr F(z) = \sum_{i = 0}^{\infty} \frac{1}{\sqrt{5}} (\phi^i - \hat{\phi}^i) z
    $$

    We can derive from $ F_x = F_{x-1} + F_{x-2} $
    that
    
    $$
    \begin{aligned}
    F_x + \frac{\sqrt{5}-1}{2} F_{x-1} =& {\left(\frac{1+\sqrt{5}}{2}\right)}^{x-1} \\
    F_x - \frac{\sqrt{5}+1}{2} F_{x-1} =& {\left(\frac{1-\sqrt{5}}{2}\right)}^{x-1}
    \end{aligned}
    $$

    then we have:
    
    $$
    \sqrt{5} F_{x-1} = \frac{(1+\sqrt{5})^{x-1} - (1 - \sqrt{5})^{x-1}}{2^{x-1}}
    $$
    
    i.e.
    
    $$
    F_{x} = \frac{(1+\sqrt{5})^x - (1 - \sqrt{5})^{x}}{2^x\sqrt{5}}
    $$

All that remains is the problem of finding the convergence domain of this function, which I will work out afterwards.