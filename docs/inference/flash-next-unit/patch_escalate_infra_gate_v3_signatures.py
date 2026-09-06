import json,shutil
p="/opt/t1000/home/scripts/kanban_model_escalate.py"; s=open(p).read()
old='''    "max retries exceeded",
]
HOLD_REPEAT_SECS'''
new='''    "max retries exceeded",
    "unknown provider",
    "check 'hermes model'",
    "api call failed after",
]
HOLD_REPEAT_SECS'''
assert s.count(old)==1; open(p,"w").write(s.replace(old,new,1))
cp="/opt/t1000/home/kanban/model_escalate.json"; cfg=json.load(open(cp))
for sub in ["unknown provider","check 'hermes model'","api call failed after"]:
    if sub not in cfg["infra_error_substrings"]: cfg["infra_error_substrings"].append(sub)
json.dump(cfg,open(cp,"w"),indent=2); open(cp,"a").write("\n"); print("signatures added")
