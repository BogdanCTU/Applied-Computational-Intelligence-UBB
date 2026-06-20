# Temporal Concept Analysis (TCA) — Integrated Course Summary

## 0. Preliminaries: Formal Concept Analysis (FCA)

### Formal Context
A **formal context** is a triple:
$$K = (G, M, I)$$
where:
- $G$ = set of objects
- $M$ = set of attributes
- $I \subseteq G \times M$ is an incidence relation

### Derivation Operators
For $A \subseteq G$, $B \subseteq M$:
- $A' = \{ m \in M \mid \forall g \in A: (g,m)\in I \}$
- $B' = \{ g \in G \mid \forall m \in B: (g,m)\in I \}$

A **formal concept** is a pair:
$$ (A, B) \text{ such that } A' = B \text{ and } B' = A $$

The set of all concepts forms a **concept lattice**:
$$\mathcal{B}(K)$$

---

## 1. Motivation for Temporal Concept Analysis

Classical FCA is **static**: it describes a single state of knowledge.

Many real systems are dynamic:
- patients evolve clinically
- industrial systems change state over time
- user behavior unfolds sequentially

**Key limitation of FCA:**
It cannot directly represent **conceptual evolution over time**.

### Goal of TCA
Temporal Concept Analysis introduces a framework to represent:
- conceptual states over time
- transitions between states
- structured trajectories of objects through concept space

---

## 2. Time Representation: Granules and Ordering

### Time Granules
Time is modeled as a set of discrete or structured units:
$$G_T = \{g_1, g_2, \dots\}$$

A **time granule** represents an observation unit:
- timestamp
- interval
- event index
- calendar unit

Granules may form:
- chains (linear time)
- partial orders
- trees (branching time)

A successor relation is often assumed:
$$ g \prec g' $$

---

## 3. Conceptual Time System (CTS)

A **Conceptual Time System** separates time and observations.

### Definition (structural form)
A CTS consists of:
- a time structure over granules $G_T$
- an event context describing attributes over those granules

Event context:
$$K_e = (G_T, M_e, I_e)$$

Time structure:
- typically an order or scale on $G_T$
- may be represented as a separate context or relational structure

> Interpretation: time is a structured index; events are attribute observations indexed by time.

---

## 4. States: Conceptual Representation of Time Points

For each granule $g \in G_T$, we derive a **state** from the event context.

### State Definition
A state is a formal concept induced by a granule:
$$
\sigma(g) = ( \{g\}'', \{g\}' ) \in \mathcal{B}(K_e)
$$

where:
- $\{g\}'$ = attributes observed at $g$
- $\{g\}''$ = reconstructed extent of equivalent granules

### State Space
The set of all reachable states:
$$
\Sigma = \{ \sigma(g) \mid g \in G_T \} \subseteq \mathcal{B}(K_e)
$$

The state space is partially ordered by the inherited order of the concept lattice, but is not necessarily a sublattice.

---

## 5. Transitions and State Dynamics

### Transition Relation
Given a successor relation on time:
$$ g \prec g' $$

we define a transition:
$$ \sigma(g) \to \sigma(g') $$

This induces a **state-transition graph**:
$$ S = (\Sigma, \to) $$

### Key properties
- transitions depend on time ordering, not lattice order
- multiple granules may map to the same state
- cycles and recurrent states may occur

---

## 6. Objects and CTS with Observation Structure (CTSOT)

To model multiple entities:

### CTSOT Structure
A CTSOT is:
$$ (P, G_T, \rho, K_e) $$

where:
- $P$ = set of objects (patients, machines, users)
- $G_T$ = time granules
- $\rho \subseteq P \times G_T$ = observation relation
- $K_e$ = event context

### Life-track
For each object $p \in P$, its **life-track** is:
$$
\text{life}_p : G_p \to \mathcal{B}(K_e)
$$
where:
$$G_p = \{ g \in G_T \mid (p,g) \in \rho \}$$

A life-track is a sequence (or partial sequence) of states:
$$
\sigma_p(g_1), \sigma_p(g_2), \dots
$$

---

## 7. Trajectories and Behavioral Analysis

A **trajectory** is the temporal evolution of a life-track:
- linear sequence (totally ordered time)
- branching structure (partial order)
- piecewise-constant segments

### Analytical structures
- **Reachability:** states accessible from a given state
- **Cycles:** recurrent behavioral loops
- **Sojourn time:** time spent in a state
- **Persistence:** stability of state occupancy

---

## 8. Granularity and Scaling

Granularity defines observational resolution:
- seconds → minutes → hours
- events → sessions → phases

### Refinement and Coarsening
Changing granularity modifies:
- number of states
- transition density
- conceptual abstraction level

This is a **scaling operation on the time structure**, not a change in semantics.

---

## 9. Conceptual Semantic Systems (CSS)

A **CSS** generalizes CTS by introducing multiple contextual dimensions.

Each dimension is a formal context over shared granules:
- temporal context
- spatial context
- social context
- causal context

### Structural idea
A CSS is a family:
$$ (K_i)_{i \in I} $$

Each object evolves in a **product space of concept lattices**:
$$ \mathcal{B}(K_1) \times \cdots \times \mathcal{B}(K_n) $$

Dependencies between dimensions appear as constraints on joint transitions.

---

## 10. Patterns, Implications, and Process Mining

### Types of temporal structure

- **State implications:** structural constraints in event context
- **Transition constraints:** restrictions on successor states
- **Path patterns:** temporal rules over sequences

### Process mining interpretation
CTSOT data corresponds to event logs:
- cases = objects
- timestamps = granules
- activities = attributes

TCA yields:
- state-transition abstractions of workflows
- interpretable process structure
- deviation detection via forbidden transitions

---

## 11. Relation to Temporal Logics

Temporal patterns correspond to logical operators:

- $X\varphi$ (next state): direct transition
- $F\varphi$ (eventually): reachability
- $G\varphi$ (always): invariance over trajectories
- $\varphi U \psi$ (until): constrained paths

TCA provides a **constructive, lattice-based semantics** for temporal reasoning.

---

## 12. Extensions Beyond Dyadic TCA

### 12.1 Triadic FCA Integration

A **triadic context**:
$$K_3 = (G, M, B, Y)$$
where:
- $G$ = objects
- $M$ = attributes
- $B$ = conditions
- $Y \subseteq G \times M \times B$

### Temporal Triadic Extension (3FCA + TCA)

Event structure becomes:
$$T_e^{(3)} = (G_T, M_e, B, Y_e)$$

This enables modeling:
- observer-dependent measurements
- contextual variability of attributes
- multi-perspective temporal states

### Important correction
- Triadic extensions are **not part of core TCA**
- they are **orthogonal generalizations combining FCA frameworks**

---

## 13. Computational Aspects

### Complexity considerations
- Concept enumeration is generally **exponential in worst case**
- State construction requires closure computation per granule
- Transition construction is linear in observed transitions

### Key algorithms
- Next-closure algorithm (Ganter)
- Incremental FCA updates
- Streaming adaptations for temporal data

### Practical constraint
Scalability depends primarily on:
- attribute set size
- density of incidence relation
- granule count

---

## 14. Applications

### Healthcare
- patient state evolution
- disease progression patterns
- treatment pathway analysis

### Industrial systems
- fault detection via forbidden transitions
- process monitoring
- predictive maintenance

### Behavioral analytics
- user session modeling
- recommendation systems
- activity segmentation

### Biology and ecology
- migration patterns
- behavioral cycles
- environmental adaptation trajectories

---

## 15. Key Theoretical Insights

### Fundamental principles

1. **States are concepts**
   - each time point maps to a formal concept

2. **Time induces dynamics**
   - transitions arise from ordering of granules

3. **Life-tracks are conceptual paths**
   - objects evolve through the concept lattice

4. **Granularity defines abstraction**
   - resolution controls state structure

5. **TCA separates structure from dynamics**
   - lattice = structure, time = evolution driver

---

## 16. Summary Definition Set

| Term | Definition |
|------|-----------|
| Formal Context | $K=(G,M,I)$ incidence structure |
| Concept | $(A,B)$ with Galois connection closure |
| Concept Lattice | $\mathcal{B}(K)$ ordered by inclusion |
| Time Granule | atomic unit of observation in time |
| CTS | combination of time structure + event context |
| State | $\sigma(g) \in \mathcal{B}(K_e)$ |
| Transition | $\sigma(g) \to \sigma(g')$ if $g \prec g'$ |
| Life-track | mapping from granules to states |
| CTSOT | CTS extended with object set and observation relation |
| CSS | multi-context generalization of CTS |

---

## 17. Closing Perspective

Temporal Concept Analysis provides a structured mechanism to transform static concept lattices into dynamic systems by embedding them in time-indexed observation frameworks.

The core abstraction is:

> **Concepts become states, and time becomes the ordering principle that generates motion through the concept lattice.**
