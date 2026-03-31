import nltk
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize
from nltk import pos_tag, ne_chunk, RegexpParser

class ItalianNltkTextPreprocessor:
    """
    Handles text file preprocessing for Italian.
    Extracts linguistic features using the NLTK library.
    Note: NLTK lacks native Italian models for Lemmatization, POS, and NER.
    """

    def __init__(self):
        """
        Initializes the preprocessor.
        Downloads necessary NLTK datasets and initializes tools.
        """
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('averaged_perceptron_tagger_eng', quiet=True)
        nltk.download('universal_tagset', quiet=True)
        nltk.download('maxent_ne_chunker', quiet=True)
        nltk.download('maxent_ne_chunker_tab', quiet=True)
        nltk.download('words', quiet=True)
        
        self.stemmer = SnowballStemmer("italian")
        self.chunk_parser = RegexpParser("NP: {<DT>?<JJ>*<NN>}")

    def process_sentence(self, text):
        """
        Processes a single sentence.
        Extracts linguistic features and structural data.
        Returns a dictionary of features and the generated syntax tree.
        """
        results = {
            "tokens": [],
            "stems": [],
            "lemmas": ["Not supported natively by NLTK for Italian."],
            "pos_general": [],
            "pos_detailed": [],
            "dependencies": "Not supported natively by NLTK without external models.",
            "noun_chunks": [],
            "named_entities": []
        }

        tokens = word_tokenize(text, language='italian')
        results["tokens"] = tokens

        pos_detailed = pos_tag(tokens)
        results["pos_detailed"] = pos_detailed

        pos_general = pos_tag(tokens, tagset='universal')
        results["pos_general"] = pos_general

        for token in tokens:
            results["stems"].append(self.stemmer.stem(token))

        chunk_tree = self.chunk_parser.parse(pos_detailed)
        for subtree in chunk_tree.subtrees():
            if subtree.label() == 'NP':
                results["noun_chunks"].append(" ".join(word for word, tag in subtree.leaves()))

        ner_tree = ne_chunk(pos_detailed)
        for subtree in ner_tree.subtrees():
            if hasattr(subtree, 'label') and subtree.label() != 'S':
                results["named_entities"].append((" ".join(word for word, tag in subtree.leaves()), subtree.label()))

        return results, ner_tree

    def process_file(self, input_filepath, output_txt_filepath, output_tree_filepath):
        """
        Reads sentences from an input file.
        Processes each sentence and writes detailed features to a text output file.
        Generates a text file containing string representations of syntax trees.
        Returns the collected feature data.
        """
        processed_lines = []
        
        with open(input_filepath, 'r', encoding='utf-8') as infile, \
             open(output_txt_filepath, 'w', encoding='utf-8') as outfile, \
             open(output_tree_filepath, 'w', encoding='utf-8') as treefile:
            
            for line in infile:
                clean_line = line.strip()
                if clean_line:
                    line_results, tree = self.process_sentence(clean_line)
                    processed_lines.append(line_results)
                    
                    outfile.write(f"--- Original Sentence ---\n{clean_line}\n\n")
                    outfile.write(f"Tokens: {line_results['tokens']}\n")
                    outfile.write(f"Stems: {line_results['stems']}\n")
                    outfile.write(f"Lemmas: {line_results['lemmas']}\n")
                    outfile.write(f"POS (General) [English Model]: {line_results['pos_general']}\n")
                    outfile.write(f"POS (Detailed) [English Model]: {line_results['pos_detailed']}\n")
                    outfile.write(f"Dependency Relations: {line_results['dependencies']}\n")
                    outfile.write(f"Noun Chunks [English Model]: {line_results['noun_chunks']}\n")
                    outfile.write(f"Named Entities (NER) [English Model]: {line_results['named_entities']}\n")
                    outfile.write("="*60 + "\n\n")

                    treefile.write(f"--- Syntax Tree for: {clean_line} ---\n")
                    treefile.write(str(tree))
                    treefile.write("\n\n" + "="*60 + "\n\n")

        return processed_lines

if __name__ == "__main__":
    processor = ItalianNltkTextPreprocessor()
    
    processor.process_file(
        input_filepath="ItalianInput.txt", 
        output_txt_filepath="ItalianNLPKOutput.txt", 
        output_tree_filepath="ItalianNLTKSyntaxTrees.txt"
    )
