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

---

## 📖 2.5 Formal Concepts

🔴 A **Formal Concept of a context** $\mathbb{K} **is defined as a pair (_A, B_) where A is a subset of objects (A ⊆ G) and B is a subset of attributes (B ⊆ M)**. The relationship is only valid if both A′ = B and B′ = A hold true simultaneously.

Terminology:
* **Extent** ($A$): _The set of objects covered by the concept_;
* **Intent** ($B$): _The set of attributes shared by the concept_.

| # | Extent A | Intent B |
| :--- | :--- | :--- |
| c1 | {Bat} | {wng, fly, fur, wrm} |
| c2 | {Eagle, Bat} | {wng, fly, wrm} |
| c3 | {Bat, Dog} | {fur, wrm} |
| c4 | {Eagle, Bat, Penguin} | {wng, wrm} |
| c5 | {Eagle, Bat, Penguin, Dog} | {wrm} |
| c6 | {Eagle, Bat, Penguin, Dog, Salmon} | ∅ |
| c0 | ∅ | {wng, fly, fur, wrm} *(only if no obj has all)* |

> ### Table: Sample Concept Systematic Approach

**Systematic Discovery**: To find all formal concepts, iterate through every possible subset of attributes ($B$) and compute its closure (B′′). If B = B′′, then the pair (B′, B) forms a valid concept. The same process works inversely for object subsets.

---

## 📖 2.6 Concept Lattices

Basic Theorem of FCA (Wille, 1982): When all formal concepts of a context are ordered by the subconcept relation ($\leq$), they form a mathematical structure called a Complete Lattice, denoted as $\mathfrak{B}(\mathbb{K})$.

Meet (Infimum / $\bigwedge$): Represents the greatest common subconcept. It is calculated by intersecting the extents and taking the closure of the united intents: $(\bigcap_{t}A_{t},(\bigcup_{t}B_{t})^{\prime\prime})$.

Join (Supremum / $\bigvee$): Represents the least common superconcept. It is calculated by taking the closure of united extents and intersecting the intents: $((\bigcup_{t}A_{t})^{\prime\prime},\bigcap_{t}B_{t})$.

Hasse Diagram Rules (Visualizing the Lattice):

Each node is a formal concept.

Upward edges indicate a direct superconcept relationship.

Objects are labeled at their "introducing concept" (the lowest possible node containing them).

Attributes are labeled at their highest possible node.

Reading the Lattice:

Moving down the diagram increases specificity (fewer objects, more attributes).

Moving up increases generality (more objects, fewer attributes).

A concept's extent contains all objects found at or below its node.

A concept's intent contains all attributes found at or above its node.

Lattice Complexity: The number of concepts can grow exponentially relative to the data size, bounded by an upper limit of $\min(2^{n},2^{k})$. Because of this, algorithms computing lattices must be highly efficient.

---

## 📖 2.7 Subconcept - Superconcept Relationship in Depth

Subconcept Definition ($\leq$): A concept $(A_1, B_1)$ is a subconcept of $(A_2, B_2)$ if its extent is smaller ($A_1 \subseteq A_2$). Because of the Galois connection, a smaller extent automatically mathematically guarantees a larger intent ($B_2 \subseteq B_1$).

Port-Royal Law: FCA formalizes the philosophical rule that the extension (general objects) and comprehension (specific attributes) of an idea exist in an inverse ratio.

Partial Order: The subconcept relation creates a partial order, meaning it is reflexive, antisymmetric, and transitive.

Incomparable Concepts: Concepts that are not subconcepts or superconcepts of one another represent horizontal diversity (e.g., distinct features like "winged" vs. "furred" that share a common domain but don't strictly overlap).

Cover Relation (Direct Steps): An edge in the lattice diagram represents a "cover" ($<$), meaning one concept is directly below another with no steps strictly between them.

Direct Superconcepts are found by adding a minimal new object to an extent: $((A\cup\{g\})^{\prime\prime}, (A\cup\{g\})^{\prime})$.

Direct Subconcepts are found by adding a minimal new attribute to an intent: $((B\cup\{m\})^{\prime}, (B\cup\{m\})^{\prime\prime})$.

Lattice Dimensions:

Chains (Height): Totally ordered vertical paths representing deep hierarchies (e.g., biological taxonomies).

Antichains (Width): Sets of mutually incomparable concepts representing horizontal feature diversity.

Attribute Inheritance: An object in a subconcept naturally inherits all attributes from every superconcept above it in the chain. This guarantees that all attributes are available to subconcepts without requiring redundant data storage.

Topological Properties: Any interval between two concepts ($[c, d]$) forms its own self-contained complete lattice.
