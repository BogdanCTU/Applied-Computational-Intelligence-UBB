import os
from gensim.models import KeyedVectors

def read_input_data(filepath: str) -> tuple:
    # Parses the input file to extract search words and analogy configurations.
    words_list = []
    analogies_list = []
    
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                
                # Parses analogy lines formatted as "ANALOGY: word1:POS, word2:POS, word3:POS"
                if line.startswith("ANALOGY:"):
                    content = line.replace("ANALOGY:", "").strip()
                    parts = [part.strip().split(":") for part in content.split(",")]
                    if len(parts) == 3:
                        analogies_list.append((
                            (parts[0][0], parts[0][1]),
                            (parts[1][0], parts[1][1]),
                            (parts[2][0], parts[2][1])
                        ))
                
                # Parses word list lines formatted as "POS: word1, word2"
                elif ":" in line:
                    pos, words_str = line.split(":", 1)
                    pos = pos.strip().upper()
                    words = [w.strip() for w in words_str.split(",")]
                    for w in words:
                        words_list.append((w, pos))
    except FileNotFoundError:
        print(f"Error: The input file {filepath} was not found.")
        
    return words_list, analogies_list

def format_word(word: str, pos_tag: str, current_model: str) -> str:
    # Applies the correct Morphosyntactic Description (MSD) prefix if the active model requires Lemma + POS.
    if current_model == "LEMMA + POS":
        pos_map = {
            "NOUN": "Nc",
            "VERB": "Vm",
            "ADJECTIVE": "Af",
            "PROPN": "Np"
        }
        prefix = pos_map.get(pos_tag, pos_tag)
        
        # Ensures proper nouns begin with a capital letter for the Np_ format.
        if pos_tag == "PROPN":
            word = word.capitalize()
            
        return f"{prefix}_{word}"
    return word

# Defines the base directory and the specific paths for the three COROLA models.
base_dir = "E:\\_3_Master\\_5_SEM2_NaturalLanguageProcessing_NLP\\TASK2\\COROLA\\"
input_filename = "Task2_Part2_COROLA_Input.txt"
output_filename = "Task2_Part2_COROLA_Output.txt"

models = [
    ("WORDS", os.path.join(base_dir, "corola.300.20.vec")),
    ("LEMMA", os.path.join(base_dir, "corola.lemma.300.50.vec")),
    ("LEMMA + POS", os.path.join(base_dir, "corola.lemma.pos.300.50.vec"))
]

# Extracts data from the external file.
words_to_search, vector_analogies = read_input_data(input_filename)

# Clears the existing content of the output file before starting the batch process.
with open(output_filename, "w", encoding="utf-8") as file:
    file.write("")

# Iterates through each model, processes the input data, and writes the output.
for model_name, model_path in models:
    print(f"Loading {model_name} model...")
    
    try:
        model = KeyedVectors.load_word2vec_format(model_path, binary=False)
    except FileNotFoundError:
        print(f"Error: Model not found at {model_path}. Skipping.")
        continue

    # Appends the results for the current model to the text file.
    with open(output_filename, "a", encoding="utf-8") as file:
        file.write(f"--------------------------- The {model_name} specific word embeddings ---------------------------\n")
        
        # Calculates and writes the 10 nearest neighbors for each input word.
        for raw_word, tag in words_to_search:
            search_word = format_word(raw_word, tag, model_name)
            file.write(f"\nNeighbors for '{search_word}':\n")
            
            if search_word in model:
                neighbors = model.most_similar(search_word, topn=10)
                for neighbor, score in neighbors:
                    file.write(f"  {neighbor}: {score:.4f}\n")
            else:
                file.write("  Word not found in the vocabulary.\n")
        
        # Calculates and writes the vector analogy operations.
        file.write("\n")
        for (w1, t1), (w2, t2), (w3, t3) in vector_analogies:
            fw1 = format_word(w1, t1, model_name)
            fw2 = format_word(w2, t2, model_name)
            fw3 = format_word(w3, t3, model_name)
            
            try:
                result = model.most_similar(positive=[fw1, fw3], negative=[fw2], topn=5)
                file.write(f"{fw1} - {fw2} + {fw3} = {result}\n")
            except KeyError:
                file.write(f"{fw1} - {fw2} + {fw3} = [Word missing from vocabulary]\n")
        
        file.write("\n")

print("\nTask 2 Part 2 COROLA completed successfully.")
