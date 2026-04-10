<!-- --------------------------------------------------------------- -->
<!-- -------------------- COURSE 1 INTRODUCTION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 1 - Philosophy and Foundations of Knowledge Discovery**

---

## 📖 1 - Introduction

🔴 **Knowledge Discovery** (_KD_) **is the process of figuring out what remains true beyond just looking at single**, **isolated pieces of data**.
Storing data is not the same as understanding data. True knowledge requires structure, generalization, invariance (things that do not change) and logical relations.
Human thinking operates using concepts, categories and hierarchies, rather than raw data points. Therefore, if computers are going to help us reason, they must also operate conceptually.

🔴 **There are two main ways to learn from data**:
* **Statistical learning**: This approach estimates the likelihood of events and tolerates errors;
* **Conceptual reasoning**: This approach identifies strict invariants, produces logical rules and builds taxonomies (classification systems).

---

## 📖 2 - Introduction to Formal Concept Analysis (FCA)

🔴 **Formal Concept Analysis** (_FCA_) **is a mathematical model used to discover concepts and map out the exact dependencies within data**.
**In the standard Knowledge Discovery pipeline, FCA is primarily used for pattern extraction and knowledge representation. It transforms raw data patterns into a clear structure**.
It is highly valuable because it is explainable, exact, structured and minimal.
FCA bridges the gap between logic and data by focusing on two types of knowledge:
* **Conceptual Knowledge**: This groups objects and their features together into a hierarchical structure called a lattice. _Example: Grouping "Mammals" or "Flying animals" based on shared traits_;
* **Implicational Knowledge**: This focuses on logical rules and dependencies between features. _Example: A rule stating that all animals with fur are mammals_.

| Animal | Mammal | CanFly | Aquatic | HasFur |
|--------|--------|--------|---------|--------|
| Bat    | X      | X      |         | X      |
| Whale  | X      |        | X       |        |
| Dog    | X      |        |         | X      |
| Eagle  |        | X      |         |        |

> ### Table: Sample of knowledge representation

---

## 📖 3 - The Mathematical Core of Formal Concept Analysis (FCA)

**FCA is built on rigorous math**, including set theory and lattice theory, giving it algorithmic clarity and logical completeness.
🔴 A **Concept Lattice** **is a complete taxonomy** (**classification tree**) **created automatically from data**:
* Every point (node) in this lattice contains an Extent and an Intent;
* The **Extent represents the objects** (_e.g., specific patients or cities_);
* The **Intent represents the attributes those objects share** (_e.g., specific symptoms or climate features_).

<img width="452" height="394" alt="image" src="https://github.com/user-attachments/assets/50fe0a82-42d1-4249-8e49-09a6e3f29f2e" />

> ### Image: Concept Lattice with Intent (attrs) and Extent (objects)

<img width="806" height="379" alt="image" src="https://github.com/user-attachments/assets/19e1af36-e19d-4a59-80cc-aad2c46c0709" />

> ### Image: Concept Lattice for Programming Languages and Features

**Because raw data can generate thousands of redundant rules**, **FCA uses Canonical Bases**.
A canonical base is the smallest complete set of rules that contains no redundancy but keeps its full logical power. This acts as knowledge compression.
FCA can go beyond simple "yes/no" binary data. It can generalize rules for structured descriptions like number intervals (_e.g., temperature ranges_), sets or complex graphs, recognized as **Pattern Structures**.

<img width="817" height="394" alt="image" src="https://github.com/user-attachments/assets/6ce02c74-0fbc-4c7b-b1ae-0f45110b274c" />

> ### Image: Pattern Structure Lattice for Cities and Climate

---

## 📖 4 - Triadic Formal Concept Analysis (FCA): Adding Context

**Triadic Formal Concept Analysis** (_FCA_) **expands traditional FCA by adding a third dimension known as** "**conditions**".
Instead of just looking at Objects and Attributes, **Triadic FCA looks at Objects**, **Attributes and Conditions** (_like time, location or user session_).
This allows the system to discover **Contextualized Implications**. These are rules that are only true under specific situations.
Example: The rule "Buying sunscreen implies buying sunglasses" might hold true under the condition of "Summer", but fail under the condition of "Winter".

🔴 **Triadic FCA explores three families of implications**:
* **Attribute implications**: Finding which features entail other features given a specific context;
* **Condition implications**: Finding which contexts entail other contexts given a specific topic;
* **Object implications**: Finding which objects dominate other objects in a specific context.

### 📑 4.1 - Triadic Formal Concept Analysis (FCA) on Cities, Climate and Seasons Sample 

**Components**
* **G (objects)**: 5 cities
* **M (attributes)**: { _Hot_, _Rainy_, _Dry_, _Cold_ }
* **B (conditions)**: { _Winter_, _Summer_ }

**Triadic concept (A, B, C):**
* A × B × C ⊆ I, maximal:
* B = { m | ∀g ∈ A, b ∈ C : (g, m, b) ∈ I }
* A = { g | ∀m ∈ B, b ∈ C : (g, m, b) ∈ I }
* C = { b | ∀g ∈ A, m ∈ B : (g, m, b) ∈ I }

**Selected triconcepts:**

| Extent | Intent | Modus |
| :--- | :--- | :--- |
| Cai,Lon,Osl,Syd | Cold | Win |
| Bgk,Cai,Syd | Hot | Sum |
| Bgk,Lon,Osl | Rainy | Sum |
| Bgk,Cai,Osl | Dry | Win |
| Lon,Syd | Cold,Rainy | Win |
| Cai,Syd | Dry,Hot | Sum |
| Bangkok | Hot | W+S |

**Triadic cross-table (g, m, b) ∈ I shown as x**

| City | Winter Ho | Winter Ra | Winter Dr | Winter Co | Summer Ho | Summer Ra | Summer Dr | Summer Co |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| London | . | x | . | x | . | x | . | . |
| Cairo | . | . | x | x | x | . | x | . |
| Bangkok | x | . | x | . | x | x | . | . |
| Oslo | . | . | x | x | . | x | . | x |
| Sydney | . | x | . | x | x | . | x | . |

*Ho=Hot, Ra=Rainy, Dr=Dry, Co=Cold*

**Reading triconcept (A, B, C):** Every city in A has every feature in B during every season in C — and the triple is maximal.

### 📑 4.2 - Triadic Formal Concept Analysis (FCA) Concept Lattices per Season Sample 

**Cross season triconcepts**, modus = { Winter, Summer }:
* T10: { London } | { Rainy }
* T11: { Cairo } | { Dry }
* T12: { Bangkok } | { Hot }
* T13: { Oslo } | { Cold }

<img width="817" height="299" alt="image" src="https://github.com/user-attachments/assets/3122fccf-b819-4f12-9ef1-6ddf8cbd226d" />

> ### Image: Concept Lattices per Season
