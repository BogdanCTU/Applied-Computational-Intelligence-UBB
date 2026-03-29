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
<!-- ---------------- COURSE 3 ----------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 3 - **
