# Point ONE profile's provider `spark` at the flash-next endpoint (:11439) — same change as root/worker/orchestrator. Usage: flip_one_profile.py <profile>
import sys,shutil,datetime,re
prof=sys.argv[1]; p=f"/opt/t1000/home/profiles/{prof}/config.yaml"; s=open(p).read()
old="""  spark:
    name: Spark Ollama (tunnel :11435)
    api: http://127.0.0.1:11435/v1
    api_key: ollama
"""
new="""  spark:
    # FLIPPED 2026-09-06 (t_37efebbb): flash-next via llama.cpp on ryan-spark, tunnel :11439.
    # llama-server serves ANY model name, so the model names below are aliases of flash-next.
    name: Spark flash-next (tunnel :11439)
    api: http://127.0.0.1:11439/v1
    api_key: local
"""
if s.count(old)!=1: print(f"{prof}: spark block not in expected form, skipped"); sys.exit(0)
s=s.replace(old,new,1)
s=re.sub(r"(  spark:\n(?:    .*\n)*?    models:\n)(\s+- )", r"\1\2qwen3.8-flash-next\n\2", s, count=1)
shutil.copy(p, p+".bak-pre-flash-flip-"+datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ"))
open(p,"w").write(s); print(f"{prof}: provider spark -> :11439 flash-next")
