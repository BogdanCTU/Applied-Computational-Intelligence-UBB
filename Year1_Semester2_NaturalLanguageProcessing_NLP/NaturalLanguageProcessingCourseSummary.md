<!-- --------------------------------------------------------------- -->
<!-- -------------------- COURSE 1 INTRODUCTION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 1 - Introduction to Natural Language Processing**

[//]: ---

## 📖 1.1 Introduction to Natural Language Processing (NLP)

* **Definition**: A subfield of **Artificial Intelligence** (_AI_) focused on the automated generation and understanding of spoken and written human languages;
* **Goal**: To achieve human-like language processing and understanding;
* **Origins**: Intersects **Linguistics** (formal structural models), **Computer Science** (internal data representation and efficient processing) and **Cognitive Psychology** (modeling language via human cognitive processes).

[//]: ---

## 📖 1.2 Levels of Natural Language Processing

* **Phonology**: Interpretation of speech sounds (phonetic and prosodic rules);
* **Morphology**: Studies the componential nature of words formed by **morphemes** (stems and affixes);
* **Lexical Level**: Interpretation of individual word meanings (e.g., **part-of-speech tagging**);
* **Syntactic Level**: Analyzes grammatical structures and dependency relationships between words in a sentence using grammars and parsers;
* **Semantic Level**: Determines the exact meaning of sentences by resolving word-level ambiguities (_selecting the correct sense of polysemous words_);
* **Discourse Level**: Focuses on the text as a whole, connecting component sentences (_e.g., resolving pronouns to the entities they refer to_);
* **Pragmatic Level**: Extracts extra context and meaning not explicitly encoded in the text, requiring world knowledge, intentions and goals.

[//]: ---

## 📖 1.3 Basic Tasks for Written Language Processing

* **Tokenization**: Dividing text into individual units (words, numbers, punctuation);
* **Sentence Segmentation**: Dividing text into sentences;
* **Lemmatization**: Identifying the base dictionary form of a word (**lemma**). _Example: "better" -> "good"_;
* **Stemming**: Chopping off affixes to reduce words to their root form, ignoring context. _Example: "connected", "connections" -> "connect"_;
    * **Inflection**: Adds suffixes without changing the part of speech (e.g., _flowers_);
    * **Derivation**: Adds affixes that change the word's class (e.g., _organization_);
* **Part-of-Speech (POS) Tagging**: Assigning grammatical categories (noun, verb, adjective) to words in context;
* **Chunking (Shallow Parsing)**: Identifying higher-level units or phrases (_e.g., noun groups_) without mapping their exact internal structure;
* **Dependency Parsing**: Mapping the grammatical dependencies between words to understand structure;
* **Syntactic Parsing**: Assigning a full hierarchical syntactic structure (parse tree) to a sentence based on grammar rules.

[//]: ---

## 📖 1.4 Meaning and Disambiguation

* **Natural Language Meaning**: Characterized by **Variability** (multiple ways to express one meaning) and **Ambiguity** (one expression having multiple meanings);
* **Word Sense Disambiguation (WSD)**: Determining the exact sense of an ambiguous word in context. _Example: "Plant" can mean a factory or a living organism_;
* **Textual Entailment**: Determining if one text is a logical consequence of another (Yes/No/Unknown);
* **Co-reference Resolution**: Grouping words ("mentions") that refer to the same real-world entity. Includes **Anaphora resolution** (linking pronouns to previous nouns);
* **Named Entity Recognition (NER)**: Classifying text items into predefined categories (_e.g., Person, Organization, Location, Date_).

[//]: ---

## 📖 1.5 Practical NLP Tasks

* **Speech Processing**: Speech recognition (speech-to-text), text-to-speech, speaker recognition;
* **Machine Translation**: Automated translation between human languages (an "AI-complete" problem);
* **Information Retrieval & Question Answering**: Finding relevant documents or exact answers to natural language queries;
* **Text Mining**: Extracting structured data from unstructured text (includes Categorization, Clustering, and Summarization);
* **Sentiment Analysis / Opinion Mining**: Analyzing attitudes and emotions. Can be applied at the Document, Sentence (subjective vs. objective) or Entity/Aspect level;
* **Other Tasks**: Authorship attribution, **Natural Language Generation** (_NLG_) and **Discourse Analysis**;

[//]: ---

## 📖 1.6 Approaches to NLP

## 📑 1.6.1 Symbolic Approaches
Perform deep linguistic analysis using explicit knowledge representation.
* **Methods**: Logic-based systems (first-order logic), Rule-based systems, Semantic Networks, Description Logics and Formal Concept Analysis (FCA).

## 📑 1.6.2 Statistical & Machine Learning Approaches
Use mathematical techniques and large text corpora to build probabilistic models.
* **Methods**: Hidden Markov Models (HMM) for POS tagging/speech, supervised/unsupervised machine learning.

## 📑 1.6.3 Deep Learning
Uses neural networks with many layers to extract features and classify data directly from text.
* **Methods**: CNNs, RNNs, Autoencoders and pre-trained Transformer models.

[//]: ---

## 📖 1.7 Knowledge Bases in NLP

* **Corpora**: Large, structured sets of texts (Monolingual, Multilingual, Aligned, Annotated, Parsed/Treebanks);
* **Electronic Dictionaries**: Definitions and pronunciations;
* **Thesauri**: Groupings of words by semantic similarity (_e.g., WordNet_);
* **Ontologies**: Formal representations of concepts and their relationships within a specific domain.

[//]: ---

## 📖 1.8 Language Models and LLMs

* **Language Models**: Built to predict word sequences and probabilities. Feature **Word Embeddings** (_Word2Vec, GloVe_), where words with similar meanings have similar vector representations;
* **Large Language Models (LLMs)**: Foundation models trained on immense datasets. Capable of generation, translation, summarization, and zero-shot reasoning. Rely heavily on **Transformer architecture** and **attention mechanisms** (_e.g., BERT, GPT_).

[//]: ---

## 📖 1.9 Challenges in NLP

* **Contextual Understanding & Ambiguity**: Struggle with implicit meanings and metaphors;
* **Common Sense Reasoning**: Lacking basic human intuition and background knowledge;
* **Bias and Fairness**: Inheriting and amplifying discriminatory biases present in training data;
* **Multilingual Challenges**: Scarcity of labeled data for non-dominant languages;
* **Ethical Use**: Mitigating fake news, hate speech and ensuring transparency;
* **Continual Learning**: Updating models with new data without forgetting old knowledge.


<!-- --------------------------------------------------------------- -->
<!-- ---------------- COURSE 2 TEXT CLASSIFICATION ----------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 2 - Text Classification**

| **Text Classification Task**       | **Applications**                                                                  |
|------------------------------------|---------------------------------------------------------------------------------- |
| **Topic Classification**           | Recommender systems, bio-informatics, document annotation                         |
| **Intent Detection**               | Spam detection, email classification, product analysis                            |
| **Sentiment Analysis**             | Market research, social media monitoring, customer feedback                       |
| **Language Detection**             | Document classification, speech recognition, email filtering, machine translation |
| **Textual Entailment**             | Natural language inference, document summarization, machine translation           |
| **Authorship Attribution**         | Literature and history, software engineering, cybersecurity                       |
| **Genre Classification**           | Literature                                                                        |
| **Speech Recognition**             | Virtual assistants (e.g., Siri, Alexa)                                            |
| **Word-level Classification**      | Part-of-speech tagging, word-sense disambiguation                                 |

## 📖 2.1 **Text Classification (Categorization)**

**Definition:** Text classification is the automated process of assigning natural language texts to one or more predefined groups (categories) based on their content. It uses a mathematical function called a classifier to match texts to the correct categories.

* **Types of Classification:**
    * **Single-label:** Exactly one category is assigned to each document. When there are only two categories, it is called binary classification;
    * **Multi-label:** Any number of categories can be assigned to a single document;
* **Common Applications:** Spam detection (intent detection), social media monitoring (sentiment analysis), sorting emails and virtual assistants (speech recognition).

[//]: ---

## 📖 2.2 **Approaches to Text Classification**

* **Rule-based:** Uses manual, handcrafted linguistic rules and lists of words to classify text. This method takes a lot of time to build and is hard to expand;
* **Machine Learning (ML):** Uses algorithms to learn patterns from large sets of annotated (labeled) data. This requires a step called feature extraction, which turns text into measurable data;
* **Deep Learning:** Uses complex computational models with multiple processing layers to learn data representations automatically. It easily integrates pre-trained word embeddings (numerical representations of words);

[//]: ---

## 📖 2.3 **The Machine Learning Pipeline**

* **Steps:** The text goes through Feature Extraction, followed by Dimensionality Reduction, then Classification (using a learning model), and finally Prediction and Evaluation;
* **Popular Algorithms:** **Logistic Regression** (_LR_), **Support Vector Machines** (_SVM_), **K-Nearest Neighbors** (_KNN_), **Naïve Bayes** (_NB_), **Decision Trees** (_DT_), **Random Forest** (_RF_) and **Neural Networks** (_NN_).
 
<img width="665" height="165" alt="image" src="https://github.com/user-attachments/assets/75e6a981-93be-4aab-b4bd-1301d646a67b" />

> ### Image: Overview of text classification pipeline

[//]: ---

## 📖 2.4 **Dimensionality Reduction**

**Definition:** A technique to simplify datasets by reducing the number of features while keeping the most important information.

* **Principal Component Analysis (PCA)**: Transforms data into new, uncorrelated variables that capture the maximum amount of original information;
* **t-distributed Stochastic Neighbor Embedding (t-SNE)**: **unsupervised non-linear technique**, is a visual tool that groups similar high-dimensional data points together in a simple 2D or 3D visual space;
* **LSA (Latent Semantic Analysis):** The method applies **Singular Value Decomposition** (_SVD_). Reduces features while preserving the semantic (meaning) similarity between texts, changing sparse high-dimensional data into dense low-dimensional data. The output vector space is called **Latent Semantic Indexing** (_LSI_).

[//]: ---

## 📖 2.5 **Text Pre-Processing**

**Definition:** Cleaning and standardizing text before it is analyzed.

* **Key Steps:**
    * **Tokenization:** Breaking text into smaller units, like individual words;
    * **Stop words removal:** Removing very common words (_e.g., "the", "is"_) that carry little useful information;
    * **Stemming & Lemmatization:** Reducing words to their base or dictionary root form (_e.g., "studying" becomes "study"_);
    * **POS-tagging:** Labeling the part of speech for each word, such as noun or verb;
    * **NER (Named Entity Recognition):** Identifying specific names, places or organizations..

<img width="471" height="204" alt="image" src="https://github.com/user-attachments/assets/48d8d049-0423-4c24-af0a-a4bd87c2c085" />

> ### Image: Dependency Tree of phrase "_Maria si Tudor studiaza la UBB, Cluj_."

[//]: ---

## 📖 2.6 **Text Representation (Syntactic Features)**

**Definition:** Methods for converting text into numbers so a computer can process it.

* **One-Hot Encoding:** The simplest method where a vocabulary is built, and each word gets a unique vector filled with 0s except for a single 1. It cannot measure similarity between words;
* **Bag of Words (BOW):** Counts the unique words in a text but completely loses the order in which they appeared;
* **N-grams:** Groups sequences of words or characters together to keep some local order. _Example: A word-level bigram for "One Two" groups them together_;
* **Term Frequency - Inverse Document Frequency (TF-IDF):** Measures how relevant a word is to a specific document within a larger collection.
    * *TF* counts how often the word appears in the document;
    * *IDF* checks how rare the word is across all documents;
    * *Drawback:* These methods create sparse data with very high dimensionality.

[//]: ---

## 📖 2.7 **Semantic Representations and Language Models**

**Vector Space Models (VSM):** Represents words or documents as vectors in a space where items with similar meanings are located close together. These are called embeddings.

* **Word2Vec:** A simple neural network that learns word meanings based on context:
    * *CBOW:* Predicts a missing target word based on the surrounding context. Faster and better for frequent words;
      <img width="792" height="1025" alt="image" src="https://github.com/user-attachments/assets/3c5bc099-36a0-43ae-86be-b7129665c78b" />
    * *Skip-gram:* Predicts the surrounding context based on a single target word. Better for rare words;
      <img width="813" height="825" alt="image" src="https://github.com/user-attachments/assets/214b9f0d-fcd4-4fe0-9428-f0b768d4070b" />

<img width="601" height="341" alt="image" src="https://github.com/user-attachments/assets/f22f6aec-2535-4999-b789-6b6e2366b2d7" />

> ### Image: CBOW and Skip-gram comparasion

* **FastText:** Improves on Word2Vec by generating numerical representations for parts of words (character n-grams), allowing it to guess embeddings for words it has never seen before;
* **GloVe:** Learns word representations by looking at global word co-occurrence statistics across a whole corpus;
  <img width="827" height="440" alt="image" src="https://github.com/user-attachments/assets/4bc56438-b82b-4e35-9a9e-155a34dc30fd" />
* **Doc2Vec:** Extends Word2Vec to create a single vector representation for an entire paragraph or document;

<img width="625" height="379" alt="image" src="https://github.com/user-attachments/assets/316a5656-66c6-46bf-954b-0bf928c186fe" />

* **Top2Vec:** Automatically finds dense areas of similar documents to detect topics without needing to know the number of topics in advance;
* **CoRoLa:** A massive reference corpus for the Romanian language used to generate specific semantic representations (embeddings) for Romanian words.

<img width="1250" height="900" alt="image" src="https://github.com/user-attachments/assets/707a6094-c051-4a46-b791-61444d501635" />

> ### Image: CoRoLa

<img width="534" height="216" alt="image" src="https://github.com/user-attachments/assets/b32e3a2a-91bf-4560-82ab-8c5b8a7c3f35" />

> ### Image: CoRoLa Nearest Neighbor

<img width="592" height="274" alt="image" src="https://github.com/user-attachments/assets/5420ffc0-d3c0-4bbc-a211-23eb23b95d43" />

> ### Image: CoRoLa Analogies

[//]: ---

## 📖 2.8 **Transfer Learning & Contextualized Embeddings**
* **Transfer Learning:** Taking a large model trained on massive amounts of general data (pre-training) and tweaking it for a specific task using labeled data (fine-tuning);
* **Contextualized Embeddings:** Dynamic representations where the exact same word receives a different numerical vector depending on the surrounding context in a sentence.

[//]: ---

## 📖 2.9 **Bidirectional Encoder Representations from Transformers (BERT)**

**Definition:** A powerful language model that reads sequences of words in both directions at the same time to deeply understand context.

<img width="1045" height="613" alt="image" src="https://github.com/user-attachments/assets/28e0d2d6-66d6-4c82-9c68-02cb0c7357f7" />

> ### Image: BERT Model

* **Training Tasks:**
    * **Masked Language Modeling (MLM):** Randomly hides 15% of the input words and trains the model to predict them using both the left and right context;
    * **Next Sentence Prediction (NSP):** Trains the model to predict the likelihood that one sentence logically follows another;
* **Model Variations:**
    * **RoBERTa:** Improves BERT by removing the NSP task and using much more data;
    * **DistilBERT:** A smaller, compressed version of BERT that trains faster;
    * **Romanian BERTs:** Specific Transformer models exist for Romanian (e.g., Romanian DistilBERT) and are evaluated on tasks like Emotion Detection and Named Entity Recognition.
 
<img width="1275" height="744" alt="image" src="https://github.com/user-attachments/assets/782e5d22-13d6-4e16-81b9-b3273d3cc0d9" />

> ### Image: Models comparasion


<!-- --------------------------------------------------------------- -->
<!-- ----------------- COURSE 3 SYNTACTIC PARSING ------------------ -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 3 - Syntactic Parsing**

## 📖 3.1 Parsing Techniques
* **Constituency Parsing**: Identifies groups of words, called constituents and arranges them in a hierarchical tree structure;
* **Dependency Parsing**: Connects words directly to each other using directed links to show how they relate. 

<img width="826" height="328" alt="image" src="https://github.com/user-attachments/assets/d2e6707c-3498-469b-91a5-85186ab92b82" />

> ##### Image: Dependency Parsing using Relate-Teprolin

<img width="675" height="564" alt="image" src="https://github.com/user-attachments/assets/e2b1dd02-2ec7-4a93-b1d3-a140e4664586" />

> ##### Image: Constituency and Dependency Parsing

---

## 📖 3.2 Phrase Structure and Constituents
Words in a sentence naturally group together into units called phrases or constituents. 
* **Noun Phrase** (_NP_): A group of words centered around a noun. It can include determiners (words like "a" or "the") and adjectives;
* **Prepositional Phrase** (_PP_): Starts with a preposition (like "on" or "in") and includes a Noun Phrase;
* **Verb Phrase** (_VP_): Centered around a verb. It contains all elements of the sentence that depend on the action;
* **Adjective Phrase** (_AP_): Centered around an adjective, such as "very sure". 

---

## 📖 3.3 Context-Free Grammars (_CFG_)
🔴 **Syntactic Parsing** is the task of assigning a grammatical structure to a sentence using formal rules. For English, we model this using a **Context-Free Grammar** (_CFG_), which is a mathematical system that describes how to build correct sentences.

A CFG has four parts:
* **Start symbol** (_S_): The root of the entire sentence;
* **Non-terminals** (_N_): Symbols representing phrases (like NP) or part-of-speech tags;
* **Terminals** (_$\Sigma$_): The actual written words in the language, like "house" or "read";
* **Production rules** (_R_): Rules that show how a symbol can be replaced by a sequence of other symbols or words. 

---

## 📖 3.4 Attachment Ambiguity
🔴 **Attachment Ambiguity** is the confusion about where a phrase belongs in a sentence. It usually happens when a sentence has multiple prepositional phrases. 

Example: "The boy saw the girl with the telescope." It is unclear if the girl is carrying a telescope, or if the boy is looking through a telescope to see the girl. 

---

## 📖 3.5 Parsing Strategies
Parsers search for the correct grammatical tree using two main strategies: 
* **Top-down search**: Starts at the root (S) and builds down to the words, guided by the grammar rules;
* **Bottom-up search**: Starts with the actual words and builds up to the root, ensuring the tree matches the input data;
* 🔴 Both strategies struggle with the **re-parsing problem** (building the same structure multiple times) and **local ambiguity** (sections of a sentence that are confusing on their own). 

---

## 📖 3.6 Dynamic Programming Parsing Methods
These methods solve the re-parsing problem by using tables to save phrases as soon as they are discovered. 
* 🔴 **Cocke-Kasami-Younger Algorithm** (_CKY_): A bottom-up method driven by a table. It requires the grammar to be in **Chomsky Normal Form** (_CNF_), meaning every rule must break down into exactly two non-terminals or one word. It builds a matrix where each cell holds the phrases that cover a specific span of words;

<img width="571" height="413" alt="image" src="https://github.com/user-attachments/assets/57ea3b0c-e7c9-4c99-8b42-91618ef06fc9" />

> ##### Image: Cocke-Kasami-Younger Algorithm
 
* **Earley Algorithm**: A top-down search method that also uses tables to build predictions. 

---

## 📖 3.7 Statistical Parsing
🔴 **Probabilistic Context-Free Grammar** (_PCFG_) is a Context-Free Grammar (CFG) where every production rule is assigned a **probability**.
* These probabilities help solve ambiguity by allowing the computer to choose the most likely parse tree;
* The probability of a specific parse tree is calculated by multiplying the probabilities of all the rules used to build it;
* Rule probabilities are usually learned from a Treebank, which is a large database of sentences already parsed by humans. 

<img width="843" height="510" alt="image" src="https://github.com/user-attachments/assets/29124110-5ca6-46b0-8d24-7bc6c634dd91" />

> ##### Image: Probabilities sample for finding the right parse tree

---

## 📖 3.8 Evaluating Parsers
🔴 **PARSEVAL** measures are standard formulas used to compare a computer's parse tree against a human-made "gold standard" reference tree;
* **Labeled Recall**: The fraction of correct phrases in the human reference tree that the computer successfully found;
* **Labeled Precision**: The fraction of phrases proposed by the computer that are actually correct.

---

## 📖 3.9 Applications of Syntactic Analysis

Understanding word relationships is a core step for many advanced language technologies.  It is used heavily in:
* **Machine Translation**: To ensure translated sentences follow correct grammar;
* **Question Answering**: To link question words to their proper answers;
* **Speech Recognition**: To figure out the grammatical structure of spoken words;
* **Sentiment Analysis**, Text Summarization, and Grammar Checking.


<!-- --------------------------------------------------------------- -->
<!-- ------------------------ COURSE 4 HMM ------------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 4 - Hidden Markov Model (HMM)**

## 📖 4.1 Introduction to Hidden Markov Models (_HMM_)

🔴 **An HMM is a statistical machine learning tool used for sequence classification and text processing**.
It looks at a sequence of items and finds the best sequence of labels for them.
HMMs use probability to link two types of events:
* **Observed events**: Things we can see in our data, such as words in a sentence;
* **Hidden events**: Things we cannot see but act as causes, such as grammatical part-of-speech (POS) tags.
HMMs are widely used in speech recognition (observed: sounds, hidden: words), part-of-speech tagging (observed: words, hidden: tags), and machine translation.

### 📑 4.1.1 Formal Definition

🔴 **An HMM is a finite state automaton** (**a machine that moves between different states**) **that uses random probabilities to transition between states and emit symbols**.
It models a generative process. This means it creates a sequence by starting in an initial state, moving to a new state, and outputting an observed symbol.
The mathematical model is defined as $M=(Q,V,A,B,q_{0})$:
* $Q$: A set of hidden states;
* $V$: An alphabet of possible observations (emissions);
* $A$: The transition probability matrix. This is the chance of moving from one hidden state to another;
* $B$: The emission probability matrix. This is the chance of a hidden state generating a specific observation;
* $q_{0}$: The starting state, which does not emit any observation.

### 📑 4.1.2 Key Assumptions

To make the math simple, HMMs rely on two strict rules:
* **Markov Assumption**: The probability of the next state depends only on the current state, ignoring all older history. The formula is $P(q_{i}|q_{1},...,q_{i-1})=P(q_{i}|q_{i-1})$.
* **Output Independence**: The probability of an observed event depends only on the hidden state that made it, ignoring all other states or observations.
  The formula is $P(o_{i}|q_{1}...q_{i}...q_{T},o_{1}...o_{i}...o_{T})=P(o_{i}|q_{i})$. Note, "o1, o2, o3" are the output sequence (the sequence of observations)

<img width="813" height="267" alt="image" src="https://github.com/user-attachments/assets/e0c06f90-9151-4dd9-b0c8-0b357812b327" />

> ##### Image: Temporal evolution of an HMM

---

## 📖 4.2 The Three Canonical Problems of HMMs

When working with HMMs, there are three main mathematical tasks:
* **Problem 1 - Evaluation**: We want to know how well a specific HMM matches a given sequence of observations. This uses the Forward algorithm;
* **Problem 2 - Decoding**: We have an observation sequence, and we want to uncover the hidden states that most likely created it. This uses the Viterbi algorithm;
* **Problem 3 - Learning**: We have data, and we want to train the HMM by finding the best transition and emission probabilities. This uses the Baum-Welch algorithm.

---

## 📖 4.3 Core Algorithms

Both the Forward and Viterbi algorithms use dynamic programming. They process events in a sequence step-by-step.
* **Forward Algorithm**: Calculates the overall probability that a sequence of observations could happen at all. It does this by adding up the probabilities of every possible path through the hidden states;
* **Viterbi Algorithm**: Finds the single best path of hidden states. Instead of adding probabilities, it looks for the maximum probability at each step and uses a "backpointer" to remember the winning path;

## 📖 4.3.1 Weather Problem Example
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

## 📖 4.3.2 Forward Algorithm on Weather Problem Example

Forward Algorithm calculations over the probability of a sequence of observations:

| Time:     | Day 1 (t=1)           | Day 2 (t=2)                                                 | Day 3 (t=3)                                                      |
|-----------|-----------------------|-------------------------------------------------------------|------------------------------------------------------------------|
| Forward:  | Walk                  | Shop                                                        | Clean                                                            |
| Rainy     | 0.6 * 0.1 = **0.06**  | **0.06** * 0.7 * 0.4 + **0.24** * 0.4 * 0.4 = _**0.0552**_  | _**0.0552**_ * 0.7 * 0.5 + _**0.0486**_ * 0.4 * 0.5 = 0.02904    |
| Sunny     | 0.4 * 0.6 = **0.24**  | **0.06** * 0.3 * 0.3 + **0.24** * 0.6 * 0.3 = _**0.0486**_  | _**0.0552**_ * 0.3 * 0.1 + _**0.0486**_ * 0.6  * 0.1 = 0.004476  |

<img width="478" height="388" alt="image" src="https://github.com/user-attachments/assets/27203798-f8f4-4bbc-aa12-893deabd1b56" />

> ##### Image: Forward Algorithm State Machine

## 📖 4.3.3 Viterbi Algorithm on Weather Problem Example

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

## 📖 4.4 Application: Part-of-Speech (POS) Tagging

**POS Tagging is the process of labeling each word in a text with its grammatical class**, **like noun or verb**.
It helps computers process text for searches, information extraction and correct pronunciation.

**How HMMs do it**:
* **Words are the observed events**;
* **POS tags are the hidden events**;
* **Transition Probability** $P(t2|t1)$: The chance of one tag following another (e.g., a noun following an adjective);
* **Emission Probability** $P(w|t)$: The chance of a specific tag emitting a specific word (e.g., the tag "Verb" emitting the word "race").

### 📑 4.4.1 Penn Treebank POS Tags

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



### 📑 4.4.2 Example of a HMM used for POS Tagging

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


<!-- --------------------------------------------------------------- -->
<!-- ------------------- COURSE 5 SUMMARIZATION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 5 - Summarization**

## 📖 5.1 Definition of Summarization

🔴 The **Document Summarization** is the process of taking an information source, extracting its content and presenting the most important parts in a short form.
The goal is to meet the specific needs of a user or application. **A summary is a short version of a text** (usually half the size or less) **that keeps the main ideas**.
An **Automatic Summarization** happens when a computer program creates the shortened text. Good automatic summaries must preserve key information and remain short and logical.

---

## 📖 5.2 Coherence and Cohesion
To write a good summary, the text must make sense. This relies on two concepts:
* **Coherence**: This is what makes a text logically meaningful overall. It is an abstract quality that focuses on how ideas are organized. Because it deals with ideas, coherence is qualitative and hard to measure;
* **Cohesion**: This is the actual grammatical and vocabulary glue that holds words and sentences together. It is a visible, measurable property.
    * _Lexical cohesion_ links words by meaning, such as repeating a word or using a synonym;
    * _Grammatical cohesion_ links words using grammar, such as using pronouns (like "she") or conjunctions (like "because").
* **The Rule**: A coherent text is always cohesive, but a cohesive text might not be coherent. Think of coherence as a finished building, and cohesion as the bricks.

> ### 📚 Grammar Concepts

### 5.2.1 Grammatical Cohesion

| Concept        | Definition                                                                 | Example                                                                 |
|----------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| **Anaphora**       | Referring back to something previously mentioned.                           | "Jane was brilliant. She got the best score." ("She" → "Jane")          |
| **Cataphora**      | Referring forward to something that will be mentioned.                      | "Here he comes our hero. Please, welcome John." ("he" → "John")         |
| **Ellipsis**       | Omitting words that are understood from context.                            | "A: Where are you going? B: To dance." ("I am going" omitted)            |
| **Substitution**   | Replacing a word/phrase with another to avoid repetition.                   | "I would like the pink one." ("one" → "T-shirt")                         |
| **Conjunctions**   | Linking words that connect ideas or sentences.                              | "We agree on the principle but disagree on the method."                 |

### 5.2.2 Lexical Cohesion

| Concept     | Definition                                                                 | Example                                                                 |
|-------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| **Repetition**  | Reusing the same word multiple times.                                      | "Birds are beautiful. Everybody likes birds."                           |
| **Synonymy**    | Using words with similar or identical meanings.                            | "snake" → "serpent"                                                     |
| **Hyponymy**    | Using a general category to refer to a specific item.                      | "cat" → "animal"                                                        |
| **Meronymy**    | Using a part-to-whole relationship.                                        | "tire" → part of "car"                                                  |
| **Antonymy**    | Using words with opposite meanings.                                        | "old" ↔ "new"                                                           |

### 📑 5.2.3 Tool for the Automatic Analysis of Cohesion (TAACO)

🔴 **Tool for the Automatic Analysis of Cohesion** (_TAACO_) is a free software program used to measure how well a text connects and flows together, which is known as cohesion. It is easy to use, works on most operating systems like Windows, Mac and Linux, and can process many text files at once. The tool uses over 150 different measurements, called indices, to evaluate a text.

The Three Levels of CohesionTAACO focuses on three main ways a text sticks together:
* **Local Cohesion**: This looks at connections at the sentence level, meaning how well smaller chunks of text link to one another;
* **Global Cohesion**: This looks at connections between larger chunks of text, which are usually paragraphs;
* **Overall text Cohesion**: This looks at the entire text as a whole to see how often cohesive features appear, such as how much the vocabulary varies across the document.

Here are six specific ways TAACO measures cohesion:
* **Sentence overlap**: This measures local cohesion by checking if neighboring sentences share the same root words, which are called lemmas;
* **Paragraph overlap**: This measures global cohesion by checking if neighboring paragraphs share the same root words;
* **Semantic overlap**: This measures both local and global cohesion. It uses a dictionary database called WordNet to check if words or groups of similar words (synsets) are shared between sentences and paragraphs;
* **Givenness**: This measures overall text cohesion by counting how many pointing words are used. These include pronouns (like "he" or "it"), definite articles (like "the"), and demonstratives (like "this" or "that");
* **Type-token ratio**: This measures overall text cohesion by checking how much words are repeated. It does this by dividing the total number of words in the text (tokens) by the number of unique, individual words (types);
* **Connectives**: This measures local cohesion by counting linking words. It tracks different types of links, such as positive versus negative words, or words that show time (temporal), add information (additive), or show cause and effect (causative).

---

## 📖 5.3 Types of Summaries
Summaries come in different forms:
* **Extract vs. Abstract**: An extract copies exact sentences from the text, while an abstract rewrites the content in new words;
* **Single vs. Multi-document**: A summary can be made from just one text or by combining many texts;
* **Indicative vs. Informative**: Indicative summaries act as a quick alert to tell you what a text is about. Informative summaries act as a substitute for the full text.

---

## 📖 5.4 The Three Stages of Summarization
Every summarizer follows three steps:
* **Analysis**: The system reads and understands the source text to build a mental map of it;
* **Transformation**: The system selects the most important content from that map;
* **Synthesis**: The system generates the final shortened text.

---

## 📖 5.5 Extractive vs. Abstractive Summarization
Definitions:
* **Extractive Summarization**: This method selects existing, important sentences from the original document and glues them together. It uses statistics and word patterns to find the best sentences.
    * _Outcome_: It has high factual accuracy but can read like a choppy list of sentences;

<img width="714" height="280" alt="image" src="https://github.com/user-attachments/assets/6eeba4aa-2503-4cd6-9a8b-ef013bb6334e" />

> ##### Image: Architecture for extraction

* **Abstractive Summarization**: This method understands the original text and retells it in fewer, new words. It uses complex Natural Language Processing (NLP)—how computers interpret human language—to write fluently.
    * _Outcome_: It creates a very natural summary using Generative AI, but it might accidentally change the original facts.

<img width="717" height="277" alt="image" src="https://github.com/user-attachments/assets/7aafb078-af3a-4f65-b0c2-246a4312962e" />

> ##### Image: Architecture for abstraction

| Feature                              | Extractive Summarization        | Abstractive Summarization            |
|--------------------------------------|--------------------------------|-------------------------------------|
| Approach                             | Extracts key sentences         | Generates new summaries             |
| Focus                                | Surface-level features         | Context and meaning                 |
| Use of AI                            | Limited                        | Generative AI (LLMs)                |
| Generate creative and engaging summaries | No                         | Yes                                 |
| Output Style                         | Choppy, sentence-like          | More fluent and coherent            |
| Preserve original content            | Yes                            | No                                  |
| Information Preservation             | High factual accuracy          | May introduce paraphrases           |

---

## 📖 5.6 How Computers Score Sentences (Extractive Features)
In extractive summarization, a computer grades sentences to decide which ones to keep. Sentences score higher if they:

1) **Content word (Keyword) feature**: Sentences that contain frequent nouns, known as keywords, have a higher chance of being included in the summary;
2) **Title word feature**: Sentences that share words with the document's title indicate the main theme and are more likely to be selected;
3) **Sentence location feature**: The first and last sentences of the first and last paragraphs are usually considered the most important;
4) **Sentence Length feature**: Sentences are penalized if they are too short or too long compared to the longest sentence in the document;
5) **Proper Noun feature**: Sentences containing proper nouns, such as names of specific people or places, have a greater chance of being included;
6) **Upper-case word feature**: Sentences that contain acronyms or proper names written in capital letters are more likely to be selected;
7) **Cue-Phrase Feature**: Sentences containing transition words, such as "for example," "first," or "in conclusion," are highly likely to be included;
8) **Biased Word Feature**: Sentences are marked as important if they contain words from a predefined list of topic-specific vocabulary;
9) **Font based feature**: Sentences with words styled in bold, italics, underlined, or upper-case fonts are usually considered more important;
10) **Pronouns**: Sentences containing pronouns, such as "she" or "it," are excluded unless the pronoun can be replaced with the specific noun it refers to;
11) **Sentence-to-Sentence Cohesion**: Cohesion is how well parts of a text connect to each other. A sentence is scored by calculating how similar it is to every other sentence in the text, and sentences with high overall similarity are kept;
12) **Sentence-to-Centroid Cohesion**: A centroid is the mathematical average of all sentences, representing the core idea. Sentences are compared to this central average, and those that are highly similar are selected because they represent the basic ideas of the document.

---

## 📖 5.7 Mathematical and AI Methods
Computers use different algorithms to pick the best sentences:
1) **Machine Learning**: The program looks at human-made summaries to learn the rules of extraction. It treats summarization as a simple choice: "Is this a summary sentence, Yes or No?";

<img width="732" height="392" alt="image" src="https://github.com/user-attachments/assets/6f159d23-feeb-496b-8783-e06aa53d3116" />

> ##### Image: Classifier learning how to summarize

3) **Graph-Based Ranking** (**TextRank**): This treats sentences as points on a map (a graph).
    * Sentences "vote" for each other based on how similar they are;
    * Similarity is calculated by counting how many words the two sentences share;
    * Sentences with the most votes win and go into the summary;
    * The Formula: The ranking score uses a damping factor ($d$) and edge weights ($w$) for similarity:
    $$WS(V_{i})=(1-d)+d^{*}\sum_{V_{j}\in In(V_{i})}\frac{w_{ji}}{\sum_{V_{k}\in Out(V_{j})}w_{jk}}WS(V_{j})$$
4) **Summarization by Clustering**: Clustering means grouping similar sentences together.
    * By picking just one sentence from each group (cluster), the summary avoids repeating the same information;
    * **The Formula**: Computers group these sentences by measuring cosine similarity, as following:
    $$\mathrm{sim}(S_i,S_j)=\cos(V_i,V_j)=\frac{\sum_{k=1}^{m}f(i,t_k)\,f(j,t_k)}{\sqrt{\left(\sum_{k=1}^{m}f(i,t_k)^2\right)\left(\sum_{k=1}^{m}f(j,t_k)^2\right)}}$$
5) **BERTSum** (**Neural Networks**): BERTSum is an advanced AI model that reads an entire document. It transforms words into complex mathematical vectors (embeddings) and uses a classifier to predict exactly which sentences should make the final cut.

---

## 📖 5.8 Evaluating a Summary
We need to test if a summary is actually good.
* **Intrinsic Evaluation**: Humans grade the summary by reading it. They check for good spelling, grammar, and informativeness (how much original text survived);
* **Extrinsic Evaluation**: Testers see if the summary helps a person accomplish a real-world task, like answering a reading comprehension test;
* **ROUGE**: This is an automated software tool. It mathematically compares a computer's summary to a perfect human summary by counting how many words and phrases match.


<!-- --------------------------------------------------------------- -->
<!-- --------------------- COURSE 6 CLUSTERING --------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 6 - Clustering**

## 📖 6.1 Definition of Clustering

🔴 **Clustering is the task of dividing data points into groups**, which are called **clusters**:
* **Data points in the same cluster are highly similar to each other**;
* **Data points in different clusters are highly different from each other**;
* **It is an unsupervised learning method**. This means the algorithm finds patterns on its own without using pre-labeled data;
* The input is usually a vector, which is just a list of numbers representing a single data point.

---

## 📖 6.2 Types of Clustering
* **Hard Clustering**: A data point completely belongs to one specific cluster, or it does not.
Example: A store places a customer exactly into group A;
* **Soft Clustering**: A data point is given a probability or chance, of belonging to different clusters.
Example: A customer has a 70% chance of being in group A and a 30% chance of being in group B.

---

## 📖 6.3 Distance Metrics
🔴 **Distance metrics are math formulas used to measure how similar two objects are**.
We treat the objects as vectors, $g_{1}$ and $g_{2}$.
* **Euclidean distance**: The straight-line distance between two points.
Formula: $d(g_{1},g_{2})=\sqrt{\sum_{i=1}^{n}(x_{i}-y_{i})^{2}}$.
* **Manhattan distance**: The distance measured along axes at right angles, like walking city blocks.
Formula: $d(g_{1},g_{2})=\sum_{i=1}^{n}|(x_{i}-y_{i})|$.
* **Minkowski distance**: A flexible formula that generalizes the two above.
Formula: $d(g_{1},g_{2})=\sqrt[m]{\sum_{i=1}^{n}(x_{i}-y_{i})^{m}}$.

---

## 📖 6.4 Clustering Models

### 📑 6.4.1 Hierarchical Clustering (Connectivity Model)

🔴 **Connectivity models group points based on the idea that closer points in space are more similar**.

* **Bottom-Up Approach**: Starts by treating every single data point as its own separate cluster. It repeatedly merges the closest pair of clusters together. It stops when all points are combined into one single giant cluster;
* **Dendrogram**: A tree-like diagram that shows the history of how clusters were merged.  The root is the final giant cluster, and the leaves are the starting single points.

Similarity Measures:
* **Single-link**: Measures distance by looking only at the two closest (most similar) points between two clusters;
* **Complete-link**: Measures distance by looking at the two farthest (most dissimilar) points between two clusters.

### 📑 6.4.2 K-Means Clustering (Centroid Model)

🔴 **Centroid models group points based on how close they are to a central point**, **known as the centroid**.

Algorithm Steps:
1) Choose K, which is the exact number of clusters you want to find;
2) Randomly assign points to K clusters and calculate the center (centroid) for each group;
3) Measure the distance from each point to every center. Move the point to the cluster with the closest center;
4) Recalculate the centers based on the new groups;
5) Repeat steps 3 and 4 until the centers stop moving.

| Feature           | Hierarchical Clustering                                   | K-Means Clustering                          |
|-------------------|-----------------------------------------------------------|---------------------------------------------|
| Speed             | Slow, time complexity is O(n³).                           | Fast, time complexity is O(n).              |
| Number of Clusters| Decided at the end by cutting the dendrogram tree.        | Must be known and set before starting.      |
| Consistency       | Always produces the exact same results.                   | Results can change because starting points are random. |
| Best Used For     | Discovering hidden tree-like structures.                  | Data where clusters are round (spherical).  |

---

## 📖 6.5 Evaluation Metrics
Metrics are used to score how good the resulting clusters are.

### 📑 6.5.1 Internal Metrics
Used when you do not know the true groups. They check for compactness (points are packed tightly) and separation (clusters are far apart);
* **Silhouette Coefficient**: Measures if a point is close to its own cluster but far from others. Scores range from -1 to 1, and closer to 1 is better;
* **Dunn Index**: The ratio of the shortest distance between clusters to the largest cluster size. Higher scores mean tighter, better-separated clusters;
* **Inertia**: The sum of squared distances between points and their centers. Lower scores mean tighter clusters;
* **Davies-Bouldin Index** (_DBI_): Calculates the ratio of distances inside a cluster compared to distances between clusters. A lower score is better;
* **Calinski-Harabasz Index**: Measures how spread apart the clusters are compared to how spread apart the points inside a cluster are. A higher score is better.

### 📑 6.5.2 External Metrics
Used when you already know the true, correct groups (ground truth labels) to compare against.
* **Adjusted Rand Index** (_ARI_): Looks at pairs of points to see if the algorithm grouped them correctly. It adjusts for random guessing. A score of 1.0 is perfect, while 0.0 is random;
* **Rand Index** (_RI_): Measures the percentage of correctly grouped pairs, but does not adjust for random guessing;
* **Jaccard Index**: Measures shared correct pairs divided by the total number of unique pairs;
* **Normalized Mutual Information** (_NMI_): Measures how much correct information is shared between the true groups and the predicted groups. Scores range from 0 to 1.


<!-- --------------------------------------------------------------- -->
<!-- ----------------- COURSE 7 SENTIMENT ANALYSIS ----------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 7 - Sentiment and Emotion Analysis**

## 📖 7.1 Sentiment Analysis - Opinion Mining
🔴 **Sentiment analysis is a field of study that looks at people's opinions, feelings, attitudes and emotions toward entities like products, services or individuals**.
The main goal is to **classify text based on its polarity**, which means deciding if the feeling expressed is **positive, negative or neutral**.

---

## 📖 7.2 Levels of Sentiment Analysis
* **Document Level**: This level decides if an entire text document expresses an overall positive or negative feeling;
* **Sentence Level**: This level separates objective sentences (which state facts) from subjective sentences (which state personal views);
* **Entity and Aspect Level**: This is a highly detailed approach that finds feelings about specific parts of a target object.
For example, in a phone review, it separates opinions about the "battery life" aspect from the "call quality" aspect.

---

## 📖 7.3 The Formal Definition of an Opinion
An opinion is formally defined by five core parts (a quintuple):
* **Entity** ($e_j$): The main object being discussed;
* **Aspect** ($a_{jk}$): A specific feature of that main object;
* **Sentiment** ($S0_{ijkl}$): The actual feeling or rating given;
* **Holder** ($h_i$): The person or organization sharing the opinion;
* **Time** ($t_l$): When the opinion was expressed.

---

## 📖 7.4 Tasks of Sentiment Analysis
To fully process opinions in text, a system must complete six steps:
* Extract and group the main entities;
* Extract and group the specific aspects of those entities;
* Identify the opinion holder;
* Extract and standardize the time the opinion was given;
* Classify the sentiment on each aspect as positive, negative, or neutral;
* Generate the final 5-part opinion structure.

---

## 📖 7.5 Semantic Orientation and Polarity
* **Semantic Orientation**: A measurement of how subjective a text is, evaluating its polarity (positive or negative) and strength (how intense the feeling is);
* **Prior Polarity**: The standard feeling of a word when looked up in a dictionary outside of any text;
* **Contextual Polarity**: The actual feeling of a word based on how it is used in a specific sentence;
* **Meaning Shifts**: Positive words can turn negative depending on the context, such as when used with sarcasm, in bad situations, or with negations like "not great".

---

## 📖 7.6 Approaches

### 📑 7.6.1 Lexicon-Based Classification

**A Lexicon is a specialized dictionary that lists words and their pre-calculated positive or negative scores**.
This approach calculates the overall sentiment score of a text by adding up the scores of the individual words inside it.

* **Micro-phrases**: A system splits text into small chunks using grammar rules (like Adverb + Adjective + Noun) to calculate scores more accurately;
* **Modifiers**: Some words change the score of nearby words. Amplifiers (like "very") increase the intensity, downtoners (like "slightly") decrease the intensity, and negation shifters (like "not") reverse the score completely.

There are four math formulas to calculate the final text score:
* **Basic** (total score divided by text length);
* **Normalized** (adjusted for phrase length);
* **Emphasized** (gives more weight to important words like verbs and adjectives);
* **Emphasized - Normalized**.

### 📑 7.6.2 Supervised Learning Classification

**This method treats sentiment analysis like a standard text sorting problem**.
Algorithms (like _Naïve Bayes_ or _Support Vector Machines_ (_SVM_)) are trained using data that already has known ratings, such as 1-star to 5-star product reviews.
Important Features for Learning:
* **Term Frequency**: Counting how often specific words appear in the text;
* **Term Frequency-Inverse Document Frequency** (_TF-IDF_): A mathematical formula that gives higher importance to words that are rare across all documents but frequent in one specific document;
* **Parts of speech** (especially adjectives) **and punctuation** (like exclamation marks) are also used to help the system learn.

---

## 📖 7.7 Emotion Analysis

Unlike basic sentiment analysis, emotion analysis detects specific, complex feelings.
* **Plutchik's Model**: A psychological framework stating there are 8 basic, biological emotions: _Joy, Trust, Fear, Surprise, Sadness, Disgust, Anger and Anticipation_;
* **Derived Emotions**: Complex emotions created by combining two basic ones. For instance, Love is a combination of Joy and Trust;
* **Modern Tools**: Deep learning models, like **BERT** (**a powerful neural network for understanding language context**), are fine-tuned to classify text into highly specific emotion categories;
Massive datasets, such as the **GoEmotions Dataset** (which labels Reddit comments with 27 different emotions), are used to train these advanced models.


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

<img width="739" height="276" alt="image" src="https://github.com/user-attachments/assets/bbad64e5-c9ee-417b-aecc-6f4e8adc372e" />

> ##### Image: Usage of NLP pipeline modules for markables

* **Generate Features**: The system creates a feature vector containing 12 traits for every pair of words.
Key features check distance, pronoun status, string matching, gender/number agreement and whether they are proper names;
* **Train Classifier**: A decision tree learns from positive examples (adjacent pairs in a chain) and negative examples (unrelated pairs);
* **Resolve**: For a new text, the tree tests potential antecedents in reverse document order until it finds a match.

---

## 📖 8.8 Extra

| S.No | Name of the Tool                              | Developed By                              | Source                                                      | Language | Last Modified | Version | License                 |
|------|-----------------------------------------------|-------------------------------------------|-------------------------------------------------------------|----------|---------------|---------|-------------------------|
| 1    | **ARKRef**                                    | Carnegie Mellon University                | http://www.cs.cmu.edu/~ark/ARKref/                          | Java     | 2013          | none    | GPL                     |
| 2    | **BART**                                      | Johns Hopkins University                  | http://www.sfs.uni-tuebingen.de/~versley/BART/              | Java     | 2008          | 1.0     | GPL, Apache             |
| 3    | **Berkeley Entity Resolution System**         | University of California, Berkeley        | http://nlp.cs.berkeley.edu/projects/coref.shtml             | Scala    | 2015          | 1.1     | GPLv3                   |
| 4    | **GATE**                                      | The University of Sheffield               | https://gate.ac.uk/sale/tao/splitch7.html                   | Java     | 2016          | 8.5.1   | GPL                     |
| 5    | **Guitar**                                    | University of Essex                       | http://www.essex.ac.uk/research/nle/GuiTAR/                 | Java     | 2007          | 3.0.3   | GPL                     |
| 6    | **Illinois Coreference Package**              | University of Illinois                    | https://cogcomp.cs.illinois.edu/page/software_view/Coref    | Java     | 2008          | 1.3.2   | Academic Use License    |
| 7    | **JavaRAP**                                   | National University of Singapore          | http://aye.comp.nus.edu.sg/~qiu/nlpTools/JavaRAP.html       | Java     | 2011          | 1.13    | GPL                     |
| 8    | **OpenNLP**                                   | Apache Software Foundation                | https://issues.apache.org/jira/browse/OPENNLP               | Java     | 2010          | 1.6.0   | Apache v2.0             |
| 9    | **Reconcile**                                 | Cornell University                        | https://csta.cs.utah.edu/nlp/reconcile/                     | Java     | 2010          | 1.0     | GPL                     |
| 10   | **RelaxCor**                                  | Universitat Politècnica de Catalunya      | http://nlp.lsi.upc.edu/relaxcor/                            | Perl     | 2012          | 1.1     | GPL                     |
| 11   | **Stanford Deterministic Coreference System** | Stanford University                       | http://nlp.stanford.edu/software/dcoref.shtml               | Java     | 2016          | 3.9.2   | GPL v3                  |
| 12   | **SpaCy**                                     | Explosion AI                              | https://spacy.io/                                           | Python   | 2017          | 2.1.3   | MIT                     |
| 13   | **CorefGraph**                                | Rodrigo Agerri, University of Deusto      | https://pypi.org/project/corefgraph                         | Python   | 2017          | 1.2.3   | Apache Software License |
| 14   | **SpaCy CoreferenceResolver**                 | Explosion AI                              | https://spacy.io/api/coref                                  | Python   | N/A           | N/A     | MIT                     |
| 15   | **NeuralCoref**                               | Hugging Face                              | https://github.com/huggingface/neuralcoref                  | Python   | N/A           | 2       | MIT                     |

> ##### Table: List of open source Coreferencce tools and libraries


<!-- --------------------------------------------------------------- -->
<!-- ---------------- COURSE 9 aaa ----------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 9 - aaa**

## 📖 9.1 aaa
