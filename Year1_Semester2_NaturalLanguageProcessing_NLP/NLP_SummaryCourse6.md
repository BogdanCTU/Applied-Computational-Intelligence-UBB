<!-- --------------------------------------------------------------- -->
<!-- ------------------------ COURSE 6 HMM ------------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 6 - Hidden Markov Model (HMM)**

## 📖 6.1 Introduction to Hidden Markov Models (_HMM_)

🔴 **An HMM is a statistical machine learning tool used for sequence classification and text processing**.
It looks at a sequence of items and finds the best sequence of labels for them.
HMMs use probability to link two types of events:
* **Observed events**: Things we can see in our data, such as words in a sentence;
* **Hidden events**: Things we cannot see but act as causes, such as grammatical part-of-speech (POS) tags.
HMMs are widely used in speech recognition (observed: sounds, hidden: words), part-of-speech tagging (observed: words, hidden: tags), and machine translation.

### 📑 6.1.1 Formal Definition

🔴 **An HMM is a finite state automaton** (**a machine that moves between different states**) **that uses random probabilities to transition between states and emit symbols**.
It models a generative process. This means it creates a sequence by starting in an initial state, moving to a new state, and outputting an observed symbol.
The mathematical model is defined as $M=(Q,V,A,B,q_{0})$:
* $Q$: A set of hidden states;
* $V$: An alphabet of possible observations (emissions);
* $A$: The transition probability matrix. This is the chance of moving from one hidden state to another;
* $B$: The emission probability matrix. This is the chance of a hidden state generating a specific observation;
* $q_{0}$: The starting state, which does not emit any observation.

### 📑 6.1.2 Key Assumptions

To make the math simple, HMMs rely on two strict rules:
* **Markov Assumption**: The probability of the next state depends only on the current state, ignoring all older history. The formula is $P(q_{i}|q_{1},...,q_{i-1})=P(q_{i}|q_{i-1})$.
* **Output Independence**: The probability of an observed event depends only on the hidden state that made it, ignoring all other states or observations.
  The formula is $P(o_{i}|q_{1}...q_{i}...q_{T},o_{1}...o_{i}...o_{T})=P(o_{i}|q_{i})$. Note, "o1, o2, o3" are the output sequence (the sequence of observations)

<img width="813" height="267" alt="image" src="https://github.com/user-attachments/assets/e0c06f90-9151-4dd9-b0c8-0b357812b327" />

> ##### Image: Temporal evolution of an HMM

---

## 📖 6.2 The Three Canonical Problems of HMMs

When working with HMMs, there are three main mathematical tasks:
* **Problem 1 - Evaluation**: We want to know how well a specific HMM matches a given sequence of observations. This uses the Forward algorithm;
* **Problem 2 - Decoding**: We have an observation sequence, and we want to uncover the hidden states that most likely created it. This uses the Viterbi algorithm;
* **Problem 3 - Learning**: We have data, and we want to train the HMM by finding the best transition and emission probabilities. This uses the Baum-Welch algorithm.

---

## 📖 6.3 Core Algorithms

Both the Forward and Viterbi algorithms use dynamic programming. They process events in a sequence step-by-step.
* **Forward Algorithm**: Calculates the overall probability that a sequence of observations could happen at all. It does this by adding up the probabilities of every possible path through the hidden states;
* **Viterbi Algorithm**: Finds the single best path of hidden states. Instead of adding probabilities, it looks for the maximum probability at each step and uses a "backpointer" to remember the winning path;

## 📖 6.3.1 Weather Problem Example
If Alice only observes Bob's activities (Walk, Shop, Clean), she can use the Viterbi algorithm to guess the hidden weather (Rainy, Sunny) that caused those activities.

* HMM - finite state automaton
    * M = (Q, V, A, B, q0);
    * Q = {Rainy, Sunny}, _states(hidden events)_;
    * V = {Walk, Shop, Clean}, _observations_;
    * q0 = Start / Start State;
    * model: u=(A,B).

The **transition probability matrix** A:

| A      | Rainy                 | Sunny                  |
|--------|-----------------------|------------------------|
| Start  | P(Rainy|Start) = 0.6  | P(Sunny|Start) = 0.4   |
| Rainy  | P(Rainy|Rainy) = 0.7  | P(Sunny|Rainy) = 0.3   |
| Sunny  | P(Rainy|Sunny) = 0.4  |  P(Sunny|Sunny) = 0.6  |

The **emission probability matrix** B:

| B      | Walk                 | Shop                   | Clean               |
|--------|----------------------|------------------------|---------------------|
| Rainy  | P(Walk|Rainy) = 0.1  | P(Shop|Rainy) = 0.4  | P(Clean|Rainy) = 0.5  |
| Sunny  | P(Walk|Sunny) = 0.6  | P(Shop|Sunny) = 0.3  | P(Clean|Sunny) = 0.1  |

<img width="697" height="390" alt="image" src="https://github.com/user-attachments/assets/8132357c-6499-4e30-9082-5882aeef9e5a" />

> ##### Image: HMM State Machine

Forward Algorithm calculations over the probability of a sequence of observations:

| Time:     | Day 1 (t=1)           | Day 2 (t=2)                                                 | Day 3 (t=3)                                                      |
|-----------|-----------------------|-------------------------------------------------------------|------------------------------------------------------------------|
| Forward:  | Walk                  | Shop                                                        | Clean                                                            |
| Rainy     | 0.6 * 0.1 = **0.06**  | **0.06** * 0.7 * 0.4 + **0.24** * 0.4 * 0.4 = _**0.0552**_  | _**0.0552**_ * 0.7 * 0.5 + _**0.0486**_ * 0.4 * 0.5 = 0.02904    |
| Sunny     | 0.4 * 0.6 = **0.24**  | **0.06** * 0.3 * 0.3 + **0.24** * 0.6 * 0.3 = _**0.0486**_  | _**0.0552**_ * 0.3 * 0.1 + _**0.0486**_ * 0.6  * 0.1 = 0.004476  |

---

## 📖 6.4 Application: Part-of-Speech (POS) Tagging

**POS Tagging is the process of labeling each word in a text with its grammatical class**, **like noun or verb**.
It helps computers process text for searches, information extraction and correct pronunciation.
**How HMMs do it**:
* **Words are the observed events**;
* **POS tags are the hidden events**;
* **Transition Probability** $P(t2|t1)$: The chance of one tag following another (e.g., a noun following an adjective);
* **Emission Probability** $P(w|t)$: The chance of a specific tag emitting a specific word (e.g., the tag "Verb" emitting the word "race").

To decode a sentence (like "I want to race"), the system runs the Viterbi algorithm to find the sequence of POS tags with the highest final probability.
