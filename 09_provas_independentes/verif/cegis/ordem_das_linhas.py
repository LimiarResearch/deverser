"""A ordem das linhas do resultados.jsonl bate com uma execucao paralela real?

Hipotese: P processos pegam os casos em ordem de id e cada linha e gravada quando o caso termina. Simula a fila com a duracao
registrada de cada caso (soma dos segundos dos tres metodos, mais uma sobra fixa opcional) e compara a ordem simulada com a gravada.

Uso: python3 -I ordem_das_linhas.py <resultados.jsonl>
"""
import heapq, json, sys
L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
obs = [r["id"] for r in L]
dur = {r["id"]: r["f"]["segundos"] + r["cegis_poda"]["segundos"] + r["cegis"]["segundos"] for r in L}

def simular(P, sobra=0.0):
    livres = [(0.0, w) for w in range(P)]
    heapq.heapify(livres)
    fim = []
    for i in range(192):
        t, w = heapq.heappop(livres)
        tf = t + dur[i] + sobra
        fim.append((tf, i))
        heapq.heappush(livres, (tf, w))
    return [i for _, i in sorted(fim)]

def kendall(a, b):
    pos = {x: k for k, x in enumerate(b)}
    s = [pos[x] for x in a]
    n = len(s); disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            if s[i] > s[j]: disc += 1
    tot = n * (n - 1) // 2
    return 1 - 2 * disc / tot, disc

base = kendall(obs, list(range(192)))
print("ordem gravada x ordem de id: tau=%.3f (pares invertidos %d)" % base)
melhor = None
for P in range(1, 33):
    for sobra in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0):
        sim = simular(P, sobra)
        tau, disc = kendall(obs, sim)
        iguais = sum(1 for a, b in zip(obs, sim) if a == b)
        if melhor is None or tau > melhor[0]:
            melhor = (tau, disc, P, sobra, iguais)
        if sobra == 0.0 and P in (1, 2, 4, 6, 8, 12, 16, 24, 32):
            print("P=%2d sobra=%.2f tau=%.3f invertidos=%d posicoes identicas=%d" % (P, sobra, tau, disc, iguais))
print("melhor ajuste: tau=%.3f invertidos=%d P=%d sobra=%.2f posicoes identicas=%d de 192" % melhor)
print("primeiras 30 linhas gravadas:", obs[:30])
P, sobra = melhor[2], melhor[3]
print("primeiras 30 simuladas      :", simular(P, sobra)[:30])
print("duracao total dos tres metodos: %.1f s" % sum(dur.values()))
