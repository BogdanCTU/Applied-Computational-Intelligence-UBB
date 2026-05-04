# Course 4 Exercise 3

## Introduction

ToscanaJ is an open-source Java tool for building and navigating Conceptual Information Systems (CIS). A CIS consists of a many-valued context together with a set of pre-dened scales and a nested-line-diagram view. Users can interactively zoom into subscales and query the object set associated with any concept node.

## Context

Consider a library database modelled as a many-valued context with M = {Year, Subject, Length (pages)} and the following value ranges:
- Year: 1980 to 2024 (numeric);
- Subject: {Mathematics, Computer Science, Physics, Biology};
- Length: short (< 150 pp.), medium (150400 pp.), long (> 400 pp.)

### a) 
Define an appropriate scale for each attribute.
For Year, propose an interordinal scale distinguishing the decades (1980s, 1990s, 2000s, 2010s, and 2020s) and draw its
cross-table.

# Solution

We define one conceptual scale for each attribute:
 1. **Scale for Subject**: Since **Subject** is an _unordered categorical attribute_, the appropriate scale is a **nominal scale**. Each subject becomes one binary attribute.

| Subject value | Mathematics | Computer Science | Physics | Biology |
|---|:---:|:---:|:---:|:---:|
| Mathematics | X |  |  |  |
| Computer Science |  | X |  |  |
| Physics |  |  | X |  |
| Biology |  |  |  | X |

 2. **Scale for Length**: Values have a natural order ("_short < medium < long_"), therefore, an **ordinal scale** is appropriate. As an example, a book book with length **medium** receives the binary attributes "at least medium" and "at least long".

| Length value | at least short | at least medium | at least long |
|---|:---:|:---:|:---:|
| short | X | X | X |
| medium |  | X | X |
| long |  |  | X |

 3. **Scale for Year**: The **Year** attribute is numeric and ordered. The exercise asks for an **interordinal scale** (_a scale that scale uses both lower-bound and upper-bound attributes_).

| Year decade | ≤ 1980s | ≤ 1990s | ≤ 2000s | ≤ 2010s | ≤ 2020s | ≥ 1980s | ≥ 1990s | ≥ 2000s | ≥ 2010s | ≥ 2020s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1980s | X | X | X | X | X | X |  |  |  |  |
| 1990s |  | X | X | X | X | X | X |  |  |  |
| 2000s |  |  | X | X | X | X | X | X |  |  |
| 2010s |  |  |  | X | X | X | X | X | X |  |
| 2020s |  |  |  |  | X | X | X | X | X | X |

---

## Final Derived Context Attribute Set

The derived binary context replaces the original many-valued attributes with scaled binary attributes:

### Subject-derived attributes

- Subject: Mathematics
- Subject: Computer Science
- Subject: Physics
- Subject: Biology

### Length-derived attributes

- Length: at least short
- Length: at least medium
- Length: at least long

### Year-derived attributes

- Year ≤ 1980s
- Year ≤ 1990s
- Year ≤ 2000s
- Year ≤ 2010s
- Year ≤ 2020s
- Year ≥ 1980s
- Year ≥ 1990s
- Year ≥ 2000s
- Year ≥ 2010s
- Year ≥ 2020s

This derived binary context can now be processed using ordinary Formal Concept Analysis.
