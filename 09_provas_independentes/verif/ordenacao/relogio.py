"""Investiga a granularidade dos ciclos registrados (rdtsc) no ledger da corrida de 8 elementos.

Os campos ciclos_por_vetor, ciclos_referencia e ciclos_simd sao a mediana de contagens inteiras de blocos de 256 vetores, divididas por 256.
Logo ciclos*256 deve ser inteiro (a mediana do programa pega um elemento, nao a media de dois). Se o contador avanca em passos de q
tiques, as contagens sao multiplos de q (ou proximas). Aqui se procura o q que melhor explica os valores.

Uso: python3 -I relogio.py <ledger.jsonl>
"""
import json
import sys


def main():
    L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
    ticks = []
    for e in L:
        if e["tipo"] != "veredito":
            continue
        m = e["medidas"]
        for k in ("ciclos_por_vetor", "ciclos_referencia", "ciclos_simd"):
            ticks.append(m[k] * 256)
    inteiros = [round(t) for t in ticks]
    err = max(abs(t - round(t)) for t in ticks)
    print("valores:", len(ticks), "maior distancia de um inteiro (ciclos*256):", round(err, 3))
    print("amostra de contagens:", sorted(set(inteiros))[:40])
    # para cada q, a fracao de contagens que fica a menos de 1 tique de um multiplo de q
    melhores = []
    for q in range(2, 200):
        perto = sum(1 for t in inteiros if min(t % q, q - t % q) <= 1)
        melhores.append((perto / len(inteiros), q))
    melhores.sort(reverse=True)
    print("q com mais contagens a <=1 tique de um multiplo (fracao, q):", [(round(f, 3), q) for f, q in melhores[:12]])
    # diferencas entre contagens distintas
    u = sorted(set(inteiros))
    dif = sorted({b - a for a, b in zip(u, u[1:])})
    print("menores diferencas entre contagens distintas:", dif[:25])


if __name__ == "__main__":
    main()
