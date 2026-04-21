# Romanian Word Embeddings with COROLA

This project explores natural language processing using the COROLA corpus.
The COROLA corpus is a large collection of Romanian text.
The provided Python script analyzes word embeddings.
Word embeddings are a way to represent words as lists of numbers.
The computer uses these numbers to understand which words have similar meanings.

## Features

* **Nearest Neighbors Calculation:** The script finds the 10 most similar words for a given input word based on their numerical distance;
* **Vector Analogies:** The script solves mathematical equations using word meanings. A vector analogy calculates relationships between concepts. A simple example is the equation "king - man + woman = queen";
* **Automated Batch Processing:** The program reads multiple inputs from a single text file and writes all computed results to a separate text file.

## Models Analyzed

The script evaluates three different embedding models to compare how text preparation changes the results:

* **WORDS:** Uses the exact words as they appear in the original text;
* **LEMMA:** Uses the base dictionary form of the words. A lemma is the core word without grammatical endings. For example, the lemma of "studying" is "study";
* **LEMMA + POS:** Combines the base word with a Part of Speech tag. A Part of Speech is a grammatical category like a noun (a person, place, or thing) or a verb (an action). The script automatically applies the correct Morphosyntactic Description prefix for this model.

## Requirements

* Python 3
* The `gensim` library. This is a technical framework used to load and analyze word embedding models;
* The pre-trained COROLA vector models saved as `.vec` files.

## Input and Output Configuration

* The input words and analogy targets must be placed in a file named `Task2_Part2_COROLA_Input.txt`;
* Standard search words are defined using the format `POS: word1, word2`;
* Vector analogies are defined using the format `ANALOGY: word1:POS, word2:POS, word3:POS`;
* The script executes the analysis iteratively across all three models;
* The generated similarities and analogy results are saved sequentially in `Task2_Part2_COROLA_Output.txt`.
