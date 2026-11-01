# Automatic milestone suggestions

Enabled by default. Normal refresh assesses declared capability gaps and objectives locally. `milestone --json` exposes deterministic, deduplicated drafts and source references. Plain output shows the draft count. No model requests, executor prompt additions or automatic activation occur. Configured milestone gates and authority remain unchanged.

```
python3 -m urace configuration auto-milestones --json
python3 -m urace configuration auto-milestones --enabled false --json
python3 -m urace configuration auto-milestones --enabled true --json
python3 -m urace milestone --json
```

Draft IDs are stable for unchanged criteria. Existing non-superseded milestone coverage suppresses duplicate suggestions. Completed capabilities/objectives need no new draft; missing capability observations remain UNKNOWN. Objective success criteria are copied literally, never translated into invented acceptance tests. A draft requires review of independent acceptance, quality and constraints before adoption through existing authority. Expected planning benefit is qualitative and unverified; no numeric value score is invented. Disable hides suggestions while preserving existing milestones/history. Refresh stores only compact counts/status; full drafts are computed on demand, avoiding repeated history growth. This is local planning feedback, not evidence that the product has qualified or delivered user benefit.
