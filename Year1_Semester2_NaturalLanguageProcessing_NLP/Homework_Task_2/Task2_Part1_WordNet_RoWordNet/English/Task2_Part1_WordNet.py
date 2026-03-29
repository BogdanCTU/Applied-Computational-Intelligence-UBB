import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import sentiwordnet as swn

# If needed download the required English language data sets:
# nltk.download('wordnet')
# nltk.download('sentiwordnet')
# nltk.download('omw-1.4')

class EnglishWordNetAnalyzer:
    
    
    def __init__(self, input_path: str, output_path: str):
        # Initializes the file paths for reading input words and saving the output results.
        self.input_path = input_path
        self.output_path = output_path


    def analyze(self) -> None:
        # Reads the word lists, triggers the analysis for each word, and handles file writing.
        words_by_pos = self._read_input()
        
        with open(self.output_path, "w", encoding="utf-8") as out_file:
            for pos_name, words in words_by_pos.items():
                out_file.write(f"\n------------------------ {pos_name} word analysis ------------------------\n")
                for word in words:
                    self._process_single_word(word.strip(), pos_name, out_file)


    def _read_input(self) -> dict:
        # Parses the text file into a dictionary grouped by the part of speech.
        # Expects lines structured as "PART_OF_SPEECH: word1, word2".
        data = {"NOUN": [], "VERB": [], "ADJECTIVE": []}
        try:
            with open(self.input_path, "r", encoding="utf-8") as in_file:
                for line in in_file:
                    if ":" in line:
                        pos, word_list = line.split(":", 1)
                        pos = pos.strip().upper()
                        if pos in data:
                            data[pos] = [w.strip() for w in word_list.split(",")]
        except FileNotFoundError:
            print(f"Error: The file {self.input_path} does not exist. An empty dictionary is returned.")
        return data


    def _process_single_word(self, word: str, pos_name: str, out_file) -> None:
        # Retrieves synsets for a specific word and directs the extraction of its details.
        out_file.write(f"\nCurrent {pos_name} is '{word}'\n")
        
        # Maps the string identifier to the official NLTK part of speech constant.
        pos_tag = None
        if pos_name == "NOUN":
            pos_tag = wn.NOUN
        elif pos_name == "VERB":
            pos_tag = wn.VERB
        elif pos_name == "ADJECTIVE":
            pos_tag = wn.ADJ

        synsets = wn.synsets(word, pos=pos_tag)
        
        if not synsets:
            out_file.write("  No synsets found for this word.\n")
            return

        for synset in synsets:
            self._write_synset_details(synset, out_file)


    def _write_synset_details(self, synset, out_file) -> None:
        # Extracts meanings, sentiment scores, and hierarchical relations from a single synset and writes to the file.
        synset_id = synset.name()
        literals = [lemma.name() for lemma in synset.lemmas()]
        definition = synset.definition()
        
        # Retrieves Positive, Negative, and Objective scores safely.
        pos_score, neg_score, obj_score = 0.0, 0.0, 1.0
        try:
            senti_synset = swn.senti_synset(synset_id)
            pos_score = senti_synset.pos_score()
            neg_score = senti_synset.neg_score()
            obj_score = senti_synset.obj_score()
        except Exception:
            pass

        out_file.write(f"\nCurrent synset is {synset_id} with literals {literals}.\n")
        out_file.write(f"  Definition: '{definition}'.\n")
        out_file.write(f"  PNO score: Positive: {pos_score}, Negative: {neg_score}, Objective: {obj_score}\n")
        
        # Retrieves and writes broader categories (hypernyms).
        hypernyms = synset.hypernyms()
        out_file.write("  Outbound Relations (Broader Concepts):\n")
        if hypernyms:
            for hypernym in hypernyms:
                out_file.write(f"    - Relation [hypernym] to synset {hypernym.name()}, literals {[l.name() for l in hypernym.lemmas()]}\n")
        else:
            out_file.write("    - No broader concepts found.\n")

        # Retrieves and writes narrower categories (hyponyms).
        hyponyms = synset.hyponyms()
        out_file.write("  Inbound Relations (Narrower Concepts):\n")
        if hyponyms:
            for hyponym in hyponyms:
                out_file.write(f"    - Relation [hyponym] from synset {hyponym.name()}, literals {[l.name() for l in hyponym.lemmas()]}\n")
        else:
            out_file.write("    - No narrower concepts found.\n")

# Execution block
if __name__ == "__main__":
    task = EnglishWordNetAnalyzer("Task2_Part1_WordNet_Input.txt", "Task2_Part1_WordNet_Output.txt")
    task.analyze()
    print("Task 2 WordDet successfully completed (output on Task2_Part1_WordNet_Output file).")
    
