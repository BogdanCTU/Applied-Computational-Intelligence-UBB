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
* **Modern Tools**: Deep learning models, like **BERT** (**a powerful neural network for understanding language context**), are fine-tuned to classify text into highly specific emotion categories.
Massive datasets, such as the **GoEmotions Dataset** (which labels Reddit comments with 27 different emotions), are used to train these advanced models.
