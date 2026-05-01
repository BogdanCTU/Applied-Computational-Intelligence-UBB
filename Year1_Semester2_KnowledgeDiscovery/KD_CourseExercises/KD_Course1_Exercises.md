# ✔️ Exercise Solutions — Formal Concept Analysis (FCA)

---

# 🔷 Exercise 1

## 📌 Given formal context K

Objects:
G = {Leech, Bream, Frog, Spike-Weed, Reed, Bean, Maize}

Attributes abbreviated:

- W = needs water to live  
- W_in = lives in water  
- L = lives on land  
- C = needs chlorophyll  
- 2L = two seed leaves  
- 1L = one seed leaf  
- M = can move around  
- Lim = has limbs  
- S = suckles offspring  

---

## 📍 1) {Bean}′

Bean has:
- W, L, C, 2L

✔️ Result:
{Bean}′ = {needs water to live, lives on land, needs chlorophyll, two seed leaves}

---

## 📍 2) {lives on land}′

Objects with L:
Frog, Reed, Bean, Maize

Common attributes:

✔️ Result:
{lives on land}′ = {needs water to live, lives on land}

---

## 📍 3) {two seed leaves}′′

Step 1:
{two seed leaves}′ = {Bean}

Step 2:
{Bean}′ = {W, L, C, 2L}

✔️ Result:
{two seed leaves}′′ = {needs water to live, lives on land, needs chlorophyll to produce food, two seed leaves}

---

## 📍 4) {Frog, Maize}′

Frog ∩ Maize attributes:

✔️ Result:
{Frog, Maize}′ = {needs water to live, lives on land}

---

## 📍 5) {needs chlorophyll, can move around}′

Check objects having BOTH C and M:

- Spike-Weed (C only)
- Reed (C only)
- Bean (C only)
- Maize (C only)
- Leech/Bream/Frog (M only)

No intersection.

✔️ Result:
{needs chlorophyll to produce food, can move around}′ = ∅

---

## 📍 6) {lives in water, lives on land}′

Objects satisfying BOTH:
Frog, Reed

Common attributes:

✔️ Result:
{lives in water, lives on land}′ = {needs water to live, lives in water, lives on land}

---

## 📍 7) Repeated set

Same as (5)

✔️ Result:
∅

---

## 📌 1b) Extend K with one object + one attribute

Example extension:

- New object: Duck  
- New attribute: can swim and fly  

Extended assignments:
- Duck: W, W_in, L, M, Lim (partial overlap depending on modeling choice)
- New attribute links: Duck, Frog, Bream

✔️ Purpose: increases lattice granularity and introduces hybrid mobility concept

---

# 🔷 Exercise 2

## 📍 a) Derivation operator definition

Let K = (G, M, I)

For A ⊆ G:
A′ = { m ∈ M | ∀ g ∈ A : (g, m) ∈ I }

For B ⊆ M:
B′ = { g ∈ G | ∀ m ∈ B : (g, m) ∈ I }

---

## 📍 b1) A ⊆ B ⇒ B′ ⊆ A′

If A ⊆ B, then B has fewer constraints than A.

Any attribute shared by all objects in B is necessarily shared by all objects in A.

✔️ Therefore:
B′ ⊆ A′

---

## 📍 b2) A ⊆ A′′

A′ = attributes common to A  
A′′ = objects sharing all those attributes

Every object in A satisfies its own derived intent.

✔️ Therefore:
A ⊆ A′′ (extensivity property)

---

## 📍 b3) A′ = A′′′

Using Galois connection:

- A → A′ (objects → attributes)
- A′ → A′′ (closure back to objects)
- A′′ → A′′′ (back to attributes again)

Closure stabilizes after 3 applications.

✔️ Therefore:
A′ = A′′′

---

## 📍 b4) Characterization of formal concepts

A pair (C, D) is a formal concept iff:

- C = E′′
- D = E′
for some E ⊆ G

✔️ Interpretation:

- E′ generates shared attributes
- E′′ restores maximal object set consistent with those attributes

✔️ Therefore:
(C, D) is a formal concept ⇔ ∃E ⊆ G such that:
C = E′′ and D = E′

---