<!-- --------------------------------------------------------------- -->
<!-- ---------------- COURSE 8 ANAPHORA RESOLUTION ----------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 8 - Anaphora and Co-reference Resolution**

## 📖 8.1 Core Concepts

Discourse is a group of related sentences or utterances, placed together. Each sentence adds to the overall meaning.
To understand a text, a system must map the complex semantic connections between these sentences.

🔴 **Anaphora Resolution** (_AR_) is the process of linking a word to an earlier or later item in the text:
* **Reference**: Using words to point to a specific entity;
* **Referent** (**Antecedent**): The actual entity being talked about;
* **Anaphor**: A word that points back to a previously mentioned entity;
* **Cataphora**: A word that points forward to an entity mentioned later;
* **Co-reference**: Two or more expressions referring to the exact same entity.

_Example: "John helped Tom. He was kind.". "John" is the antecedent, and "He" is the anaphor._
Anaphors can be **intrasentential** (_the antecedent is in the same sentence_) or **intersentential** (_the antecedent is in a different sentence_).

---

## 📖 8.2 Co-reference Chains and Formal Definitions

🔴 **Co-reference Resolution is the task of finding all words in a text that refer to the same entity**.
When an anaphor and multiple previous entities refer to the same thing, they form a **co-reference chain**.

Mathematically, this is defined using two relations:
* **Antecedes**(_$X,Y$_): A directional link where $X$ is the antecedent of anaphor $Y$. This relation is reflexive and transitive, but it is not symmetric;
* **Coref**(_$X,Y$_): An equivalence relation that holds if at least one direction of the "antecedes" relation applies or if they share a common antecedent.
It is reflexive, transitive and symmetric. This creates equivalence classes: $equiv(X)=\{Y|coref(X,Y)\}$. These classes represent the actual co-reference chains.

---

## 📖 8.3 The Role of AR in NLP Applications

Resolving anaphors is a notoriously difficult **Natural Language Processing** (_NLP_) task.
It is vital for many tools:
* **Automatic Translation**: Helps translate pronouns correctly between languages with different grammar rules;
* **Summarization**: Improves the quality of automatically generated text summaries;
* **Other Uses**: Information retrieval, question-answering, and text classification.

---

## 📖 8.4 Types of Anaphors

There are four primary types of anaphors:
1. **Pronominal**: The referent is replaced by a pronoun. This includes personal pronouns ("he"), possessive ("his"), reflexive ("himself"), demonstrative ("this") and relative ("who");
2. **Definite Noun Phrase**: The referent is replaced by a phrase starting with "the". Example: "a Ford Mustang" becomes "The Mustang";
3. **Quantifier / Ordinal**: The anaphor is a number word like 'one' or 'first';
4. **Verb Phrase**: An action is referred back to using a substitute verb like "did".

---

## 📖 8.5 Traditional Approaches to Resolution

Traditional systems filter out bad options and score the good ones.

### 📑 8.5.1 Hard Constraints (Eliminative)
**These are strict rules to filter out impossible referents**:
* **Agreement**: The anaphor and referent must match in number, gender, person and case;
* **Syntactic Constraints**: Grammar rules limit matches. For instance, a reflexive pronoun ("himself") must refer to the subject of its immediate sentence clause;
* **Selectional Restrictions**: Verbs require specific types of objects. _Example: You can "drive" a car, but you cannot "drive" a garage_.

### 📑 8.5.2 Weighting Preferences
**These factors assign a likelihood score to competing referents**:
* **Recency**: Recently mentioned entities are preferred;
* **Grammatical Role**: Subjects are prioritized over objects;
* **Repeated Mention**: Entities frequently discussed in the text are prioritized;
* **Parallelism**: Pronouns tend to match the grammatical role (like subject or object) of their antecedents;
* **Verb Semantics**: The implied cause of a verb focuses attention on a specific subject or object.

---

## 📖 8.6 Key Traditional Algorithms

### 📑 8.6.1 Lappin and Leass Algorithm
🔴 **This algorithm requires a fully analyzed sentence structure**.
It applies syntactic hard constraints to eliminate bad matches.
It assigns **salience weights** to surviving candidates based on their grammatical role.
Examples of initial weights include sentence recency (100) and subject emphasis (80).
**The candidate with the highest total weight wins**.

### 📑 8.6.2 Mitkov's Algorithm
🔴 **This algorithm avoids complex grammar analysis**.
It looks at noun phrases up to two sentences back and filters them by gender and number.
It applies a simple scoring system using **boosting indicators** (adds points for good signs, like being the
first noun or repeating often) and **impeding indicators** (subtracts points for bad signs, like being indefinite).
**The highest-scoring phrase is selected**.

---

## 📖 8.7 Machine Learning Approach

Modern systems often use **Machine Learning** (_ML_).
A well-known system by Wee Meng Soon uses annotated training documents:
* **Extract Markables**: A pipeline identifies all potential noun phrases and names, called "markables";
* **Generate Features**: The system creates a feature vector containing 12 traits for every pair of words.
Key features check distance, pronoun status, string matching, gender/number agreement and whether they are proper names;
* **Train Classifier**: A decision tree learns from positive examples (adjacent pairs in a chain) and negative examples (unrelated pairs);
* **Resolve**: For a new text, the tree tests potential antecedents in reverse document order until it finds a match.
