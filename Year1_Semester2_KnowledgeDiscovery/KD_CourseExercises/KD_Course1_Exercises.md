## 📖 Exercise 1

Regard the following formal context K, given as a cross table:

| Object | needs water to live | lives in water | lives on land | needs chlorophyll to produce food | two seed leaves | one seed leaf | can move around | has limbs | suckles its offspring |
|---|---|---|---|---|---|---|---|---|---|
| Leech | x | x | | | | | x | | |
| Bream | x | x | | | | | x | x | |
| Frog | x | x | x | | | | x | x | x |
| Spike-Weed | x | x | | x | | x | | | |
| Reed | x | x | x | x | | x | | | |
| Bean | x | | x | x | x | | | | |
| Maize | x | | x | x | | x | | | |

a) Specify the following sets:

  1. {Bean}′
  2. {lives on land}′
  3. {two seed leaves}′′
  4. {F rog, M aize}′
  5. {needs chlorophyll to producef ood, can move around}′
  6. {lives in water, lives on land}′
  7. {needs chlorophyll to producef ood, can move around}′
  
b) Extend K with both an object and an attribute.

---

### a) Derivations from the Table

To find the derivation of a set of objects, list all attributes that every object in that set shares.
To find the derivation of a set of attributes, list all objects that possess every attribute in that set.

**1. $\{Bean\}'$**
Look at the row for "Bean". List all columns with an "x".
*   **Result:** $\{needs\ water\ to\ live,\ lives\ on\ land,\ needs\ chlorophyll\ to\ produce\ food,\ two\ seed\ leaves\}$

**2. $\{lives\ on\ land\}'$**
Look at the column for "lives on land". List all rows with an "x".
*   **Result:** $\{Frog,\ Reed,\ Bean,\ Maize\}$

**3. $\{two\ seed\ leaves\}''**
First, find $\{two\ seed\ leaves\}'$. Only the "Bean" has this attribute. So, $\{two\ seed\ leaves\}' = \{Bean\}$. 
Next, find $\{Bean\}'$. We already solved this in Step 1.
*   **Result:** $\{needs\ water\ to\ live,\ lives\ on\ land,\ needs\ chlorophyll\ to\ produce\ food,\ two\ seed\ leaves\}$

**4. $\{Frog,\ Maize\}'$**
Find the attributes that *both* the Frog and the Maize share. The Frog has many attributes. The Maize has several.
The only ones they both have are "needs water to live" and "lives on land".
*   **Result:** $\{needs\ water\ to\ live,\ lives\ on\ land\}$

**5. $\{needs\ chlorophyll\ to\ produce\ food,\ can\ move\ around\}'$**
Find the objects that do *both* of these things. Plants have chlorophyll. Animals move around. No single object in this table does both.
*   **Result:** $\emptyset$ (The empty set)

**6. $\{lives\ in\ water,\ lives\ on\ land\}'$**
Find the objects that have an "x" in both the "lives in water" and "lives on land" columns. 
*   **Result:** $\{Frog,\ Reed\}$

**7. $\{needs\ chlorophyll\ to\ produce\ food,\ can\ move\ around\}'$**
This is a duplicate of question 5. 
*   **Result:** $\emptyset$

### b) Extend the Context

We will add a new object ("Dog") and a new attribute ("has fur"). 

| Object | needs water to live | lives in water | lives on land | needs chlorophyll to produce food | two seed leaves | one seed leaf | can move around | has limbs | suckles its offspring | **has fur** |
|---|---|---|---|---|---|---|---|---|---|---|
| Leech | x | x |  |  |  |  | x |  |  | |
| Bream | x | x |  |  |  |  | x | x |  | |
| Frog | x | x | x |  |  |  | x | x | x | |
| Spike-Weed | x | x |  | x |  | x |  |  |  | |
| Reed | x | x | x | x |  | x |  |  |  | |
| Bean | x |  | x | x | x |  |  |  |  | |
| Maize | x |  | x | x |  | x |  |  |  | |
| **Dog** | **x** | | **x** | | | | **x** | **x** | **x** | **x** |

---

## Exercise 3

### a) Definition of the Derivation Operator $(\cdot)'$

The derivation operator finds the connections between objects and attributes in a context $K = (G, M, I)$, where $G$ is a set of objects, $M$ is a set of attributes and $I$ is the relation between them.

1.  **For a set of objects $A \subseteq G$:** 
    $A'$ is the set of all attributes shared by *every* object in $A$. 
    Formula: $A' = \{m \in M \mid \forall g \in A: (g, m) \in I\}$
2.  **For a set of attributes $B \subseteq M$:** 
    $B'$ is the set of all objects that possess *every* attribute in $B$.
    Formula: $B' = \{g \in G \mid \forall m \in B: (g, m) \in I\}$

### b) Proofs

Let $K = (G, M, I)$ be a formal context. Let $A$ and $B$ be sets of objects ($A, B \subseteq G$). 

**1. Prove: $A \subseteq B$ implies $B' \subseteq A'$**
*   **Proof:** Let $m$ be an attribute in $B'$. This means every object in $B$ has the attribute $m$. We are told that $A$ is a subset of $B$ ($A \subseteq B$). Therefore, every object in $A$ is also inside $B$. Because all objects in $B$ have attribute $m$, all objects in $A$ must also have attribute $m$. Thus, $m$ belongs to $A'$. This proves $B' \subseteq A'$.

**2. Prove: $A \subseteq A''$**
*   **Proof:** Let $g$ be a specific object in set $A$. The set $A'$ contains all the attributes that are shared by *every* object in $A$. Therefore, object $g$ must possess all the attributes found in $A'$. The set $A''$ (which is $(A')'$) is defined as the set of all objects that possess all the attributes in $A'$. Since object $g$ possesses all attributes in $A'$, object $g$ must be in $A''$. This proves $A \subseteq A''$.

**3. Prove: $A' = A'''$**
*   **Proof:** We prove this in two steps by showing they are subsets of each other.
    *   *Step 1:* Replace $A$ with $A'$ in the rule we proved in part 2. This gives us $A' \subseteq (A')''$, which is $A' \subseteq A'''$.
    *   *Step 2:* We know from part 2 that $A \subseteq A''$. Apply the rule from part 1 to this statement. Reversing the order and adding a prime gives us $(A'')' \subseteq A'$, which is $A''' \subseteq A'$.
    *   *Conclusion:* Since $A'$ is a subset of $A'''$, and $A'''$ is a subset of $A'$, they must be exactly equal. Thus, $A' = A'''$.

**4. Prove: For $C \subseteq G$ and $D \subseteq M$, $(C, D)$ is a formal concept if and only if there is some $E \subseteq G$ such that $C = E''$ and $D = E'$.**
*   **Proof:** A pair $(C, D)$ is defined as a "formal concept" if the objects exactly map to the attributes ($C' = D$) and the attributes exactly map back to the objects ($D' = C$).
    *   *Forward Direction ($\Rightarrow$):* Assume $(C, D)$ is a formal concept. This means $C' = D$ and $D' = C$. Let the set $E$ be equal to $C$. Then $E' = C' = D$. And $E'' = (E')' = D' = C$. We have found our $E$.
    *   *Backward Direction ($\Leftarrow$):* Assume there is a set $E$ where $C = E''$ and $D = E'$. We need to prove $C' = D$ and $D' = C$.
        *   Test $C'$: $C' = (E'')' = E'''$. We proved in part 3 that $E''' = E'$. Since $E' = D$, then $C' = D$.
        *   Test $D'$: $D' = (E')' = E''$. We were given that $E'' = C$. So, $D' = C$.
    *   *Conclusion:* Both sides match the definition. The statement is proven.
