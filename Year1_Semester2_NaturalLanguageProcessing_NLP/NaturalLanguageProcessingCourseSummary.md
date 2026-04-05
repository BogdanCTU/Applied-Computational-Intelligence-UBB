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
<!-- --------------------- COURSE 3 CLUSTERING --------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 3 - Clustering**

## 📖 3.1 Definition of Clustering

🔴 **Clustering is the task of dividing data points into groups**, which are called **clusters**:
* **Data points in the same cluster are highly similar to each other**;
* **Data points in different clusters are highly different from each other**;
* **It is an unsupervised learning method**. This means the algorithm finds patterns on its own without using pre-labeled data;
* The input is usually a vector, which is just a list of numbers representing a single data point.

---

## 📖 3.2 Types of Clustering
* **Hard Clustering**: A data point completely belongs to one specific cluster, or it does not.
Example: A store places a customer exactly into group A;
* **Soft Clustering**: A data point is given a probability or chance, of belonging to different clusters.
Example: A customer has a 70% chance of being in group A and a 30% chance of being in group B.

---

## 📖 3.3 Distance Metrics
🔴 **Distance metrics are math formulas used to measure how similar two objects are**.
We treat the objects as vectors, $g_{1}$ and $g_{2}$.
* **Euclidean distance**: The straight-line distance between two points.
Formula: $d(g_{1},g_{2})=\sqrt{\sum_{i=1}^{n}(x_{i}-y_{i})^{2}}$.
* **Manhattan distance**: The distance measured along axes at right angles, like walking city blocks.
Formula: $d(g_{1},g_{2})=\sum_{i=1}^{n}|(x_{i}-y_{i})|$.
* **Minkowski distance**: A flexible formula that generalizes the two above.
Formula: $d(g_{1},g_{2})=\sqrt[m]{\sum_{i=1}^{n}(x_{i}-y_{i})^{m}}$.

---

## 📖 3.4 Clustering Models

### 📑 3.4.1 Hierarchical Clustering (Connectivity Model)

🔴 **Connectivity models group points based on the idea that closer points in space are more similar**.

* **Bottom-Up Approach**: Starts by treating every single data point as its own separate cluster. It repeatedly merges the closest pair of clusters together. It stops when all points are combined into one single giant cluster;
* **Dendrogram**: A tree-like diagram that shows the history of how clusters were merged.  The root is the final giant cluster, and the leaves are the starting single points.

Similarity Measures:
* **Single-link**: Measures distance by looking only at the two closest (most similar) points between two clusters;
* **Complete-link**: Measures distance by looking at the two farthest (most dissimilar) points between two clusters.

### 📑 3.4.2 K-Means Clustering (Centroid Model)

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

## 📖 3.5 Evaluation Metrics
Metrics are used to score how good the resulting clusters are.

### 📑 3.5.1 Internal Metrics
Used when you do not know the true groups. They check for compactness (points are packed tightly) and separation (clusters are far apart);
* **Silhouette Coefficient**: Measures if a point is close to its own cluster but far from others. Scores range from -1 to 1, and closer to 1 is better;
* **Dunn Index**: The ratio of the shortest distance between clusters to the largest cluster size. Higher scores mean tighter, better-separated clusters;
* **Inertia**: The sum of squared distances between points and their centers. Lower scores mean tighter clusters;
* **Davies-Bouldin Index** (_DBI_): Calculates the ratio of distances inside a cluster compared to distances between clusters. A lower score is better;
* **Calinski-Harabasz Index**: Measures how spread apart the clusters are compared to how spread apart the points inside a cluster are. A higher score is better.

### 📑 3.5.2 External Metrics
Used when you already know the true, correct groups (ground truth labels) to compare against.
* **Adjusted Rand Index** (_ARI_): Looks at pairs of points to see if the algorithm grouped them correctly. It adjusts for random guessing. A score of 1.0 is perfect, while 0.0 is random;
* **Rand Index** (_RI_): Measures the percentage of correctly grouped pairs, but does not adjust for random guessing;
* **Jaccard Index**: Measures shared correct pairs divided by the total number of unique pairs;
* **Normalized Mutual Information** (_NMI_): Measures how much correct information is shared between the true groups and the predicted groups. Scores range from 0 to 1.

<!-- --------------------------------------------------------------- -->
<!-- ------------------- COURSE 4 SUMMARIZATION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 4 - Summarization**

## 📖 4.1 Definition of Summarization

🔴 The **Document Summarization** is the process of taking an information source, extracting its content and presenting the most important parts in a short form.
The goal is to meet the specific needs of a user or application. **A summary is a short version of a text** (usually half the size or less) **that keeps the main ideas**.
An **Automatic Summarization** happens when a computer program creates the shortened text. Good automatic summaries must preserve key information and remain short and logical.

---

## 📖 4.2 Coherence and Cohesion
To write a good summary, the text must make sense. This relies on two concepts:
* **Coherence**: This is what makes a text logically meaningful overall. It is an abstract quality that focuses on how ideas are organized. Because it deals with ideas, coherence is qualitative and hard to measure;
* **Cohesion**: This is the actual grammatical and vocabulary glue that holds words and sentences together. It is a visible, measurable property.
    * _Lexical cohesion_ links words by meaning, such as repeating a word or using a synonym;
    * _Grammatical cohesion_ links words using grammar, such as using pronouns (like "she") or conjunctions (like "because").
* **The Rule**: A coherent text is always cohesive, but a cohesive text might not be coherent. Think of coherence as a finished building, and cohesion as the bricks.

> ### 📚 Grammar Concepts

### 4.2.1 Grammatical Cohesion

| Concept        | Definition                                                                 | Example                                                                 |
|----------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| **Anaphora**       | Referring back to something previously mentioned.                           | "Jane was brilliant. She got the best score." ("She" → "Jane")          |
| **Cataphora**      | Referring forward to something that will be mentioned.                      | "Here he comes our hero. Please, welcome John." ("he" → "John")         |
| **Ellipsis**       | Omitting words that are understood from context.                            | "A: Where are you going? B: To dance." ("I am going" omitted)            |
| **Substitution**   | Replacing a word/phrase with another to avoid repetition.                   | "I would like the pink one." ("one" → "T-shirt")                         |
| **Conjunctions**   | Linking words that connect ideas or sentences.                              | "We agree on the principle but disagree on the method."                 |

### 4.2.2 Lexical Cohesion

| Concept     | Definition                                                                 | Example                                                                 |
|-------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| **Repetition**  | Reusing the same word multiple times.                                      | "Birds are beautiful. Everybody likes birds."                           |
| **Synonymy**    | Using words with similar or identical meanings.                            | "snake" → "serpent"                                                     |
| **Hyponymy**    | Using a general category to refer to a specific item.                      | "cat" → "animal"                                                        |
| **Meronymy**    | Using a part-to-whole relationship.                                        | "tire" → part of "car"                                                  |
| **Antonymy**    | Using words with opposite meanings.                                        | "old" ↔ "new"                                                           |

### 📑 4.2.3 Tool for the Automatic Analysis of Cohesion (TAACO)

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

## 📖 4.3 Types of Summaries
Summaries come in different forms:
* **Extract vs. Abstract**: An extract copies exact sentences from the text, while an abstract rewrites the content in new words;
* **Single vs. Multi-document**: A summary can be made from just one text or by combining many texts;
* **Indicative vs. Informative**: Indicative summaries act as a quick alert to tell you what a text is about. Informative summaries act as a substitute for the full text.

---

## 📖 4.4 The Three Stages of Summarization
Every summarizer follows three steps:
* **Analysis**: The system reads and understands the source text to build a mental map of it;
* **Transformation**: The system selects the most important content from that map;
* **Synthesis**: The system generates the final shortened text.

---

## 📖 4.5 Extractive vs. Abstractive Summarization
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

## 📖 4.6 How Computers Score Sentences (Extractive Features)
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

## 📖 4.7 Mathematical and AI Methods
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

## 📖 4.8 Evaluating a Summary
We need to test if a summary is actually good.
* **Intrinsic Evaluation**: Humans grade the summary by reading it. They check for good spelling, grammar, and informativeness (how much original text survived);
* **Extrinsic Evaluation**: Testers see if the summary helps a person accomplish a real-world task, like answering a reading comprehension test;
* **ROUGE**: This is an automated software tool. It mathematically compares a computer's summary to a perfect human summary by counting how many words and phrases match.


<!-- --------------------------------------------------------------- -->
<!-- ----------------- COURSE 5 SYNTACTIC PARSING ------------------ -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 5 - Syntactic Parsing**

## 📖 5.1 Parsing Techniques
* **Constituency Parsing**: Identifies groups of words, called constituents and arranges them in a hierarchical tree structure;
* **Dependency Parsing**: Connects words directly to each other using directed links to show how they relate. 

<img width="826" height="328" alt="image" src="https://github.com/user-attachments/assets/d2e6707c-3498-469b-91a5-85186ab92b82" />

> ##### Image: Dependency Parsing using Relate-Teprolin

<img width="675" height="564" alt="image" src="https://github.com/user-attachments/assets/e2b1dd02-2ec7-4a93-b1d3-a140e4664586" />

> ##### Image: Constituency and Dependency Parsing

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
* 🔴 **Cocke-Kasami-Younger Algorithm** (_CKY_): A bottom-up method driven by a table. It requires the grammar to be in **Chomsky Normal Form** (_CNF_), meaning every rule must break down into exactly two non-terminals or one word. It builds a matrix where each cell holds the phrases that cover a specific span of words;

<img width="571" height="413" alt="image" src="https://github.com/user-attachments/assets/57ea3b0c-e7c9-4c99-8b42-91618ef06fc9" />

> ##### Image: Cocke-Kasami-Younger Algorithm
 
* **Earley Algorithm**: A top-down search method that also uses tables to build predictions. 

---

## 📖 5.7 Statistical Parsing
🔴 **Probabilistic Context-Free Grammar** (_PCFG_) is a Context-Free Grammar (CFG) where every production rule is assigned a **probability**.
* These probabilities help solve ambiguity by allowing the computer to choose the most likely parse tree;
* The probability of a specific parse tree is calculated by multiplying the probabilities of all the rules used to build it;
* Rule probabilities are usually learned from a Treebank, which is a large database of sentences already parsed by humans. 

<img width="843" height="510" alt="image" src="https://github.com/user-attachments/assets/29124110-5ca6-46b0-8d24-7bc6c634dd91" />

> ##### Image: Probabilities sample for finding the right parse tree

---

## 📖 5.8 Evaluating Parsers
🔴 **PARSEVAL** measures are standard formulas used to compare a computer's parse tree against a human-made "gold standard" reference tree;
* **Labeled Recall**: The fraction of correct phrases in the human reference tree that the computer successfully found;
* **Labeled Precision**: The fraction of phrases proposed by the computer that are actually correct.

---

## 📖 5.9 Applications of Syntactic Analysis

Understanding word relationships is a core step for many advanced language technologies.  It is used heavily in:
* **Machine Translation**: To ensure translated sentences follow correct grammar;
* **Question Answering**: To link question words to their proper answers;
* **Speech Recognition**: To figure out the grammatical structure of spoken words;
* **Sentiment Analysis**, Text Summarization, and Grammar Checking.

<!-- --------------------------------------------------------------- -->
<!-- --------------------- COURSE 6 --------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 6 - **

