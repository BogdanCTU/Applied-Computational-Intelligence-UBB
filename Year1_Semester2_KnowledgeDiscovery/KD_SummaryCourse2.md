<!-- --------------------------------------------------------------- -->
<!-- ------------------------- COURSE 2 FCA ------------------------ -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 2 - Formal Concept Analysis (FCA)**

## 📖 2.1 Motivation and Background

🔴 **Formal Concept Analysis** (**FCA**) **is a mathematical method used to find natural groupings of items that share common properties**. It organizes these groups into a clear, **structured hierarchy** called a "**lattice**".

**Key Idea**: In FCA, a "**concept**" is made of two parts: the items it covers (its "extent") and the properties those items share (its "intent").

🔴 **Benefits**: **FCA turns complex data into easily readable summaries**, helps discover rules within data and is highly useful in fields like machine learning and biology.

| | has wings | can fly | has fur | warm-blood |
| :--- | :---: | :---: | :---: | :---: |
| Eagle | × | × | | × |
| Bat | × | × | × | × |
| Penguin | × | | | × |
| Dog | | | × | × |
| Salmon | | | | |

> ### Table: Sample 

---

## 📖 2.2 Formal Contexts

🔴 **The Formal Context is the basic data structure used to organize information in FCA**.
It is defined mathematically as a triplet $\mathbb{K}=(G,M,I)$:
* $G$ (Objects): The set of items or things you are studying, like different animals;
* $M$ (Attributes): The set of properties or features those items might have, like "has wings" or "can fly";
* $I$ (Incidence Relation): A simple rule that links an object to an attribute. If an object $g$ possesses an attribute $m$, we write $g|m$.

🔴 **The Cross Table is a visual grid used to display a formal context**. **The rows represent objects**, **the columns represent attributes**, and an "X" in a cell means the object has that specific attribute. Context Refinement:
* **Clarified Context**: A clean table where no two objects (rows) are identical, and no two attributes (columns) are identical;
* **Reduced Context**: An even simpler table where no row or column can be perfectly predicted by a combination of the others.

Cross Table Formal Context Sample:
* G = {Python, Java, C++, Haskell}
* M = {OOP, functional, typed, GC, compiled}

| | OOP | fun | typed | GC | cmp |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Python | × | × | | × | |
| Java | × | | × | × | × |
| C++ | × | | × | | × |
| Haskell | | × | × | × | × |

> ### Table: Cross Table for Software Features

---

## 📖 2.3 Derivation Operators

🔴 The **Derivation Operators** ($'$), also known as "**prime operators**", these are mathematical rules that let you translate between groups of objects and groups of attributes:
* **For a group of objects $A$**, the operation $A^{\prime}$ finds the specific attributes that every single object in group $A$ shares;
* **For a group of attributes $B$**, the operation $B^{\prime}$ finds the specific objects that possess every single attribute in group $B$.

🔴 **Key Properties of Derivation**:
* **Anti-monotone**: If you add more objects to your starting group, the number of attributes they all share will either stay the same or shrink. Mathematically: A₁ ⊆ A₂ ⇒ A₂' ⊆ A₁'
* **Extensive**: If you take a group of objects, find their shared attributes, and then find all objects with those attributes, your new group of objects will always include your starting group. Mathematically: A ⊆ A''
* **Idempotent**: Applying the prime operator three times gives the exact same result as applying it just once. Mathematically: A''' = A'

Let 𝕂 = (G, M, I), A, A₁, A₂ ⊆ G, B, B₁, B₂ ⊆ M. Then:
- P1  A₁ ⊆ A₂ ⇒ A₂' ⊆ A₁' ⇒ (_anti-monotone_)
- P2  B₁ ⊆ B₂ ⇒ B₂' ⊆ B₁' ⇒ (_anti-monotone_)
- P3  A ⊆ A'' ⇒ (_extensive_)
- P4  B ⊆ B'' ⇒ (_extensive_)
- P5  A''' = A' ⇒ (_idempotent under double prime_)
- P6  B''' = B' ⇒ (_idempotent under double prime_)
- P7  (A₁ ∪ A₂)' = A₁' ∩ A₂'
- P8  (B₁ ∪ B₂)' = B₁' ∩ B₂'

The **Closure Operator** ($^{\prime\prime}$) **is defined by applying the prime operator twice in a row** (_e.g., finding shared attributes, then finding objects with those attributes_).
A set of objects $A$ is considered closed if applying the closure operator gives you the exact same set back ( A'' = A ).
These closed sets are critical because they represent the final groupings (extents) that make up formal concepts.

---

## 📖 2.4 Galois Connections

* **Poset** (**Partially Ordered Set**): A collection of items organized by a specific ranking rule, such as "is a subset of";
* **Lattice**: A special type of poset where any two items have a unique overlapping point (a "meet") and a unique combined point (a "join"). A Complete Lattice guarantees these points exist for groups of any size;
* **Galois Connection**: A mathematical mirror relationship that links two different posets together using two reversing functions;
  - G1) A1 ⊆ A2 ⇒ A′2 ⊆ A′1 (_antitone_)
  - G2) B1 ⊆ B2 ⇒ B′2 ⊆ B′1 (_antitone_)
  - G3) A ⊆ A′′, B ⊆ B′′ (_extensive_)
  - G4) A′′′ = A′, B′′′ = B′ (_idempotent_)
  - G5) (Si Ai )′ = Ti A′i , (Si Bi )′ = Ti B′i
* **The FCA Connection**: The derivation operators (_'_) create an exact Galois connection between the subsets of objects and the subsets of attributes. This connection acts as a bridge, proving that every closed group of objects pairs perfectly with a closed group of attributes.

When a closed group of objects and a closed group of attributes perfectly point to one another (A'= B and B'= A), they form a complete formal concept.

<img width="586" height="320" alt="image" src="https://github.com/user-attachments/assets/d634f991-a88a-49df-8120-f0c32e3f6a43" />

> Image: Visualising the Galois Connection
