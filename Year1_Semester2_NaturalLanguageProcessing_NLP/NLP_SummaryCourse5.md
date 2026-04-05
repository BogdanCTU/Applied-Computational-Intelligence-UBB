
<!-- --------------------------------------------------------------- -->
<!-- ----------------- COURSE 5 SYNTACTIC PARSING ------------------ -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 5 - Syntactic Parsing**

## 📖 5.1 Parsing Techniques
* **Constituency Parsing**: Identifies groups of words, called constituents and arranges them in a hierarchical tree structure;
**Dependency Parsing**: Connects words directly to each other using directed links to show how they relate. 

---

## 📖 5.2 Phrase Structure and Constituents
Words in a sentence naturally group together into units called phrases or constituents. 
* **Noun Phrase** (_NP_): A group of words centered around a noun. It can include determiners (words like "a" or "the") and adjectives;
* **Prepositional Phrase** (_PP_): Starts with a preposition (like "on" or "in") and includes a Noun Phrase;
* **Verb Phrase** (_VP_): Centered around a verb. It contains all elements of the sentence that depend on the action;
* **Adjective Phrase** (_AP_): Centered around an adjective, such as "very sure". 

---

## 📖 5.3 Context-Free Grammars (_CFG_)
🔴 **Syntactic Parsing** is the task of assigning a grammatical structure to a sentence using formal rules. For English, we model this using a **Context-Free Grammar** (_CFG_), which is a mathematical system that describes how to build correct sentences.
A CFG has four parts:
* **Start symbol** (_S_): The root of the entire sentence;
* **Non-terminals** (_N_): Symbols representing phrases (like NP) or part-of-speech tags;
* **Terminals** (_$\Sigma$_): The actual written words in the language, like "house" or "read";
* **Production rules** (_R_): Rules that show how a symbol can be replaced by a sequence of other symbols or words. 

---

## 📖 5.4 Attachment Ambiguity
🔴 **Attachment Ambiguity** is the confusion about where a phrase belongs in a sentence. It usually happens when a sentence has multiple prepositional phrases. 

Example: "The boy saw the girl with the telescope." It is unclear if the girl is carrying a telescope, or if the boy is looking through a telescope to see the girl. 

---

## 📖 5.5 Parsing Strategies
Parsers search for the correct grammatical tree using two main strategies: 
* **Top-down search**: Starts at the root (S) and builds down to the words, guided by the grammar rules;
* **Bottom-up search**: Starts with the actual words and builds up to the root, ensuring the tree matches the input data;
* 🔴 Both strategies struggle with the **re-parsing problem** (building the same structure multiple times) and **local ambiguity** (sections of a sentence that are confusing on their own). 

---

## 📖 5.6 Dynamic Programming Parsing Methods
These methods solve the re-parsing problem by using tables to save phrases as soon as they are discovered. 
* **CKY Algorithm**: A bottom-up method driven by a table. It requires the grammar to be in **Chomsky Normal Form** (_CNF_), meaning every rule must break down into exactly two non-terminals or one word. It builds a matrix where each cell holds the phrases that cover a specific span of words;
* **Earley Algorithm**: A top-down search method that also uses tables to build predictions. 

---

## 📖 5.7 Statistical Parsing
**Probabilistic Context-Free Grammar** (_PCFG_) is a CFG where every production rule is assigned a probability. 
* These probabilities help solve ambiguity by allowing the computer to choose the most likely parse tree;
* The probability of a specific parse tree is calculated by multiplying the probabilities of all the rules used to build it;
* Rule probabilities are usually learned from a Treebank, which is a large database of sentences already parsed by humans. 

---

## 📖 5.8 Evaluating Parsers
🔴 **PARSEVAL** measures are standard formulas used to compare a computer's parse tree against a human-made "gold standard" reference tree. 
* **Labeled Recall**: The fraction of correct phrases in the human reference tree that the computer successfully found;
* **Labeled Precision**: The fraction of phrases proposed by the computer that are actually correct. 

---

## 📖 5.9 Applications of Syntactic Analysis

Understanding word relationships is a core step for many advanced language technologies.  It is used heavily in:
* **Machine Translation**: To ensure translated sentences follow correct grammar;
* **Question Answering**: To link question words to their proper answers;
* **Speech Recognition**: To figure out the grammatical structure of spoken words;
* **Sentiment Analysis**, Text Summarization, and Grammar Checking.
 
