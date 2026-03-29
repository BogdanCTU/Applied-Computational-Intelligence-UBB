<!-- --------------------------------------------------------------- -->
<!-- -------------------- COURSE 1 INTRODUCTION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 1 - Introduction to Natural Language Processing**

---

## 📖 1.1 Introduction to Natural Language Processing (NLP)

* **Definition**: A subfield of **Artificial Intelligence** (_AI_) focused on the automated generation and understanding of spoken and written human languages;
* **Goal**: To achieve human-like language processing and understanding;
* **Origins**: Intersects **Linguistics** (formal structural models), **Computer Science** (internal data representation and efficient processing) and **Cognitive Psychology** (modeling language via human cognitive processes).

---

## 📖 1.2 Levels of Natural Language Processing

* **Phonology**: Interpretation of speech sounds (phonetic and prosodic rules);
* **Morphology**: Studies the componential nature of words formed by **morphemes** (stems and affixes);
* **Lexical Level**: Interpretation of individual word meanings (e.g., **part-of-speech tagging**);
* **Syntactic Level**: Analyzes grammatical structures and dependency relationships between words in a sentence using grammars and parsers;
* **Semantic Level**: Determines the exact meaning of sentences by resolving word-level ambiguities (_selecting the correct sense of polysemous words_);
* **Discourse Level**: Focuses on the text as a whole, connecting component sentences (_e.g., resolving pronouns to the entities they refer to_);
* **Pragmatic Level**: Extracts extra context and meaning not explicitly encoded in the text, requiring world knowledge, intentions and goals.

---

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

---

## 📖 1.4 Meaning and Disambiguation

* **Natural Language Meaning**: Characterized by **Variability** (multiple ways to express one meaning) and **Ambiguity** (one expression having multiple meanings);
* **Word Sense Disambiguation (WSD)**: Determining the exact sense of an ambiguous word in context. _Example: "Plant" can mean a factory or a living organism_;
* **Textual Entailment**: Determining if one text is a logical consequence of another (Yes/No/Unknown);
* **Co-reference Resolution**: Grouping words ("mentions") that refer to the same real-world entity. Includes **Anaphora resolution** (linking pronouns to previous nouns);
* **Named Entity Recognition (NER)**: Classifying text items into predefined categories (_e.g., Person, Organization, Location, Date_).

---

## 📖 1.5 Practical NLP Tasks

* **Speech Processing**: Speech recognition (speech-to-text), text-to-speech, speaker recognition;
* **Machine Translation**: Automated translation between human languages (an "AI-complete" problem);
* **Information Retrieval & Question Answering**: Finding relevant documents or exact answers to natural language queries;
* **Text Mining**: Extracting structured data from unstructured text (includes Categorization, Clustering, and Summarization);
* **Sentiment Analysis / Opinion Mining**: Analyzing attitudes and emotions. Can be applied at the Document, Sentence (subjective vs. objective) or Entity/Aspect level;
* **Other Tasks**: Authorship attribution, **Natural Language Generation** (_NLG_) and **Discourse Analysis**;

---

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

---

## 📖 1.7 Knowledge Bases in NLP

* **Corpora**: Large, structured sets of texts (Monolingual, Multilingual, Aligned, Annotated, Parsed/Treebanks);
* **Electronic Dictionaries**: Definitions and pronunciations;
* **Thesauri**: Groupings of words by semantic similarity (_e.g., WordNet_);
* **Ontologies**: Formal representations of concepts and their relationships within a specific domain.

---

## 📖 1.8 Language Models and LLMs

* **Language Models**: Built to predict word sequences and probabilities. Feature **Word Embeddings** (_Word2Vec, GloVe_), where words with similar meanings have similar vector representations;
* **Large Language Models (LLMs)**: Foundation models trained on immense datasets. Capable of generation, translation, summarization, and zero-shot reasoning. Rely heavily on **Transformer architecture** and **attention mechanisms** (_e.g., BERT, GPT_).

---

## 📖 1.9 Challenges in NLP

* **Contextual Understanding & Ambiguity**: Struggle with implicit meanings and metaphors;
* **Common Sense Reasoning**: Lacking basic human intuition and background knowledge;
* **Bias and Fairness**: Inheriting and amplifying discriminatory biases present in training data;
* **Multilingual Challenges**: Scarcity of labeled data for non-dominant languages;
* **Ethical Use**: Mitigating fake news, hate speech and ensuring transparency;
* **Continual Learning**: Updating models with new data without forgetting old knowledge.
