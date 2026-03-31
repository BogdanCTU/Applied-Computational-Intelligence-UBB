import spacy
from spacy import displacy
from pathlib import Path

class SpacyTextPreprocessor:
    """
    Handles text file preprocessing for Italian.
    Extracts linguistic features using Spacy.
    Note: Stemming is omitted as Spacy utilizes lemmatization exclusively.
    """

    def __init__(self):
        """
        Initializes the preprocessor.
        Loads Italian Spacy model.
        """
        self.spacy_it = spacy.load("it_core_news_sm")

    def process_sentence(self, text):
        """
        Processes a single sentence.
        Extracts linguistic features and structural data.
        Returns a dictionary of features and the document object.
        """
        doc = self.spacy_it(text)
        
        results = {
            "tokens": [],
            "lemmas": [],
            "pos_general": [],
            "pos_detailed": [],
            "dependencies": [],
            "noun_chunks": [],
            "named_entities": []
        }

        for token in doc:
            results["tokens"].append(token.text)
            results["lemmas"].append(token.lemma_)
            results["pos_general"].append(token.pos_)
            results["pos_detailed"].append(token.tag_)
            results["dependencies"].append((token.text, token.dep_, token.head.text))

        if doc.has_annotation("DEP"):
            for chunk in doc.noun_chunks:
                results["noun_chunks"].append(chunk.text)

        for ent in doc.ents:
            results["named_entities"].append((ent.text, ent.label_))

        return results, doc

    def process_file(self, input_filepath, output_txt_filepath, output_html_filepath):
        """
        Reads sentences from an input file.
        Processes each sentence and writes detailed features to a text output file.
        Generates an HTML file containing dependency graphs.
        Returns the collected feature data.
        """
        processed_lines = []
        spacy_docs = []
        
        with open(input_filepath, 'r', encoding='utf-8') as infile, \
             open(output_txt_filepath, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                clean_line = line.strip()
                if clean_line:
                    line_results, doc = self.process_sentence(clean_line)
                    processed_lines.append(line_results)
                    spacy_docs.append(doc)
                    
                    outfile.write(f"--- Original Sentence ---\n{clean_line}\n\n")
                    outfile.write("Stemming: Not supported natively by Spacy (uses Lemmatization instead)\n")
                    outfile.write(f"Tokens: {line_results['tokens']}\n")
                    outfile.write(f"Lemmas: {line_results['lemmas']}\n")
                    outfile.write(f"POS (General): {line_results['pos_general']}\n")
                    outfile.write(f"POS (Detailed): {line_results['pos_detailed']}\n")
                    outfile.write(f"Dependency Relations: {line_results['dependencies']}\n")
                    outfile.write(f"Noun Chunks: {line_results['noun_chunks']}\n")
                    outfile.write(f"Named Entities (NER): {line_results['named_entities']}\n")
                    outfile.write("="*60 + "\n\n")

        html_data = displacy.render(spacy_docs, style="dep", page=True)
        output_path = Path(output_html_filepath)
        output_path.write_text(html_data, encoding="utf-8")

        return processed_lines

if __name__ == "__main__":
    processor = SpacyTextPreprocessor()
    
    processor.process_file(
        input_filepath="ItalianInput.txt",
        output_txt_filepath="ItalianSpacyOutput.txt",
        output_html_filepath="ItalianSpacyDependencyGraphsEnglish.html"
    )
