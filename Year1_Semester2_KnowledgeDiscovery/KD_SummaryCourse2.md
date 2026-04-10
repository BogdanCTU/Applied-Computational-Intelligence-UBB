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

🔴 **Basic Theorem of FCA** (Wille, 1982): **When all formal concepts of a context are ordered by the subconcept relation** ($\leq$), **they form a mathematical structure called a Complete Lattice**, denoted as $\mathfrak{B}(\mathbb{K})$.

* **Meet** (Infimum / $\bigwedge$): Represents the greatest common subconcept. It is calculated by intersecting the extents and taking the closure of the united intents: $(\bigcap_{t}A_{t},(\bigcup_{t}B_{t})^{\prime\prime})$.

* **Join** (Supremum / $\bigvee$): Represents the least common superconcept. It is calculated by taking the closure of united extents and intersecting the intents: $((\bigcup_{t}A_{t})^{\prime\prime},\bigcap_{t}B_{t})$.

**Hasse Diagram Rules** (**Visualizing the Lattice**):
* Each node is a formal concept;
* Upward edges indicate a direct superconcept relationship;
* Objects are labeled at their "introducing concept" (the lowest possible node containing them);
* Attributes are labeled at their highest possible node.

<img width="662" height="389" alt="image" src="https://github.com/user-attachments/assets/3f33c263-955f-4be9-a809-bf2057ad9e5c" />

> ### Image: Hasse Diagram

**Reading the Lattice**:
* Moving down the diagram increases specificity (fewer objects, more attributes);
* Moving up increases generality (more objects, fewer attributes);
* A concept's extent contains all objects found at or below its node;
* A concept's intent contains all attributes found at or above its node.

**Lattice Complexity**: The number of concepts can grow exponentially relative to the data size, bounded by an upper limit of $\min(2^{n},2^{k})$. Because of this, algorithms computing lattices must be highly efficient.

---

## 📖 2.7 Subconcept - Superconcept Relationship in Depth

🔴 **Subconcept Definition** ($\leq$): A concept $(A_1, B_1)$ is a subconcept of $(A_2, B_2)$ if its extent is smaller ($A_1 \subseteq A_2$). Because of the Galois connection, a smaller extent automatically mathematically guarantees a larger intent ($B_2 \subseteq B_1$).

**Port-Royal Law**: FCA formalizes the philosophical rule that the extension (general objects) and comprehension (specific attributes) of an idea exist in an inverse ratio.

**Partial Order**: The subconcept relation creates a partial order, meaning it is reflexive, antisymmetric, and transitive.

**Incomparable Concepts**: Concepts that are not subconcepts or superconcepts of one another represent horizontal diversity (e.g., distinct features like "winged" vs. "furred" that share a common domain but don't strictly overlap).

**Cover Relation** (**Direct Steps**): An edge in the lattice diagram represents a "cover" ($<$), meaning one concept is directly below another with no steps strictly between them.
* Direct Superconcepts are found by adding a minimal new object to an extent: $((A\cup\{g\})^{\prime\prime}, (A\cup\{g\})^{\prime})$;
* Direct Subconcepts are found by adding a minimal new attribute to an intent: $((B\cup\{m\})^{\prime}, (B\cup\{m\})^{\prime\prime})$.

**Lattice Dimensions**:
* **Chains** (**Height**): Totally ordered vertical paths representing deep hierarchies (e.g., biological taxonomies);
* **Antichains** (**Width**): Sets of mutually incomparable concepts representing horizontal feature diversity.

Attribute Inheritance: An object in a subconcept naturally inherits all attributes from every superconcept above it in the chain. This guarantees that all attributes are available to subconcepts without requiring redundant data storage.

Topological Properties: Any interval between two concepts ($[c, d]$) forms its own self-contained complete lattice.

---

## 📖 2.8 Building the Concept Lattice: Construction and Labelling

🔴 **5-Step Construction Algorithm**:

1. **Enumerate**: Find all formal concepts by applying the closure operator ($B^{\prime\prime}$) to subset;
2. **Order**: Establish the partial order by checking which extents are subsets of others;
3. **Cover** Relations: Remove transitive edges to find direct cover relations;
4. **Label**: Assign reduced labels to the concepts;
5. **Draw**: Create the Hasse diagram.

Reduced Labelling: A technique to prevent diagrams from becoming unreadable by eliminating repetitive information. Instead of listing every object and attribute at every node, items are labeled exactly once.

Object Concept $\gamma(g)$: The smallest (lowest) concept containing an object $g$ in its extent. Formula: $(\{g\}^{\prime\prime}, \{g\}^{\prime})$. Object labels go here.

Attribute Concept $\mu(m)$: The largest (highest) concept containing an attribute $m$ in its intent. Formula: $(\{m\}^{\prime}, \{m\}^{\prime\prime})$. Attribute labels go here.

Mathematical Equivalence: The reduced diagram is a mathematically lossless representation of the original data table. An object has an attribute ($g|m$) if and only if $\gamma(g) \le \mu(m)$.

Reading Rules:

Extent: To find all objects belonging to a concept, collect all object labels found by moving downward from that node.

Intent: To find all attributes belonging to a concept, collect all attribute labels found by moving upward from that node.

---

## 📖 2.9 Elegant Concept Lattice Drawing

Non-Negotiable Rules: The top concept must be at the highest point, and the bottom concept at the lowest point. Edges must point strictly upward. Only draw direct cover edges (never draw transitive shortcuts). Write object labels below their nodes and attribute labels above.

Rank Assignment: A concept's rank is calculated by the length of the longest chain of steps connecting it to the bottom node. Concepts sharing the same rank should be placed on the exact same horizontal level.

Additive Line Diagrams: A specific drawing style where the physical slope of an edge indicates which attribute is being introduced. The final position of any concept node is the vector sum of its attributes' directional slopes. * Advanced Layouts: For complex data, diagrams can use visual aids like scaling node sizes based on object count, color-coding patterns, edge bundling to reduce clutter, or force-directed physics to balance spacing.

---

## 📖 2.10 Conceptual Landscapes

Definition: A holistic environment combining concept lattices with a navigational infrastructure, logical implications, visual maps, and linked contexts.

The Paradigm: Proposed by Rudolf Wille as a cognitive tool for human thinking. It operates like a terrain: "peaks" represent broad, generalized overviews, while "valleys" represent highly detailed, specific clusters.

Multi-Context Spaces: Complex domains require multiple linked contexts (e.g., mapping patients to symptoms, and symptoms to diagnoses) to form a complete Concept Information System.

Navigation Actions: Users can specialize (zoom in to subconcepts), generalize (zoom out to superconcepts), move laterally to incomparable concepts, or query specific attribute/object nodes directly.

Conceptual Scales: Real-world data often uses specific values (like "hot" or "cold") instead of simple binary "yes/no" markers. Conceptual scaling translates these multi-valued attributes into binary formal contexts using predefined logical frameworks like Nominal (unordered) or Ordinal (ranked) scales.

TOSCANA: An early software system built for exploring these landscapes. It visually combined different conceptual scales using nested line diagrams, drawing an inner scale lattice completely inside the node of an outer lattice.
