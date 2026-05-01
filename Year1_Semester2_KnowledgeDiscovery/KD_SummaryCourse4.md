<!-- --------------------------------------------------------------- -->
<!-- ---------------------- COURSE 4 ToscanaJ ---------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 4 - Many-Valued Contexts, Conceptual Scaling, and ToscanaJ — Optimized Revision Summary

---

## 📖 4.1 Formal Concept Analysis (FCA) Fundamentals

### 📑 4.1.1 Formal Context

A **formal context** is a basic table of binary data.

It consists of three parts: **objects** (the items being studied), **attributes** (the traits of the items) and an **incidence relation** (a connection showing that an object has a specific trait). Is reppresented by a triple: **K = (G, M, I)**
- **G** = set of objects
- **M** = set of attributes
- **I ⊆ G × M** = binary incidence relation

For reppresentation, `(g, m) ∈ I` means **object g has attribute m**

### 📑 4.1.2 Derivation Operators

For:
- `A ⊆ G`
- `B ⊆ M`
- 
Definitions:
- A′ = {m ∈ M | ∀g ∈ A : gIm} , meaning `A′` = attributes common to all objects in A
- B′ = {g ∈ G | ∀m ∈ B : gIm} , meaning `B′` = objects having all attributes in B

### 📑 4.1.3 Formal Concept

A **formal concept** is a pairing of a set of objects and a set of attributes. Every object in the grouping shares all the attributes in the grouping and no other objects share all those exact attributes. The pair is reppresented as `(A, B) with A′ = B and B′ = A`.
- **A** = extent (objects)
- **B** = intent (attributes)

### 📑 4.1.4 Concept Lattice

All formal concepts ordered by (A₁, B₁) ≤ (A₂, B₂) so A₁ ⊆ A₂ forms a **complete lattice**. It is basically a structured visual hierarchy showing all formal concepts.  Higher points in the diagram represent larger groups of objects, while lower points represent a larger set of shared attributes.  

### 📑 4.1.5 Limitation of Classical FCA

Standard Formal Concept Analysis only handles yes/no binary attributes. Real-world databases use varied values like ages, prices or colors.

Real-world data uses attributes with values, data that is **not binary**.

| Attribute | Example |
|---|---|
| Age | 23, 45 |
| Size | small, large |
| Temperature | cold, warm |
| Rating | 1–5 |
| Price | 5.99 |
| Color | red, blue |

---

## 📖 4.2 Many-Valued Contexts

### 📑 4.2.1 Many-Valued Context

**Many-Valued Context** is an expanded dataset structure. It **contains objects, attributes, attribute values and a ternary incidence relation** (a connection linking an object, an attribute, and a specific value, such as "eagle", "size" and "large").

A **many-valued context** is a quadruple: `K = (G, M, W, I)` where:
- **G** = objects
- **M** = many-valued attributes
- **W** = set of values
- **I ⊆ G × M × W** = ternary incidence relation

### 📑 4.2.2 Functionality Condition

**Functionality Condition** is a rule stating an object can only possess one specific value for any single attribute Each object has at most one value per attribute **(g, m, v) ∈ I ∧ (g, m, w) ∈ I ⇒ v = w**, using the notation `m(g) = v`.

### 📑 4.2.3 Attribute Types

1. **Nominal**: unordered values (color, habitat, language);
2. **Ordinal**: ordered values (size, age, blood pressure);
3. **Special Case**: `W = {0,1}`, then it reduces to ordinary FCA.

> ### _Note_: It is acceptable for an object to lack data for a specific attribute, resulting in a partial context, defining **Missing Values**.

---

## 📖 4.3 Conceptual Scaling

**Conceptual Scaling** is a method of translating a complex many-valued context into a simple binary formal context. This produces a **Derived Context** which can be processed using ordinary **FCA** (with binary values).

<img width="311" height="286" alt="image" src="https://github.com/user-attachments/assets/4f29ed21-7e5d-4c96-8262-fec2793792e9" />

> ### Image: Conceptual scaling representation

### 📑 4.3.1 Conceptual Scale

With **Conceptual Scale** reffers to a custom rulebook for converting a single attribute. It treats the original values as objects and creates new binary attributes based on their structure. A normal formal context, for attribute `m` with value set `Wm`, define Sₘ = (Wₘ, Sₘ, Jₘ) where:
- `Wm` acts as objects
- `Sm` = scale attributes
- `Jm` = binary relation

### 📑 4.3.2 Derived Context

**Derived Context** is the final combined binary dataset. It retains the original objects but replaces the many-valued attributes with the newly scaled binary attributes.

Example: if `size(eagle) = large` and scale contains “at least medium” then eagle gets attribute **size: at-least-medium**.

## 📖 4.4 Advanced Scaling Techniques

### 📑 4.4.1 Scale Types

#### 📓 4.4.1.1 Nominal Scale

Treats values as separate, unordered categories (e.g., colors or species). Each value gets exactly one attribute: `S_nom = (W, W, =)`

<img width="266" height="295" alt="image" src="https://github.com/user-attachments/assets/547e4035-22c8-4c0c-9729-f68240f5cc36" />

> ### Image: Nominal scale representation sample

#### 📓 4.4.1.2 Ordinal Scale

Ranks values in a strict sequence, capturing "at least" relationships (e.g., sizes from small to large). For ordered values `w₁ < w₂ < ... < wₙ` the ordinal scale is defined as `S_ord = (W, W, ≤)`. An object with value `wi` gets all attributes “≥ wi”.

### Ordinal scale for Size:

| | tiny | small | med. | large | huge |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **tiny** | X | X | X | X | X |
| **small** | | X | X | X | X |
| **med.** | | | X | X | X |
| **large** | | | | X | X |
| **huge** | | | | | X |

Example: For "small" reads as row “small” has attributes {small, medium, large, huge} = “at least small”.

#### 📓 4.4.1.3 Interordinal Scale (Ranges)

Combines "at least ≤" and "at most ≥" structures to represent intervals (e.g., age ranges).

#### 📓 4.4.1.4 Dichotomic Scale

Dichotomic Scale: Asks a single true/false question to split values (e.g., "Is age > 60?").

#### 📓 4.4.1.5 Biordinal Scale

Combines two independent ordinal scales on the same value set (e.g., dual ordering): `S_biord = (W , S1 ∪ S2, J1 ∪ J2)`

#### 📓 4.4.1.6 Summary

| Scale Type | Value Structure | Attributes | Example |
| :--- | :--- | :--- | :--- |
| Nominal | Unordered set | One per value | Color, species |
| Ordinal | Linear order | ≥ wi for each wi | Size, rating |
| Interordinal | Linear order | ≤ wi & ≥ wi | Age, temperature |
| Interval | Numeric range | Interval membership | Price range |
| Dichotomic | Any set | One condition | Age > 60 |
| Biordinal | Two-dim. order | Two ordinal parts | Exam scores |
| Contranominal | Set complement | One per value (neg.) | “not red” |

### 📑 4.4.2 Constructing the Derived Context

- **Step 1**: Choose a scale for each attribute;
- **Step 2**: Create new attribute set: `Ṁ = {(m, s) | m ∈ M, s ∈ Sₘ}`;
- **Step 3**: Assign incidence: `g İ (m, s) iff (m(g), s) ∈ Jₘ`;
- **Step 4**: Apply ordinary FCA.

### 📑 4.4.3 Nested Diagram

When an attribute has many values, the lattice of the derived context may be visualized as a **nested diagram**. It is a visualization technique for complex data, places a miniature lattice (representing an inner attribute) inside the nodes of a larger main lattice (representing an outer attribute). This makes reading the interactions between two separate attributes much easier for humans.

<img width="236" height="160" alt="image" src="https://github.com/user-attachments/assets/cd840db1-0450-4f0c-9b7f-fe2176c9a90a" />

> ### Image: Sample schematic nested line diagram

# 📖 4.5 ToscanaJ

**ToscanaJ** is an open-source software tool designed to execute the entire Formal Concept Analysis pipeline.


### 📑 4.5.1 Workflow

The software connects to a standard relational database, allows the user to graphically define conceptual scales, computes the derived context, and generates interactive nested line diagrams.

Users interact with the diagrams directly by **Visual Queries**. Clicking a node on the lattice automatically queries the database and displays the specific objects belonging to that concept.
