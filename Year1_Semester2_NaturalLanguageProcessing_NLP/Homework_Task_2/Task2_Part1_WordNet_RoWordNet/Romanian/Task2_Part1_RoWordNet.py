import rowordnet as rwn
from rowordnet import Synset

class RomanianWordNetAnalyzer:
    def __init__(self, input_path: str, output_path: str):
        # Inițializează obiectul RoWordNet și setează căile fișierelor pentru citirea și scrierea datelor.
        self.wn = rwn.RoWordNet()
        self.input_path = input_path
        self.output_path = output_path

    def analyze(self) -> None:
        # Orhestrează citirea fișierului de intrare și procesarea fiecărui cuvânt categorizat.
        words_by_pos = self._read_input()
        
        with open(self.output_path, "w", encoding="utf-8") as out_file:
            for pos_name, words in words_by_pos.items():
                out_file.write(f"\n------------------------ Analiza cuvintelor pentru {pos_name} ------------------------\n")
                for word in words:
                    self._process_single_word(word.strip(), pos_name, out_file)

    def _read_input(self) -> dict:
        # Analizează fișierul text într-un dicționar grupat după partea de vorbire.
        # Așteaptă linii structurate sub forma "PARTE_DE_VORBIRE: cuvânt1, cuvânt2".
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
            print(f"Eroare: Fișierul {self.input_path} nu există. Este returnat un dicționar gol.")
        return data

    def _process_single_word(self, word: str, pos_name: str, out_file) -> None:
        # Recuperează identificatorii synset pentru un cuvânt specific și direcționează extragerea detaliilor.
        out_file.write(f"\nCuvântul curent ({pos_name}) este '{word}'\n")
        
        # Mapează identificatorul șirului la constanta oficială a părții de vorbire din RoWordNet.
        pos_tag = None
        if pos_name == "NOUN":
            pos_tag = Synset.Pos.NOUN
        elif pos_name == "VERB":
            pos_tag = Synset.Pos.VERB
        elif pos_name == "ADJECTIVE":
            pos_tag = Synset.Pos.ADJECTIVE

        try:
            synset_ids = self.wn.synsets(literal=word, pos=pos_tag)
            
            if not synset_ids:
                out_file.write("  Nu au fost găsite synset-uri pentru acest cuvânt.\n")
                return

            for synset_id in synset_ids:
                self._write_synset_details(synset_id, out_file)
        except Exception as e:
            out_file.write(f"  Eroare la procesarea cuvântului: {e}\n")

    def _write_synset_details(self, synset_id: str, out_file) -> None:
        # Extrage sensurile, domeniul, scorurile de sentiment și relațiile dintr-un singur synset și le scrie în fișier.
        synset = self.wn.synset(synset_id)
        
        out_file.write(f"\nSynset-ul curent este {synset_id} cu literalii {synset.literals}.\n")
        out_file.write(f"  Definiție: '{synset.definition}'.\n")
        out_file.write(f"  Domeniu: '{synset.domain}'\n")
        out_file.write(f"  Scor PNO: {synset.sentiwn}\n")
        
        # Recuperează și scrie relațiile de ieșire (outbound).
        out_file.write("  Relații de ieșire:\n")
        outbound_relations = self.wn.outbound_relations(synset_id)
        if outbound_relations:
            for target_synset_id, relation in outbound_relations:
                target_literals = self.wn.synset(target_synset_id).literals
                out_file.write(f"    - Relația [{relation}] către synset-ul {target_synset_id}, literali {target_literals}\n")
        else:
            out_file.write("    - Nu s-au găsit relații de ieșire.\n")

        # Recuperează și scrie relațiile de intrare (inbound).
        out_file.write("  Relații de intrare:\n")
        inbound_relations = self.wn.inbound_relations(synset_id)
        if inbound_relations:
            for source_synset_id, relation in inbound_relations:
                source_literals = self.wn.synset(source_synset_id).literals
                out_file.write(f"    - Relația [{relation}] de la synset-ul {source_synset_id}, literali {source_literals}\n")
        else:
            out_file.write("    - Nu s-au găsit relații de intrare.\n")

# Bloc de execuție
if __name__ == "__main__":
    task = RomanianWordNetAnalyzer("Task2_Part1_RoWordNet_Input.txt", "Task2_Part1_RoWordNet_Output.txt")
    task.analyze()
    print("Tema 2 RoWordNet completată cu succes (rezultate în fișierul Task2_Part1_RoWordNet_Output.txt).")