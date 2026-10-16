"""O Tear só com a seleção: a ilha em C (população, torneio, confirmação em níveis e mutação) julgada pelo leito em C, sem as ferramentas e sem a mente.

  python -B rodar_ilha.py <semente> <medidas> <pasta>

A pasta recebe `recordes.jsonl` (cada recorde, só de confirmados, com a medida em que apareceu e o banco ao lado), `melhor.json`, `progresso.json`,
`estado.pkl` (relançar com a mesma pasta continua a corrida) e `fim.json`.

O leito é o original, de 15 cláusulas (família 0). As variáveis de ambiente abaixo ficam com os valores das corridas de outubro, e quem quiser outros
valores as define antes de rodar. Sem VIDA_JANELA=2 as operações 10 a 13 da vida em C viram nada, e o resultado sai errado sem aviso."""
import json
import os
import sys
import time

AMBIENTE = {"VIDA_JANELA": "2", "VIDA_REGUA_V32": "1", "VIDA_FIOS": "1", "OPENBLAS_NUM_THREADS": "1"}
for k, v in AMBIENTE.items():
    os.environ.setdefault(k, v)

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from experimentos import vida_v3c_c as VC  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    semente, medidas, pasta = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    if int(os.environ.get("VIDA_FAMILIA", "0") or 0) != 0:
        sys.exit("RECUSADO: este pacote traz só o leito original (VIDA_FAMILIA=0).")
    t0 = time.time()
    ilha = VC.IlhaC(semente, pasta)
    r = ilha.andar(medidas, medidas)              # o segundo número é o teto TOTAL de medidas da corrida
    fim = {"semente": semente, "medidas": r["n"], "melhor": r["melhor"], "cumpriu_D": r["cumpriu"], "ultimo_recorde": r["ultimo_recorde"],
           "segundos": round(time.time() - t0, 1), "ambiente": {k: os.environ[k] for k in AMBIENTE}}
    with open(os.path.join(pasta, "fim.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(fim, f, ensure_ascii=False, indent=1)
    print(json.dumps(fim, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
