### Solution to the Exercise

#### a) Identify the sets \(G\), \(M\), and \(W\) explicitly.

- **\(G\) (Objects):** The items being described  
  \(G = \{\text{Vienna, Barcelona, Lisbon, Bern}\}\)

- **\(M\) (Attributes):** The categories or features evaluated for each object  
  \(M = \{\text{Population, Coastal?, Climate}\}\)

- **\(W\) (Attribute values):** All unique values appearing in the table  
  \(W = \{\text{large, medium, small, yes, no, continental, mediterranean, alpine}\}\)

---

#### b) Write \(I\) as a set of triples \((g, m, w)\)

The incidence relation \(I\) maps each table cell to a triple consisting of an object, an attribute, and its value:

\[
I = \{
\begin{aligned}
&(Vienna, Population, large), (Vienna, Coastal?, no), (Vienna, Climate, continental), \\
&(Barcelona, Population, large), (Barcelona, Coastal?, yes), (Barcelona, Climate, mediterranean), \\
&(Lisbon, Population, medium), (Lisbon, Coastal?, yes), (Lisbon, Climate, mediterranean), \\
&(Bern, Population, small), (Bern, Coastal?, no), (Bern, Climate, alpine)
\end{aligned}
\}
\]

---

#### c) Verify the functionality condition and identify the corresponding property

- **Verification:**  
  The functionality condition requires that each object has exactly one value per attribute.  
  The table satisfies this: every object–attribute pair has a single, unique value (e.g., Vienna’s population is only “large”).

- **Property:**  
  This corresponds to the defining property of a **mathematical function**—being *single-valued* (well-defined), where each input maps to exactly one output.

---

#### d) Why a standard formal context \((G, M, I)\) cannot represent this table

A standard formal context encodes only binary relations (presence/absence), so it cannot directly represent multi-valued attributes such as “large” or “alpine” within a single cell.
