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

## 📖 6.3.2 Forward Algorithm on Weather Problem Example

Forward Algorithm calculations over the probability of a sequence of observations:

| Time:     | Day 1 (t=1)           | Day 2 (t=2)                                                 | Day 3 (t=3)                                                      |
|-----------|-----------------------|-------------------------------------------------------------|------------------------------------------------------------------|
| Forward:  | Walk                  | Shop                                                        | Clean                                                            |
| Rainy     | 0.6 * 0.1 = **0.06**  | **0.06** * 0.7 * 0.4 + **0.24** * 0.4 * 0.4 = _**0.0552**_  | _**0.0552**_ * 0.7 * 0.5 + _**0.0486**_ * 0.4 * 0.5 = 0.02904    |
| Sunny     | 0.4 * 0.6 = **0.24**  | **0.06** * 0.3 * 0.3 + **0.24** * 0.6 * 0.3 = _**0.0486**_  | _**0.0552**_ * 0.3 * 0.1 + _**0.0486**_ * 0.6  * 0.1 = 0.004476  |

<img width="478" height="388" alt="image" src="https://github.com/user-attachments/assets/27203798-f8f4-4bbc-aa12-893deabd1b56" />

> ##### Image: Forward Algorithm State Machine

## 📖 6.3.3 Viterbi Algorithm on Weather Problem Example

| Time:     | Day 1 (t=1)           | Day 2 (t=2)                                                        | Day 3 (t=3)                                                            |
|-----------|-----------------------|--------------------------------------------------------------------|------------------------------------------------------------------------|
| Forward:  | Walk                  | Shop                                                               | Clean                                                                  |
| Rainy     | 0.6 * 0.1 = **0.06**  | MAX( **0.06** * 0.7 * 0.4 , **0.24** * 0.4 * 0.4 ) = _**0.0384**_  | MAX( _**0.0384**_ * 0.7 * 0.5 , _**0.0432**_ * 0.4 * 0.5 ) = 0.01344   |
| Sunny     | 0.4 * 0.6 = **0.24**  | MAX( **0.06** * 0.3 * 0.3 , **0.24** * 0.6 * 0.3 ) = _**0.0432**_  | MAX( _**0.0384**_ * 0.3 * 0.1 , _**0.0432**_ * 0.6  * 0.1 ) = 0.00259  |

<img width="612" height="463" alt="image" src="https://github.com/user-attachments/assets/af016906-d092-42e6-9dda-febc72fb69e3" />

> ##### Image: Viterbi Algorithm State Machine

🔴 A **Trellis Diagram** _is a graph with the nodes ordered into vertical slices (time) and each node at each time is connected to (at least) one node at an earlier time and (at least) one node at a later time_. The **Viterbi Path** _is the shortest path through this trellis diagram_. The trellis for the weather example is shown in image below:

<img width="901" height="372" alt="image" src="https://github.com/user-attachments/assets/fd9224f8-2801-4b93-a597-727f36a3ad0d" />

> ##### Image: Viterbi Algorithm Trellis Diagram

---

## 📖 6.4 Application: Part-of-Speech (POS) Tagging

**POS Tagging is the process of labeling each word in a text with its grammatical class**, **like noun or verb**.
It helps computers process text for searches, information extraction and correct pronunciation.

**How HMMs do it**:
* **Words are the observed events**;
* **POS tags are the hidden events**;
* **Transition Probability** $P(t2|t1)$: The chance of one tag following another (e.g., a noun following an adjective);
* **Emission Probability** $P(w|t)$: The chance of a specific tag emitting a specific word (e.g., the tag "Verb" emitting the word "race").

### 📑 6.4.1 Penn Treebank POS Tags

| Tag    | Description             | Example      |
|--------|-------------------------|--------------|
| **CC** | coordinated conjunction | and, but, or |
| **CD** | cardinal number | one, two, four |
| **DT** | determiner | a, the |
| **EX** | existential ,,there" | there |
| **FW** | foreign word | mea culpa |
| **IN** | preposition | of, in ,by |
| **JJ** | adjective | red |
| **JJR** | adj. comparative | smaller |
| **JJS** | adj.superlative | biggest |
| **MD** | modal | can,should |
| **NN** | noun singular | cat |
| **NNS** | noun plural | books |
| **NNP** | proper noun singular | John |
| **NNPS** | proper noun plural | Carolinas |
| **PDT** | predeterminer | all, both |
| **POS** | possessive ending | 's |
| **PRP** | personal pronoun | i,you,we |
| **PRP$** | possessive pronoun | your, one's |
| **RB** | adverb | quickly, soon |
| **RBR** | adverb comparative | faster |
| **RBS** | adverb superlative | fastest |
| **TO** | ,,to" | to |
| **RP** | Particle | off, up |
| **VB** | verb, base form | eat |
| **VBD** | verb, past tense | ate |
| **VBG** | verb, gerund | eating |
| **VBN** | verb, past participle | eaten |
| **VBP** | verb, non pers 3sg | eat |
| **VBZ** | verb, pers 3sg | eats |
| **WDT** | wh-determiner | which, that |
| **WP** | wh-pronoun | what, who |
| **WP$** | possessive wh | whose |
| **WRB** | wh-adverb | how, where |



### 📑 6.4.2 Example of a HMM used for POS Tagging

Assign POS-Tags for the words of the sentence "I want to race".
To decode a sentence, the system runs the Viterbi algorithm to find the sequence of POS-Tags with the highest final probability.

* M = (Q, V, A, B, q0), where: q0 = start (initial state);
* Q = {VB, TO, NN, PPSS, ... } the set of hidden states corresponding to the parts-of-speech;
* V = the set of English words;
* O = ([I, want, to, race]), the sequence of observations.

Transition Probability Matrix:

| A | VB | TO | NN | PPSS |
|-----|-----|-----|-----|-----|
| **start** | P(VB\|start)=0.019 | P(TO\|start)=0.043 | P(NN\|start)=0.041 | P(PPSS\|start)=0.067 |
| **VB** | P(VB\|VB)=0.0038 | P(TO\|VB)=0.035 | P(NN\|VB)=0.047 | P(PPSS\|VB)=0.007 |
| **TO** | P(VB\|TO)=0.83 | P(TO\|TO)=0 | P(NN\|TO)=0.00047 | P(PPSS\|TO)=0 |
| **NN** | P(VB\|NN)=0.004 | P(TO\|NN)=0.016 | P(NN\|NN)=0.087 | P(PPSS\|NN)=0.0045 |
| **PPSS** | P(VB\|PPSS)=0.23 | P(TO\|PPSS)=0.00079 | P(NN\|PPSS)=0.0012 | P(PPSS\|PPSS)=0.00014 |

Emission Probability Matrix>

| B | I | want | to | race |
|-----|-----|-----|-----|-----|
| **VB** | P(I\|VB)=0 | P(want\|VB)=0.0093 | P(to\|VB)=0 | P(race\|VB)=0.00012 |
| **TO / TQ** | P(I\|TQ)=0 | P(want\|TQ)=0 | P(to\|TO) 0.99 | P(race\|TO)=0 |
| **NN** | P(I\|NN)=0 | P(want\|NN)=0.000054 | P(to\|NN)=0 | P(race\|NN)=0.00057 |
| **PPSS** | P(I\|PPSS)=0.37 | P(want\|PPSS)=0 | P(to\|PPSS)=0 | P(race\|PPSS)=0 |

Viterbi's Algorithm:

| Viterbi | I | want | to | race |
|-----|-----|-----|-----|-----|
| **VB** | 0\*0.019=0 | 0.02479\*0.0093\*<br>\*0.23=0.000053 | 0 | 0.1836\*10-5 \*0.00012\*<br>\*0.83=1.8286656\*10-10 |
| **TO** | 0\*0.043=0 | 0 | 0.000053\*0.99\*<br>\*0.035=<br>=0.1836\*10-5 | 0 |
| **NN** | 0\*0.041=0 | 0.02479\*0.000054\*<br>\*0.0012=0.2\*10-8 | 0 | 0.1836\*10-5 \*0.00057\*<br>\*0.00047=4.918644\*10-13 |
| **PPSS** | 0.37\*0.067=<br>= 0.02479 | 0 | 0 | 0 |


