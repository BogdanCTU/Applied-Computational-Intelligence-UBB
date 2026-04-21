# WordNet and SentiWordNet Analyzer

This repository contains a Python script that analyzes English words.
It looks up words in a dictionary database to find their meanings, sentiment scores and related words. 

The script uses **Natural Language Toolkit** (_NLTK_). _NLTK_ is a set of tools for processing human language data in Python. It relies on two specific _NLTK_ databases:
*   **WordNet**: A large database of English words linked together by their meanings;
*   **SentiWordNet**: A tool built on WordNet. It assigns positive, negative and objective scores to words based on their emotional tone.

## Technical Terms Used

*   **Part of Speech (POS)**: The role a word plays in a sentence. Examples include nouns, verbs and adjectives;
*   **Synset**: A set of synonyms. This is a group of words that share the exact same concept or meaning;
*   **Hypernym**: A broader word category. For example, "educator" is a hypernym of "teacher";
*   **Hyponym**: A narrower word category. For example, "math teacher" is a hyponym of "teacher".

## Features

The `EnglishWordNetAnalyzer` script performs the following steps:
1.  **Reads Input**: It opens a text file containing words grouped by their Part of Speech;
2.  **Finds Meanings**: It looks up every possible synset for each word;
3.  **Extracts Details**: For each synset, it finds the definition and the specific literal words used;
4.  **Scores Sentiment**: It uses SentiWordNet to give each meaning a Positive, Negative and Objective (PNO) score;
5.  **Maps Relationships**: It finds all broader concepts (hypernyms) and narrower concepts (hyponyms) related to the word;
6.  **Saves Output**: It writes all this organized data into a new text file.

## Input File Format

The script requires an input text file named `Task2_Part1_WordNet_Input.txt`. The file must group words by their Part of Speech using a colon and comma-separated values. 

**Example Input:**
```text
NOUN: student, teacher, university
VERB: study, present, work
ADJECTIVE: intelligent, hard
```

## How to Run

1.  Make sure you have **Python** installed.
2.  Install the _NLTK_ library if you do not have it:
    ```bash
    pip install nltk
    ```
3.  Run the script. It will automatically download the required WordNet and SentiWordNet datasets on the first run if you uncomment the download lines in the code.
    ```bash
    python analyzer.py
    ```
4.  Open the newly created `Task2_Part1_WordNet_Output.txt` file to view the analysis results.
```
