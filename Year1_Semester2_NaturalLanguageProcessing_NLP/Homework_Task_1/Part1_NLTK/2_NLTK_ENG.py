import nltk
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk import pos_tag, ne_chunk, RegexpParser
from nltk.corpus import wordnet

class NltkTextPreprocessor:
    """
    Handles text file preprocessing for English.
    Extracts linguistic features using the NLTK library.
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
        nltk.download('wordnet', quiet=True)
        
        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        self.chunk_parser = RegexpParser("NP: {<DT>?<JJ>*<NN>}")

    def _get_wordnet_pos(self, treebank_tag):
        """
        Maps Penn Treebank POS tags to WordNet POS tags.
        Returns the corresponding WordNet POS tag.
        """
        if treebank_tag.startswith('J'):
            return wordnet.ADJ
        elif treebank_tag.startswith('V'):
            return wordnet.VERB
        elif treebank_tag.startswith('N'):
            return wordnet.NOUN
        elif treebank_tag.startswith('R'):
            return wordnet.ADV
        else:
            return wordnet.NOUN

    def process_sentence(self, text):
        """
        Processes a single sentence.
        Extracts linguistic features and structural data.
        Returns a dictionary of features and the generated syntax tree.
        """
        results = {
            "tokens": [],
            "stems": [],
            "lemmas": [],
            "pos_general": [],
            "pos_detailed": [],
            "dependencies": "Not supported natively by NLTK without external models like Stanford CoreNLP.",
            "noun_chunks": [],
            "named_entities": []
        }

        tokens = word_tokenize(text)
        results["tokens"] = tokens

        pos_detailed = pos_tag(tokens)
        results["pos_detailed"] = pos_detailed

        pos_general = pos_tag(tokens, tagset='universal')
        results["pos_general"] = pos_general

        for i in range(len(tokens)):
            token = tokens[i]
            tag_detailed = pos_detailed[i][1]
            
            results["stems"].append(self.stemmer.stem(token))
            
            wn_pos = self._get_wordnet_pos(tag_detailed)
            results["lemmas"].append(self.lemmatizer.lemmatize(token, pos=wn_pos))

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
                    outfile.write(f"POS (General): {line_results['pos_general']}\n")
                    outfile.write(f"POS (Detailed): {line_results['pos_detailed']}\n")
                    outfile.write(f"Dependency Relations: {line_results['dependencies']}\n")
                    outfile.write(f"Noun Chunks: {line_results['noun_chunks']}\n")
                    outfile.write(f"Named Entities (NER): {line_results['named_entities']}\n")
                    outfile.write("="*60 + "\n\n")

                    treefile.write(f"--- Syntax Tree for: {clean_line} ---\n")
                    treefile.write(str(tree))
                    treefile.write("\n\n" + "="*60 + "\n\n")

        return processed_lines

if __name__ == "__main__":
    processor = NltkTextPreprocessor()
    
    processor.process_file(
        input_filepath="EnglishInput.txt", 
        output_txt_filepath="EnglishNLPKOutput.txt", 
        output_tree_filepath="EnglishNLTKSyntaxTrees.txt"
    )
