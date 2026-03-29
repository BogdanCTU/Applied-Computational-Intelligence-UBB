<!-- --------------------------------------------------------------- -->
<!-- -------------------- COURSE 1 INTRODUCTION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 1 - Introduction to Natural Language Processing**

---

## 📖 1.1 - Natural Language Processing 

**Natural Language Processing** (_NLP_), also called **Language Technology** (_LT_), is a subfield of **Artificial Intelligence** (_AI_). It focuses on teaching computers to automatically understand and generate spoken and written human languages.

- **Goal**: To achieve a human-like understanding of language;
- **Origins**: NLP combines Linguistics (the rules of language), **Computer Science** (how to represent and process data efficiently) and **Cognitive Psychology** (how humans think and use language).

---

## 📖 1.2 Levels of Language Analysis

To understand text, computers must analyze it across several levels of increasing complexity:
- **Phonology**: Interprets the sounds of speech using rules about pronunciation;
- **Morphology**: Studies how words are built. Words are made of morphemes, which are the smallest units of meaning, like a root word or a prefix;
- **Lexical Level**: Analyzes the specific meaning of individual words and determines their grammatical part of speech;
- **Syntactic Level**: Analyzes the grammatical rules of a sentence to see how words relate to and depend on one another;
- **Semantic Level**: Determines the actual meaning of a full sentence by looking at how the meanings of individual words interact;
- **Discourse Level**: Looks at a whole document to find connections between different sentences;
- **Pragmatic Level**: Extracts extra, hidden meaning using real-world knowledge, logic and context.

---

## 📖 1.3 Basic Processing Tasks

Before deeper analysis, text must be broken down and labeled:
- **Tokenization**: Cuts the text into small, manageable units called tokens, which can be words, numbers or punctuation;
- **Sentence Segmentation**: Divides a large block of text into individual sentences;
- **Lemmatization**: Finds the official dictionary base form of a word, known as a lemma. Example: The word "better" has the lemma "good";
- **Stemming**: Roughly chops off word endings to find the root stem, without looking at the surrounding context. Example: "CONNECT" is the stem for "CONNECTED" and "CONNECTIONS";
- **Part-of-Speech Tagging** (_POS_) : Figures out if a word acts as a noun, verb, adjective, etc., in a sentence;
- **Chunking**: Groups words into basic phrases (like noun groups) without mapping out the deep grammatical structure;
- **Dependency Parsing**: Explores exactly how words depend on one another to map the grammatical structure;
- **Syntactic Parsing**: Creates a tree structure that assigns formal grammatical rules to a sentence.

---

## 📖 1.4 Understanding Meaning and Context

Resolving ambiguity is a major part of NLP:
- **Word Sense Disambiguation** (_WSD_): Figures out which dictionary definition applies to a word with multiple meanings based on context. Example: _Deciding if "plant" refers to a green organism or an industrial factory_;
- **Textual Entailment**: Determines if one text logically proves that another text is true;
- **Co-reference Resolution**: Identifies when different words refer to the exact same entity. _Example: Linking the pronoun "He" to the name "John Smith"_.
- **Named Entity Recognition** (**NER**): Finds proper nouns in a text and categorizes them as people, locations, dates or organizations.

---

## 📖 1.5 Practical Applications

NLP is used to build many real-world tools:
- **Speech Processing**: Includes converting spoken words to text, converting text to speech and recognizing the identity of a speaker;
- **Machine Translation**: Automatically translates text from one human language to another;
- **Information Retrieval & Question Answering**: Finds relevant documents or specific facts to answer a user's question;
- **Text Mining**: Extracts organized data from messy, unorganized text. It includes grouping documents (_clustering_) and creating short versions of long texts (_summarization_);
- **Sentiment Analysis**: Scans text to figure out a person's emotions, opinions or attitudes toward a product or topic.

---

## 📖 1.6 Core Approaches to NLP

The way computers process language has evolved over time:
- **Symbolic Approaches**: Use strict, human-written rules and logic to represent knowledge. This includes logic-based systems and semantic networks that link concepts together;
- **Statistical Approaches**: Use math and massive text databases to learn language patterns naturally;
- **Deep Learning**: A machine learning method that uses artificial neural networks with many layers. Models train on massive datasets to learn language rules directly from examples.

---

## 📖 1.7 Knowledge Resources

NLP systems rely on large databases of information:
- **Corpora**: Large, structured electronic collections of text used to train language models;
- **Dictionaries and Thesauri**: Electronic lists containing definitions, pronunciations and grouped synonyms;
- **Ontologies**: Formal maps that define concepts and show how they are related to each other in a specific subject area;
- **Language Models**: Systems built to predict sequences of words. Large Language Models (LLMs) use massive amounts of data and special neural networks (transformers) to understand context, answer questions and generate text.

---

## 📖 1.8 Impact and Current Challenges

NLP heavily impacts industries like customer service (_chatbots_), healthcare (_analyzing medical records_), finance (_analyzing reports_) and e-commerce (_product recommendations_).

However, major challenges remain:
- **Context and Common Sense**: Computers struggle with ambiguity and lack basic human common sense;
- **Bias**: Models can learn and repeat unfair biases found in their training data;
- **Language Scarcity**: Many languages do not have enough training data to build good NLP tools;
- **Misinformation**: Ensuring NLP is used ethically and stopping the generation of fake news or harmful content is an ongoing struggle.
