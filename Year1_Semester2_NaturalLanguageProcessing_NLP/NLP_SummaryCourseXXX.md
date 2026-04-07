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
