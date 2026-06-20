# Knowledge Discovery — Lecture 8 Summary
# Temporal Concept Analysis (TCA): Foundations, Life-Tracks and Applications

> **Lecturer:** Christian Săcărea — Babeș–Bolyai University, Cluj-Napoca (May 18, 2026)  
> **Prerequisite:** Familiarity with formal contexts K=(G,M,I), concept lattices B(K), derivation operators A′, B′, and conceptual scaling.

---

## 1. Motivation & Historical Context

### Why Temporal?
- Classical FCA is **static**: a formal context K=(G,M,I) captures a single snapshot in time.
- Real systems change (patients, markets, organisms) → we need **trajectories of conceptual states**, not just inventories.
- Standard workarounds (time-stamped attributes, nested contexts) lose conceptual clarity.
- **Guiding question:** *If a concept lattice is a map of conceptual space, what is the map of conceptual motion?*

### Historical Thread
| Year | Event |
|------|-------|
| 1982 | Wille introduces FCA (order-theoretic restitution of Birkhoff's theorem) |
| 1996 | Ganter & Wille FCA monograph |
| 2001–2005 | Karl Erich Wolff develops **Temporal Concept Analysis** |
| 2002 | Wolff: "Temporal Concept Analysis" (ICCS workshop) |
| 2005 | Wolff: "States, Transitions, and Life Tracks in TCA" |
| Ongoing | Distributed, granular, fuzzy TCA; process mining; biology |

---

## 2. From Static to Temporal: Key Ideas

### Three Approaches to Time in FCA
1. **Time-stamped data** — facts tagged with time points; lattices built per time-slice → no conceptual motion.
2. **Time as attribute** — time appears as values in a many-valued context; lattices mix space and time.
3. **TCA (Wolff)** — time is an ordered set of granules; objects have **life-tracks**; states are concepts; transitions are lattice edges. ← *TCA chooses this route.*

### Two Parts of Every Temporal Observation
- **Time part** — *when*: granules, intervals, calendar structure, ordering.
- **Event part** — *what*: properties, measurements, classifications at that moment.

---

## 3. Conceptual Time Systems (CTS)

### Time Granules
- A **time granule** is a unit of observation (e.g., "year 2025", "9 May 14:32", "second visit").
- Granules can be nested, partially ordered, overlapping, or disjoint.
- The time part is itself a formal context describing the granule structure.
- *Slogan: "Time is what you measure with your time-context."*

### Definition: CTS (Wolff 2002)
A **Conceptual Time System** on a set G of time granules is a pair:

$$\mathbf{T} = (T_t, T_e)$$

- **T_t = (G, M_t, I_t)** — *time part*: describes when (ordering, calendar, nesting).
- **T_e = (G, M_e, I_e)** — *event part*: describes what (properties at each granule).
- Both contexts **share the same object set G** (time granules).

### Example: Apartment Temperature
- G = {0, 1, 2, 3, 4} (five minutes).
- Event attributes: {cool, medium, warm}.
- Time part: ordinal scale giving a chain.
- Each granule maps to one concept (state) in B(T_e).

---

## 4. States, Transitions, and the State Graph

### Definition: State
For a granule g ∈ G, the **state** at g is the formal concept generated in the event part:

$$\text{state}(g) = \bigl(\{g\}'', \{g\}'\bigr) \in \mathcal{B}(T_e)$$

- The **projection** σ: G → B(T_e), g ↦ state(g) maps every granule to its concept.
- States live in the concept lattice B(T_e).

### Definition: Transition
Given immediate-successor relation ≺ derived from T_t:

$$\sigma(g) \to \sigma(g') \quad \text{whenever } g \prec g'$$

- Repeated visits create **multi-edges**.
- The **state-transition graph**: S(T) = (σ(G), →, label).

### State Space
$$\Sigma(\mathbf{T}) = \sigma(G) \subseteq \mathcal{B}(T_e)$$

- Inherits the lattice order.
- **Important:** transitions can go up, down, or sideways — they are NOT the lattice order.

### Granularity Refinement
- **Coarsening** granules → fewer, larger states.
- **Refinement** → more, smaller states.
- Conceptual scaling of the time part is the formal mechanism.
- **Useful fact:** If T_t ≤ T′_t (T′ refines T), the induced state map factors through a surjective lattice map of state spaces.

---

## 5. Objects, Life-Tracks, and Trajectories

### CTS with Objects and Time Relation (ctsot)
A **ctsot** is a tuple (P, G, ρ, T_t, T_e) where:
- **P** — set of objects ("particles", persons, processes).
- **G** — set of time granules.
- **ρ ⊆ P × G** — assigns observed granules to each object.
- T_t, T_e — time and event parts.

### Definition: Life-Track
The **life-track** of object p ∈ P is the function:

$$\text{life}_p : G_p \to \mathcal{B}(T_e), \quad g \mapsto \text{state}_p(g)$$

where G_p = {g ∈ G | (p, g) ∈ ρ} is the time-domain of p.

- A life-track is a **path through the concept lattice indexed by time granules**.
- Different objects can share states/transitions; only their indexing differs.

### Trajectories
- **Discrete time:** sequence s₀, s₁, s₂, …
- **Branching time:** tree of state-edges.
- **Continuous time:** piecewise-constant map from intervals to states.

Trajectories enable queries such as:
- Which sub-lattices are reachable from a given state?
- What are the cycles?
- Are two life-tracks conceptually similar?

### Reachability and Basins
- **Forward basin** of s: {s′ | s ⇒ s′}
- **Backward basin**: {s′ | s′ ⇒ s}
- **Strongly connected components**: equivalence classes of ⇔

### Sojourn Times and Persistence
- **Sojourn time** in state s = cumulative length of granules an object spends in state s.
- **Persistence** is a property of trajectories, not of concepts.
- Encoded by enriching the time part with duration scales (log, ordinal, nominal).

---

## 6. Worked Examples

### Example 1 — Apartment Temperature
- σ(0)=σ(1)=**med**, σ(2)=**warm**, σ(3)=**cool**, σ(4)=**med**
- Transition graph: med → med → warm → cool → med
- Lattice B(T_e) = diamond {⊥, cool, med, warm, ⊤}; trajectory lives in the antichain layer.

### Example 2 — Patient Pathway
- P = {Alice, Bob}; G = {v₁,...,v₆} (clinic visits); attributes: fever, cough, rash, recovered.
- States computed: s₁={fever,cough}, s₂={fever,cough,rash}, s₃={cough}, s₄={recovered}, s₅={fever}
- Alice: s₁→s₂→s₃→s₄ (linear recovery); Bob: s₅→s₁ (still climbing)
- Two trajectories sharing state s₁ with different futures.

### Example 3 — Particle Motion in 1D
- Event part: nominal scale on position bins b₁,...,bₖ → flat antichain lattice.
- Adding velocity bins → product of two antichains → orbit in 2D conceptual phase space.

### Example 4 — Animal Habitat Use
- Wolf tracked 24 months; granule = month; attributes: habitat type, altitude band, pack size.
- Seasonal cycles appear as **loops of length 12** in the lattice.
- Implications like "high altitude ⇒ low pack size" show up as **forbidden transitions**.

### Example 5 — Stock Prices
- Event attributes: "up day", "down day", "high volume" → ≤8 atoms in state lattice.
- Long trajectories live in a tiny lattice; transition matrix carries the signal.
- vs. HMMs: TCA gives the **observable skeleton**; HMMs add hidden state.

---

## 7. Time Granularity

### Granularity Hierarchies
- Nested hierarchy: sec ⊂ min ⊂ hour ⊂ day ⊂ week ⊂ month ⊂ year.
- Each level encoded by a scale on the time part; switching granularity = applying a different scale.

### Calendar Contexts
- Time part objects = days; attributes = month, weekday, season, holiday.
- Benefits: trajectories get calendar context for free; discover implications like "Sunday + summer ⇒ low traffic".

### Three Flavours of Time Part
| Type | Description |
|------|-------------|
| **Ordinal time** | Chain of granules (classical). |
| **Interval time** | Granules are intervals; Allen's 13 relations encoded as attributes. |
| **Branching time** | Granules form a tree/DAG; for concurrent processes. |

---

## 8. Conceptual Semantic Systems (CSS)

**Wolff's generalisation of CTS:**
- Time is just one dimension; multiple "parts" are possible (spatial, social, causal, linguistic).
- Each part is a formal context on shared granules.
- A CSS = family (Cᵢ)_{i∈I} of contexts with shared objects plus inter-part relations.

### Product Lattices and Trajectory Geometry
- Trajectories live in B₁ × ··· × Bₖ (product of concept lattices of all parts).
- **Independent transitions** = parallel motion.
- **Coupled transitions** = constraints in the joint lattice.
- TCA detects coupling via implications (sᵢ→s′ᵢ) ⇒ (sⱼ→s′ⱼ).

---

## 9. Implications, Patterns, and Process Mining

### Types of Temporal Implications
| Type | Description |
|------|-------------|
| **State implication** | B₁ ⇒ B₂ in T_e — structural/static rule |
| **Transition implication** | s→? ⇒ ?∈S′ — restricts successors |
| **Path implication** | "after s₁s₂s₃, eventually s₅" — temporal logic statement |

### Connections to Temporal Logics (LTL/CTL)
- **Xφ** — next-state via transition concept
- **Fφ** — reachability of a state with intent including φ
- **Gφ** — invariant on a forward basin
- **φUψ** — expressible via lattice ideals in the trajectory
- TCA gives a **constructive semantics**: model-checking = navigating a lattice.

### Process Mining with TCA
- Workflow logs are naturally CTSOTs: P=cases, G=timestamps, attributes=activity/resource.
- Mining the state graph yields a **declarative process model**.
- vs. α-mining (Petri nets): TCA yields lattices — often more compact and interpretable.

---

## 10. Distributed and Fuzzy Extensions

### Distributed CTS
- Multiple agents with local CTSs T⁽ⁱ⁾, synchronised via shared granules.
- Joint state space = compatible subset of ∏ᵢ Σ(T⁽ⁱ⁾).
- Applications: multi-agent systems, sensor networks, biological populations.

### Fuzzy/Graded TCA
- Replace crisp incidence with I: G × M → [0,1].
- Fuzzy concepts via **residuated derivation operators**.
- **Fuzzy states**: each granule weighted across concepts.
- Practical caveat: heavier computation; typically thresholded at runtime.

### Pattern Structures and TCA
- **Pattern structures** (Ganter & Kuznetsov): generalise formal contexts to meet-semilattices of descriptions.
- TCA with pattern structures → trajectories over description lattices.
- Application: trajectories of molecular structures or network snapshots.

---

## 11. Algorithms and Tools

### Computing TCA Artefacts
| Artefact | Complexity |
|----------|------------|
| States | One closure per granule — O(|G|·|M_e|²) |
| Transitions | One per consecutive granule pair |
| State graph | Hash states by intent, then aggregate |
| Trajectory statistics | Linear scan per object |

- **Next-closure** (Ganter): canonical enumeration in lectic order.
- **Incremental algorithms** (Norris, Godin, van der Merwe): essential for streaming TCA.
- Lattice size: |B(K)| can be exponential; output enumeration O(|B(K)|·|G|·|M|).

### Software Tools
| Tool | Notes |
|------|-------|
| **ToscanaJ** | Many-valued contexts, scaling, nested line diagrams; best CTS support |
| **ConExp / ConExp-NG** | Classical FCA |
| **FCA4J** | Java library; pattern structures, TCA extensions |
| **concepts, fcapsy (Python)** | Recent packages |
| **fcaR (R)** | Recent package |

### Visualisation — Nested Line Diagrams
- **Outer lattice** = projection onto a small attribute subset.
- **Inner lattices** = remaining attributes within each outer cell.
- TCA bonus: trajectories appear as movements between inner cells; outer structure shows long-term phases.

---

## 12. Applications

| Domain | Key Use |
|--------|---------|
| **Medicine / Healthcare** | Patient histories as life-tracks; typical vs. chronic trajectories; rare transitions flagging complications; SNOMED ontologies as scales |
| **Behavioural / Ecological** | Animal movement, foraging, predator-prey cycles; seasonal life-tracks; inter-species comparison |
| **Industrial Processes** | Reactor state supervision; fault diagnosis via forbidden transitions; predictive maintenance |
| **Information Retrieval / Web** | User-session trajectories; conceptual recommendation; time-aware faceted search |
| **Music & Language** | Chord progressions; linguistic register shifts; stylometry as recurrent state cycles |

---

## 13. TCA Meets Triadic FCA (3FCA)

### Background: Triadic FCA
**Definition (Lehmann & Wille 1995):** A **triadic context** K₃ = (G, M, B, Y) where:
- G = objects, M = attributes, B = conditions, Y ⊆ G×M×B.
- (g, m, b) ∈ Y: "object g has attribute m under condition b".

**Triadic concept:** A maximal triple (A₁, A₂, A₃) ⊆ G×M×B such that A₁×A₂×A₃ ⊆ Y.

The set of all triadic concepts forms a **trilattice** with three quasi-orders.

**Derivation:** Three families of operators (one per pair of axes); composing two gives a closure operator. Three dyadic projections: B₁₂, B₁₃, B₂₃.

### Connection 1: Time as the Third Axis
- Let B = G_T (time granules); read (g, m, t) ∈ Y as "g has m at time t".
- **Pro:** Single triadic context absorbs temporal data; projections give "object trajectory" (B_{GB}) and "attribute calendar" (B_{MB}) for free.
- **Con:** Collapses Wolff's time part / event part distinction; ignores temporal structure (order, granularity).
- **Take-away:** "Time as third axis" is correct but not enough — time must be structured.

### Connection 2: 3FCA inside the Event Part
- Many event observations are intrinsically triadic:
  - Patient × symptom × observer
  - Process case × activity × resource
  - Animal × behaviour × context
- Forcing such data into a dyadic event part loses information.

### Definition: Triadic CTS (Proposed)
$$\mathbf{T}_3 = \bigl(T_t,\, T_e^{(3)}\bigr)$$

- **T_t = (G, M_t, I_t)** — dyadic time part (unchanged).
- **T_e^(3) = (G, M_e, B, Y_e)**, Y_e ⊆ G × M_e × B — **triadic event part** where the first axis is the time-granule set.
- *Intuition:* at each granule we observe a **matrix of (attribute, condition) facts**, not just a row.

### States in Temporal 3FCA
For each granule g ∈ G, three kinds of state are extracted:
- **σ_M(g)** ∈ B(M_e, B, Y(g)) — the (attribute, condition) concept at g.
- Projections give attribute-shadow state and condition-shadow state.
- Full σ(g) is a triadic concept in T(T_e^{(3)}).
- Life-tracks become paths in a **trilattice** — three coupled trajectories per object.

### Triadic Implications (Transitions)
- Transition implications live in three dyadic projections plus coupling implications.
- Coupling detects patterns like "when the symptom set changes, the responsible observer also changes" — *inaccessible in dyadic TCA*.

### Tetradic Outlook
- Add time as a **4th axis**: Y₄ ⊆ G×M×B×T → polyadic FCA (Voutsadakis, Cerf et al.).
- Four derivation operator families; six dyadic projections; four triadic projections.
- Algorithm: Data-Peeler extends to 4-cliques.
- Temporal 3FCA = structured slice of polyadic FCA where one axis carries an order.

### Worked Sketch — Medical Records
- Objects: hospital admissions; conditions B: {physician, nurse, lab}; attributes M: symptoms; granules G: visit timestamps.
- Triadic states reveal **who-knew-what-when** patterns.
- Life-track in trilattice = information propagation across care team over time.
- Dyadic TCA would flatten observer into "noise"; triadic TCA makes it a first-class participant.

---

## 14. Methodological Reflections

### What TCA Does NOT Replace
| Limitation | Alternative |
|------------|-------------|
| Probabilistic forecasts | HMMs, Bayesian nets |
| Hidden state discovery | Latent-variable models |
| Massive trajectory scaling without aggregation | Aggregation pipelines |

TCA provides a **transparent skeleton** on which probabilistic or learning models can be built.

### Choosing Your Contexts (Critical Practical Advice)
Quality of TCA depends almost entirely on:
1. **Choice of event attributes** — what counts as "state"?
2. **Choice of time granularity** — how coarse/fine?
3. **Choice of scales** on many-valued data.

> **Rule of thumb:** Start coarse, refine until trajectories become informative without exploding the lattice.

### Open Problems
- Scalability of incremental TCA on **streaming data**.
- **Probabilistic TCA**: mixing concept lattices with Markov models.
- Statistical inference for **transition implications**.
- Categorical foundations: TCA as a functor from time categories to lattice categories.
- TCA-based **explanations for ML predictions** on temporal data.
- Representation theorem for trilattices equipped with a successor relation on one axis.
- Efficient incremental enumeration of triadic states along a stream of granules.

---

## 15. Summary & Key Takeaways

> **TCA in one sentence:** A Conceptual Time System is a pair of formal contexts on the same granules; **states are concepts**; **life-tracks are paths in the concept lattice indexed by time**; everything else is elaboration.

| Principle | Core Idea |
|-----------|-----------|
| Dual context | Treat time and events on equal conceptual footing |
| States = intents | State of a granule is the formal concept it generates in B(T_e) |
| Transitions = edges | Conceptual motion follows the succession of granules |
| Granularity is a choice | Scaling, not metaphysics — coarsen or refine as needed |
| Trajectories animate the lattice | Life-tracks make the static lattice come alive |

---

## Key Definitions at a Glance

| Term | Definition |
|------|------------|
| **CTS** | Pair T=(T_t, T_e) of formal contexts sharing the granule set G |
| **Time granule** | Unit of observation (year, visit, simulation step, etc.) |
| **State σ(g)** | Formal concept ({g}'', {g}') ∈ B(T_e) generated at granule g |
| **Transition** | Edge σ(g)→σ(g′) whenever g ≺ g′ |
| **Life-track** | Function life_p: G_p → B(T_e), mapping granules of object p to states |
| **Trajectory** | Life-track viewed as a labeled sequence/tree/map in B(T_e) |
| **Sojourn time** | Cumulative time an object spends in a state along its life-track |
| **ctsot** | CTS extended with a set of objects P and observation relation ρ ⊆ P×G |
| **CSS** | Generalization of CTS with multiple contextual axes (spatial, social, etc.) |
| **Triadic CTS** | CTS with a triadic event part T_e^(3) encoding (attribute, condition) matrices |

---

*References: Ganter & Wille (1999), Wolff (2001, 2003, 2005, 2007), Lehmann & Wille (1995), Biedermann (1998), Voutsadakis (2002), Cerf et al. (2009), Ganter & Kuznetsov (2001).*
