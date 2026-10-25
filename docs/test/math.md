---
title: Math Rendering
tags: [math]
---

## Heading

Inline math uses round brackets: the energy is \(E = mc^2\) and the
element in row i, column j is \(a_{ij}\).

Angle brackets inside a formula: \(x<y\) and \(a > b\) should not be
treated as HTML.

Block math with double dollars:

$$
\sum_{i=1}^{n} \frac{a_{ij}}{b_{ij}} = \int_0^1 f(x)\,dx
$$

Block math with square brackets:

\[
A = \begin{pmatrix} a_{11} & a_{12} \\ a_{21} & a_{22} \end{pmatrix}
\]

## In lists and tables

- The mean is \(\bar{x} = \frac{1}{n}\sum_i x_i\)
- Variance: \(\sigma^2 = E[(X - \mu)^2]\)

| Name | Formula |
| ---- | ------- |
| Euler | \(e^{i\pi} + 1 = 0\) |
| Pythagoras | \(a^2 + b^2 = c^2\) |

## Escapes

Backslashes and underscores: \(\alpha\_1 + \beta_{2} \cdot \gamma\backslash\delta\).
