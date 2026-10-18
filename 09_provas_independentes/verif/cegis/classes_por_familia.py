"""classes_no_limite (campo da auditoria do z3) por familia, nos casos folgados (B = 50).

Uso: python3 -I classes_por_familia.py <auditoria_z3.json>
"""
import json, sys, collections
A = json.load(open(sys.argv[1], encoding="utf-8"))["casos"]
print("folgado (familia, classes_no_limite):", dict(collections.Counter((c["rotulo"].split("-")[2], c["classes_no_limite"]) for c in A if c["rotulo"].endswith("folgado"))))
por_id = {c["id"]: c for c in A}
print("curto com classes_no_limite <= folgado do par:", sum(1 for c in A if c["rotulo"].endswith("curto") and c["classes_no_limite"] <= por_id[c["id"] - 1]["classes_no_limite"]), "de 96")
