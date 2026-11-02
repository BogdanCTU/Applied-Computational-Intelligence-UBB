import pandas as pd

df = pd.read_csv('agent_om_local/output/step7d_validation_decisions.csv')

diff_names = [
    ('ProgramCommitteeChair', 'Chair_PC'),
    ('Chair_PC', 'ProgramCommitteeChair'),
    ('ConferenceMember', 'Person'),
    ('Participant', 'Person'),
    ('ConferenceMember', 'Member'),
    ('ConferenceMember', 'Participant'),
    ('ConferenceMember', 'Member_PC'),
    ('ConferenceMember', 'Conference')
]

for s, t in diff_names:
    matches = df[((df['source_name'] == s) & (df['target_name'] == t)) |
                 ((df['source_name'] == t) & (df['target_name'] == s))]
    print(f"\n========================================================")
    print(f"PAIR: {s} <--> {t}")
    print(f"========================================================")
    for variant in ['A2.1_Original', 'A2.2_Reversed', 'A2.3_Canonical']:
        v_rows = matches[matches['variant'] == variant]
        if v_rows.empty:
            print(f"[{variant}]: NOT EVALUATED (skipped due to early accept on earlier candidate)")
        else:
            for _, r in v_rows.iterrows():
                print(f"[{variant}] Dir: {r['direction']} | Dec: {r['decision']}")
                print(f"  Prompt: {repr(r['prompt'])}")
                print(f"  Response: {repr(r['raw_response'])}")

