# Exercise 1

A many-valued context is a tuple `K = (G, M, W, I)` where `G` is a set of objects, `M` a set of
attributes, `W` a set of attribute values, and `I ⊆ G × M × W` a ternary incidence relation
satisfying the functionality condition: if `(g, m, w1) ∈ I` and `(g, m, w2) ∈ I`, then `w1 = w2`.

The table below is a many-valued context describing four European cities:

| City (G)  | Population | Coastal? | Climate        |
|-----------|-----------|----------|----------------|
| Vienna    | large     | no       | continental    |
| Barcelona | large     | yes      | mediterranean  |
| Lisbon    | medium    | yes      | mediterranean  |
| Bern      | small     | no       | alpine         |

1. Identify the sets `G`, `M`, and `W` explicitly.
2. Write `I` as a set of triples `(g, m, w)`.
3. Verify that the functionality condition holds for all attributes. Which well-known property of ordinary functions does this condition correspond to?
4. Explain, in one sentence, why a standard (one-valued) formal context (`G`, `M`, `I`) cannot directly represent the information in this table.

#### 1. Identify the sets G, M, and W explicitly
- **G (Objects):** The items being described: G = {Vienna, Barcelona, Lisbon, Bern}
- **M (Attributes):** The categories or features evaluated for each object: M = {Population, Coastal?, Climate}
- **W (Attribute values):** All unique values appearing in the table: W = {large, medium, small, yes, no, continental, mediterranean, alpine}

#### 2. Write \(I\) as a set of triples \((g, m, w)\)
The incidence relation \(I\) maps each table cell to a triple consisting of an object, an attribute, and its value:
- (Vienna, Population, large)  
- (Vienna, Coastal?, no)  
- (Vienna, Climate, continental)  
- (Barcelona, Population, large)  
- (Barcelona, Coastal?, yes)  
- (Barcelona, Climate, mediterranean)  
- (Lisbon, Population, medium)  
- (Lisbon, Coastal?, yes)  
- (Lisbon, Climate, mediterranean)  
- (Bern, Population, small)  
- (Bern, Coastal?, no)  
- (Bern, Climate, alpine)

#### 3. Verify the functionality condition and identify the corresponding property
- **Verification:**  
  The functionality condition requires that each object has exactly one value per attribute.  
  The table satisfies this: every object–attribute pair has a single, unique value (e.g., Vienna’s population is only “large”).
- **Property:**  
  This corresponds to the defining property of a **mathematical function**—being *single-valued* (well-defined), where each input maps to exactly one output.

#### 4. Why a standard formal context \((G, M, I)\) cannot represent this table
A standard formal context encodes only binary relations (presence/absence), so it cannot directly represent multi-valued attributes such as “large” or “alpine” within a single cell.

---

# Exercise 2

Conceptual scaling transforms a many-valued context into a one-valued context by replacing each many-valued attribute m ∈ M with a scale S_m = (Gm, Mm, Im) whose objects are the possible values of m. The derived one-valued context K′ = (G, S_m∈M M_m, I′) is defined by: (g, n) ∈ I′ ⇐⇒ ∃ w ∈ W : (g, m, w) ∈ I and (w, n) ∈ Im, for each scale attribute n ∈ M_m.

Use the cities context from following table:
| City (G)  | Population | Coastal? | Climate        |
|-----------|-----------|----------|----------------|
| Vienna    | large     | no       | continental    |
| Barcelona | large     | yes      | mediterranean  |
| Lisbon    | medium    | yes      | mediterranean  |
| Bern      | small     | no       | alpine         |

Solve:
1. Nominal scale for "Coastal?". Construct the nominal scale S_coastal = ({yes,no), {costal, inland}, I_costal), where value "yes" maps to attribute "coastal" and value "no" maps to attribute "inland". Write out "I_Coastal" as a cross-table.
2. Ordinal scale for Population. The values small ≤ medium ≤ large are ordered. An ordinal scale uses attributes {at-least-small, at-least-medium, at-least-large}, where value v has attribute "at least u" if u ≤ v. Construct and write out the ordinal scale S_pop.
3. Derive the complete scaled one-valued context K′ for all three attributes (use your scales from (a) and (b), and a nominal scale for Climate).
4. Compare the concept-lattice structure expected from K′ with what you would obtain if you used a nominal scale for Population instead of an ordinal one. What structural difference arises, and why?

## Exercise Solution: Conceptual Scaling for Cities Context

### 1) Nominal scale for `Coastal?`

The nominal scale is:
$$\[S_{coastal} = (\{yes, no\}, \{coastal, inland\}, I_{coastal})\]$$
- `yes` maps to `coastal`
- `no` maps to `inland`

Cross-table for \(I_{coastal}\):

| Coastal? value | coastal | inland |
|---|:---:|:---:|
| yes | X | |
| no | | X |

---

### 2) Ordinal scale for `Population`

The population values are ordered as:

\[
small \leq medium \leq large
\]

The ordinal scale attributes are:

- `at-least-small`
- `at-least-medium`
- `at-least-large`

A value \(v\) has attribute `at-least-u` if \(u \leq v\).

Cross-table for \(S_{pop}\):

| Population value | at-least-small | at-least-medium | at-least-large |
|---|:---:|:---:|:---:|
| small | X | | |
| medium | X | X | |
| large | X | X | X |

---

### 3) Complete derived one-valued context \(K'\)

We use:

- Nominal scale for `Coastal?`
- Ordinal scale for `Population`
- Nominal scale for `Climate`

Climate values:

- `continental`
- `mediterranean`
- `alpine`

Derived binary attributes:

- `population: at-least-small`
- `population: at-least-medium`
- `population: at-least-large`
- `coastal: coastal`
- `coastal: inland`
- `climate: continental`
- `climate: mediterranean`
- `climate: alpine`

Derived context \(K'\):

| City | pop: at-least-small | pop: at-least-medium | pop: at-least-large | coastal | inland | continental | mediterranean | alpine |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Vienna | X | X | X | | X | X | | |
| Barcelona | X | X | X | X | | | X | |
| Lisbon | X | X | | X | | | X | |
| Bern | X | | | | X | | | X |

---

### 4) Comparison with nominal scaling for `Population`

If `Population` used a nominal scale instead of an ordinal scale, the population attributes would be:

- `population: small`
- `population: medium`
- `population: large`

Each city would receive exactly one of these attributes.

With the ordinal scale, larger population values inherit lower threshold attributes. For example:

- `large` has `at-least-small`, `at-least-medium`, and `at-least-large`
- `medium` has `at-least-small` and `at-least-medium`
- `small` has only `at-least-small`

Therefore, the ordinal scale introduces a hierarchy between population values.

Structural difference:

- With nominal scaling, population categories are independent and incomparable.
- With ordinal scaling, population categories form nested concepts because `large` implies `medium` and `small` thresholds.

As a result, the concept lattice using ordinal scaling is more hierarchical and layered, while the lattice using nominal scaling is more fragmented because `small`, `medium`, and `large` are treated as separate unrelated categories.
