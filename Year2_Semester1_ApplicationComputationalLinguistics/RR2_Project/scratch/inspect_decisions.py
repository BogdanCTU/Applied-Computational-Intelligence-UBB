import pandas as pd
df = pd.read_csv('agent_om_local/output/step7d_validation_decisions.csv')
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', 100)
targets = ['ProgramCommitteeChair', 'ConferenceMember', 'Participant', 'Chair_PC', 'Member']
sub = df[df['source_name'].str.contains('|'.join(targets), na=False) | df['target_name'].str.contains('|'.join(targets), na=False)]
for idx, row in sub.iterrows():
    print(f"[{row['variant']}] dir={row['direction']} bypass={row['bypassed']} dec={row['decision']}")
    print(f"  src={row['source_name']} ({row['source_uri']}) | tgt={row['target_name']} ({row['target_uri']})")
    print(f"  prompt:\n{row['prompt']}")
    print(f"  response:\n{row['raw_response']}")
    print("-" * 60)
