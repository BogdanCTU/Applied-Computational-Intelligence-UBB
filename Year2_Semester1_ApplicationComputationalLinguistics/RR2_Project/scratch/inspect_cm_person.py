import pandas as pd

df = pd.read_csv('agent_om_local/output/step7d_validation_decisions.csv')

for p in [('ConferenceMember', 'Person'), ('Participant', 'Person')]:
    s, t = p
    matches = df[((df['source_name'] == s) & (df['target_name'] == t)) |
                 ((df['source_name'] == t) & (df['target_name'] == s))]
    print(f"\n========================================================")
    print(f"PAIR: {s} <--> {t}")
    print(f"========================================================")
    for variant in ['A2.1_Original', 'A2.2_Reversed', 'A2.3_Canonical']:
        v_rows = matches[matches['variant'] == variant]
        for _, r in v_rows.iterrows():
            print(f"[{variant}] Dir: {r['direction']} | Dec: {r['decision']}")
            print(f"  Prompt: {repr(r['prompt'])}")
            print(f"  Response: {repr(r['raw_response'])}")


