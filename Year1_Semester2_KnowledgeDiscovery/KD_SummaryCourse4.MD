<!-- --------------------------------------------------------------- -->
<!-- ---------------------- COURSE 4 ToscanaJ ---------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 4 - Many-Valued Contexts, Conceptual Scaling, and ToscanaJ — Optimized Revision Summary

---

# 📖 4.1 Formal Concept Analysis (FCA) Fundamentals

## Formal Context

### Definition

A **formal context** is a triple:

K = (G, M, I)

where:

- **G** = set of objects
- **M** = set of attributes
- **I ⊆ G × M** = binary incidence relation

Meaning:

- `(g, m) ∈ I` means **object g has attribute m**

---

## Derivation Operators

For:

- `A ⊆ G`
- `B ⊆ M`

definitions:

A′ = {m ∈ M | ∀g ∈ A : gIm}

B′ = {g ∈ G | ∀m ∈ B : gIm}

Interpretation:

- `A′` = attributes common to all objects in A
- `B′` = objects having all attributes in B

---

## Formal Concept

### Definition

A **formal concept** is a pair:

(A, B) with A′ = B and B′ = A

where:

- **A** = extent (objects)
- **B** = intent (attributes)

---

## Concept Lattice

All formal concepts ordered by:

(A₁, B₁) ≤ (A₂, B₂) iff A₁ ⊆ A₂

This forms a **complete lattice**.

---

## Limitation of Classical FCA

Only supports:

- binary attributes (**present / absent**)

Cannot directly represent:

- age
- size
- temperature
- rating
- price
- color

This motivates **Many-Valued FCA**.

---

# 📖 4.2 Many-Valued Contexts

---

## Motivation

Real-world data uses attributes with values:

| Attribute | Example |
|---|---|
| Age | 23, 45 |
| Size | small, large |
| Temperature | cold, warm |
| Rating | 1–5 |
| Price | 5.99 |
| Color | red, blue |

These are **not binary**.

---

## Many-Valued Context

## Definition

A **many-valued context** is a quadruple:

K = (G, M, W, I)

where:

- **G** = objects
- **M** = many-valued attributes
- **W** = set of values
- **I ⊆ G × M × W** = ternary incidence relation

---

## Functionality Condition

Each object has at most one value per attribute:

(g, m, v) ∈ I ∧ (g, m, w) ∈ I ⇒ v = w

Notation:

- `m(g) = v`

Important:

- relation may be **partial**
- some values may be missing

---

## Attribute Types

### Nominal

- unordered values

Example:

- color
- habitat
- language

### Ordinal

- ordered values

Example:

- size
- age
- blood pressure

### Special Case

If:

W = {0,1}

then it reduces to ordinary FCA.

---

## Key Problem

Because incidence is ternary:

- standard FCA cannot be applied directly

### Solution:

# **Conceptual Scaling**

---

# 📖 4.3 Conceptual Scaling

---

## Core Idea

Transform each many-valued attribute into a standard one-valued formal context.

This produces a:

# **Derived Context**

which can be processed using ordinary FCA.

---

## Conceptual Scale

## Definition

For attribute `m` with value set `Wm`, define:

Sₘ = (Wₘ, Sₘ, Jₘ)

where:

- `Wm` acts as objects
- `Sm` = scale attributes
- `Jm` = binary relation

This is a normal formal context.

---

## Derived Context

### Definition

K̇ = (G, ⨆ Sₘ, İ)

Condition:

(g, (m, s)) ∈ İ iff (m(g), s) ∈ Jₘ

Interpretation:

- object gets new binary attributes derived from scale definitions

---

## Example

If:

- `size(eagle) = large`

and scale contains:

- “at least medium”

then:

- eagle gets attribute **size: at-least-medium**

---

# 4. Scale Types

---

# Most Important Scale Types

---

## 1. Nominal Scale

## Definition

Each value gets exactly one attribute:

S_nom = (W, W, =)

Use when:

- values are categories only

Examples:

- habitat
- country
- topic
- species

Effect:

- one value → one attribute

---

## 2. Ordinal Scale

## Definition

For ordered values:

w₁ < w₂ < ... < wₙ

scale:

S_ord = (W, W, ≤)

Effect:

object with value `wi` gets:

- all attributes “≥ wi”

Example:

small → {small, medium, large, huge}

Use for:

- size
- age groups
- ratings

---

## 3. Interordinal Scale

Combines:

- ≤
- ≥

Supports:

- intervals
- upper + lower bounds

Use for:

- age ranges
- temperature
- price intervals

---

## 4. Dichotomic Scale

Single binary condition.

Example:

- `age > 60 → elderly`

Use for:

- focused queries

Simplest transformation.

---

## 5. Biordinal Scale

Two independent ordinal scales.

Useful when:

- both upper/lower perspectives matter

---

# Important Principle

## Scale choice = domain knowledge

There is no single correct scale.

The scale determines:

- concepts
- implications
- analysis quality

---

# 📖 4.5 Constructing the Derived Context

---

## Algorithm

### Step 1

Choose a scale for each attribute.

### Step 2

Create new attribute set:

Ṁ = {(m, s) | m ∈ M, s ∈ Sₘ}

### Step 3

Assign incidence:

g İ (m, s) iff (m(g), s) ∈ Jₘ

### Step 4

Apply ordinary FCA.

---

# 📖 4.6 Scale Compatibility and Refinement

---

## Finer vs Coarser Scales

### Coarser Scale

- fewer concepts
- simpler lattice
- better overview

### Finer Scale

- more concepts
- more detail
- harder to read

---

## Practical Rule

Start coarse → refine only important attributes.

Recommended:

- fewer than 10 scale attributes per original attribute

---

# 📖 4.7 Implications After Scaling

---

## Attribute Exploration

After scaling, FCA discovers implications:

Example:

- `{age ≥ 50, smoker} ⇒ {bp: high}`

---

## Two Types of Implications

---

## 1. Scale-Induced

Always true because of scale structure.

Example:

- `{age ≥ 65} ⇒ {age ≥ 50}`

These are **trivial scale axioms**

---

## 2. Data-Induced

Come from actual dataset.

Example:

- `{water habitat} ⇒ {carnivore}`

These contain real domain knowledge.

---

## Best Practice

Separate:

- trivial scale implications
- meaningful empirical implications

---

# 📖 4.8 Nested Line Diagrams

---

## Purpose

Visualize large lattices compactly.

### Structure

- outer lattice → one attribute
- inner lattice → second attribute

Best for:

- nominal + ordinal combinations

Example:

- habitat × size

---

## Advantages

- easier than full lattice
- shows attribute interaction
- human-readable

---

# 📖 4.9 ToscanaJ

---

# What is ToscanaJ?

An FCA tool implementing the full pipeline:

### Workflow

SQL Database  
→ Scale Definitions  
→ Derived Context  
→ Concept Lattice  
→ Visualization + Queries

---

## Main Components

### Elba

- database connection
- schema browser

### Siena

- scale editor

### ToscanaJ Main

- lattice visualization

### Cernato

- larger datasets

---

## Supported Databases

- HSQLDB
- MySQL
- PostgreSQL
- Access
- JDBC-compatible systems

---

# 📖 4.10 ToscanaJ Workflow

---

## Step 1 — Project Setup

- connect DB / import CSV
- select table
- inspect schema

---

## Step 2 — Define Scales

Choose:

- nominal
- ordinal
- interordinal
- etc.

Important:

### ToscanaJ does NOT choose scales automatically.

Wrong scale → wrong analysis.

---

## Step 3 — Navigate Diagrams

Node shows:

- extent
- intent
- object count

Rule:

### Higher nodes

→ more objects

### Lower nodes

→ more attributes

---

## Step 4 — Query by Diagram

Selecting node:

- automatically generates SQL query

Very useful for interactive analysis.

---

## Step 5 — Nested Diagrams

Best with:

- outer = nominal
- inner = ordinal

Example:

- habitat × size

---

## Step 6 — Export

Supported:

- PNG / SVG
- HTML report
- CSV
- print

Best for reproducibility:

- share `.toscana` file + database

---

# 📖 4.11 Theoretical Foundations

---

## Fundamental Theorem

The derived lattice embeds into product of scale lattices:

B(K̇) ↪ ∏ B(Sₘ)

Meaning:

- derived context lattice is a sublattice of scale lattice product

---

## Consequence

Large scales may cause:

# exponential growth

Therefore:

### over-scaling is dangerous

---

## Scale-Closed Sets

Not every subset of derived attributes can be an intent.

Example:

with ordinal size:

- `{large}` alone is impossible

because:

- “large” implies “medium”

This reduces search space.

---

# 📖 4.12 Extensions

---

## Rough Scale Approximation

Used when scale is uncertain.

### Lower Approximation

attribute definitely holds

### Upper Approximation

attribute possibly holds

Links FCA with:

# Rough Set Theory

---

## Pattern Structures

Generalization beyond scaling.

Can directly handle:

- intervals
- sets
- graphs
- sequences

without manual scales.

More powerful, but:

### ToscanaJ does not support them.

---

# 📖 4.13 Comparison with Other Methods

---

## FCA Strengths

Compared to:

- clustering
- decision trees
- SQL/OLAP

FCA uniquely provides:

### complete lattice structure

### formal implication discovery

### explicit domain knowledge via scales

### human-readable conceptual analysis

---

# 📖 4.14 Common Pitfalls

---

## Major Mistakes

### 1. Using nominal for ordered data

→ loses ordering

### 2. Too many scale values

→ unreadable lattice

### 3. Ignoring missing values

→ false implications

### 4. Mixed inconsistent scales

→ unreliable results

---

## Sanity Check

Expected concept count:

|G| ≤ #concepts ≤ 2^|Ṁ|

If:

- too few → scale too coarse
- too many → scale too fine

---

# Final Key Conclusion

# Conceptual Scaling is the bridge

between:

## real-world many-valued data

and

## classical Formal Concept Analysis

Without scaling:

- FCA cannot be applied

With good scaling:

- concepts become meaningful
- implications become useful
- knowledge discovery becomes practical

ToscanaJ provides the operational implementation of this full process.
