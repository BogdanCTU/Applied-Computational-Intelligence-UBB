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
* **Abstractive Summarization**: This method understands the original text and retells it in fewer, new words. It uses complex Natural Language Processing (NLP)—how computers interpret human language—to write fluently.
    * _Outcome_: It creates a very natural summary using Generative AI, but it might accidentally change the original facts.

---

## 📖 4.6 How Computers Score Sentences (Extractive Features)
In extractive summarization, a computer grades sentences to decide which ones to keep. Sentences score higher if they:
* **Contain Keywords**: Sentences with highly frequent nouns get high scores;
* **Match the Title**: Sentences that share words with the document's title are seen as important;
* **Have Good Location**: The first and last sentences of paragraphs are usually the most valuable;
* **Are the Right Length**: Sentences that are too short or too long are penalized;
* **Include Clues**: Sentences with proper names, uppercase words, or cue phrases (like "in conclusion") get a boost.

---

## 📖 4.7 Mathematical and AI Methods
Computers use different algorithms to pick the best sentences:
1) **Machine Learning**: The program looks at human-made summaries to learn the rules of extraction. It treats summarization as a simple choice: "Is this a summary sentence, Yes or No?";
2) **Graph-Based Ranking** (**TextRank**): This treats sentences as points on a map (a graph).
    * Sentences "vote" for each other based on how similar they are;
    * Similarity is calculated by counting how many words the two sentences share;
    * Sentences with the most votes win and go into the summary;
    * The Formula: The ranking score uses a damping factor ($d$) and edge weights ($w$) for similarity:
    $$WS(V_{i})=(1-d)+d^{*}\sum_{V_{j}\in In(V_{i})}\frac{w_{ji}}{\sum_{V_{k}\in Out(V_{j})}w_{jk}}WS(V_{j})$$
3) **Summarization by Clustering**: Clustering means grouping similar sentences together.
    * By picking just one sentence from each group (cluster), the summary avoids repeating the same information;
    * **The Formula**: Computers group these sentences by measuring cosine similarity, as following:
    $$\mathrm{sim}(S_i,S_j)=\cos(V_i,V_j)=\frac{\sum_{k=1}^{m}f(i,t_k)\,f(j,t_k)}{\sqrt{\left(\sum_{k=1}^{m}f(i,t_k)^2\right)\left(\sum_{k=1}^{m}f(j,t_k)^2\right)}}$$
4) **BERTSum** (**Neural Networks**): BERTSum is an advanced AI model that reads an entire document. It transforms words into complex mathematical vectors (embeddings) and uses a classifier to predict exactly which sentences should make the final cut.

---

## 📖 4.8 Evaluating a Summary
We need to test if a summary is actually good.
* **Intrinsic Evaluation**: Humans grade the summary by reading it. They check for good spelling, grammar, and informativeness (how much original text survived);
* **Extrinsic Evaluation**: Testers see if the summary helps a person accomplish a real-world task, like answering a reading comprehension test;
* **ROUGE**: This is an automated software tool. It mathematically compares a computer's summary to a perfect human summary by counting how many words and phrases match.
