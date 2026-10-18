# -*- coding: utf-8 -*-
"""Confere os registros da conta 15 (so leitura). Uso:
python3 -I conta15_registros.py <pasta 07_conta_15>
Nao importa nem executa nada do repositorio: so le os .log e o .md como texto."""
import os
import re
import sys
import statistics as st

base = sys.argv[1]
reg = os.path.join(base, 'registros')


def ler(n):
    with open(os.path.join(reg, n), encoding='utf-8') as f:
        return f.read()


logs = sorted(os.listdir(reg))
print('== 1. Arquivos de registro:', len(logs))

print('\n== 2. Fim de cada registro, codigo de saida, erros, avisos, carimbos de data/hora')
padrao_data = re.compile(r'(20\d\d[-/.]\d\d[-/.]\d\d|\b\d\d:\d\d(:\d\d)?\b|\b(19|20)\d\d\b)')
for n in logs:
    t = ler(n)
    linhas = t.rstrip('\n').split('\n')
    saida = [l for l in linhas if l.startswith('saida ')]
    n_fim = sum(1 for l in linhas if l.startswith('FIM'))
    erros = [l for l in linhas if re.search(r'Traceback|Error|Erro|Exception|Warning|Killed|interromp', l)]
    datas = [m.group(0) for m in padrao_data.finditer(t)]
    print(f'{n:28s} linhas={len(linhas):3d} FIM={n_fim} {saida} erros/avisos={len(erros)} datas_ou_horas={datas[:5]}')
    for e in erros:
        print('     >>', e.strip()[:200])


def corpo_conta(t):
    """O texto da conta sem o 'saida 0' final."""
    ls = t.rstrip('\n').split('\n')
    if ls and ls[-1].startswith('saida '):
        ls = ls[:-1]
    return ls


print('\n== 3. A conta registrada (arquivo *_conta.log) e o comeco do *_vida.log')
pares = [('p1_conta.log', 'p1_vida.log'), ('p1b_conta.log', 'p1b_vida.log'), ('p2_conta.log', 'p2_vida.log'),
         ('p2b_conta.log', 'p2b_vida.log'), ('p4_conta.log', 'p4_vida.log'), ('p4b_conta.log', 'p4b_vida.log'),
         ('p4c_conta.log', 'p4c_vida.log'), ('p4d_conta.log', 'p4d_vida.log'), ('p4f_conta.log', 'p4f_vida.log')]
for c, v in pares:
    lc = corpo_conta(ler(c))
    lv = ler(v).split('\n')
    sem_fim = lc[:-1] if lc[-1] == 'FIM' else lc
    igual = lv[:len(sem_fim)] == sem_fim
    prox = lv[len(sem_fim)] if len(lv) > len(sem_fim) else None
    print(f'{c:16s} -> {v:16s}: a conta inteira (sem FIM) e o comeco identico da vida = {igual}; linha seguinte na vida: {prox!r}')
# p4e: dois blocos na conta
t = corpo_conta(ler('p4e_conta.log'))
blocos, atual = [], []
for l in t:
    atual.append(l)
    if l == 'FIM':
        blocos.append(atual[:-1])
        atual = []
for i, (b, v) in enumerate(zip(blocos, ['p4e_vida_dp3.log', 'p4e_vida_dp2.log'])):
    lv = ler(v).split('\n')
    print(f"p4e_conta bloco {i + 1} -> {v}: identico ao comeco = {lv[:len(b)] == b}; linha seguinte: {lv[len(b)]!r}")
# p2c: so o cabecalho em comum
for v in ['p2c_vida_sinapse_b.log', 'p2c_diag_b.log', 'p2c_vida_unidade.log', 'p2c_vida_sinapse.log']:
    print(f'{v}: primeira linha = {ler(v).splitlines()[0]!r}; segunda = {ler(v).splitlines()[1]!r}')
print('cabecalhos das contas da 2c:', [ler(n).splitlines()[1] for n in ('p2c_conta_a.log', 'p2c_conta.log')])

print('\n== 4. A conta da orelha (conta_orelha.log)')
t = ler('conta_orelha.log')
rod = re.findall(r'rodada (\d+): de fora (\w+);.*?a previsao da conta.*?acerto ([\d.]+)%.*?a medida em \w+, fora da conta \((\d+) falas\): acerto ([\d.]+)%.*?pela media dos bits ([\d.]+)%.*?pelo Jaccard da V10 ([\d.]+)%', t, re.S)
print('rodadas lidas:', len(rod))
for r in rod:
    print('  ', r)
def media(xs):
    return sum(xs) / len(xs)
todas = [(v, float(p), int(n), float(m), float(b), float(j)) for _, v, p, n, m, b, j in rod]
sint = [x for x in todas if x[0] != 'gabriel']
for nome, conj in (('todas as 12 rodadas (6 vozes)', todas), ('so as 10 das 5 vozes sinteticas', sint)):
    print(f'  {nome}: orelha medida {media([x[3] for x in conj]):.2f}% | prevista {media([x[1] for x in conj]):.2f}% | media dos bits {media([x[4] for x in conj]):.2f}% | Jaccard V10 {media([x[5] for x in conj]):.2f}%')
    tot = sum(x[2] for x in conj)
    print(f'     ponderado pelas falas ({tot}): orelha {sum(x[3] * x[2] for x in conj) / tot:.2f}% | bits {sum(x[4] * x[2] for x in conj) / tot:.2f}% | Jaccard {sum(x[5] * x[2] for x in conj) / tot:.2f}%')
erros_prev = [(x[0], x[1], x[3]) for x in todas]
print('  previsao acima da medida em', sum(1 for _, p, m in erros_prev if p > m), 'rodadas; abaixo em', sum(1 for _, p, m in erros_prev if p < m))

print('\n== 5. Faixas das vidas das palavras')
def vida_so(n):
    t = ler(n)
    m = re.search(r'^A VIDA(,.*)?$', t, re.M)
    return t[m.start():] if m else t
def horas(n, campo):
    linhas = [l for l in vida_so(n).splitlines() if 'h de vida' in l]
    return [int(x) for l in linhas for x in re.findall(campo, l)]
for n in ['p1_vida.log', 'p1b_vida.log', 'p2_vida.log', 'p2b_vida.log', 'p2c_vida_sinapse_b.log', 'p2c_vida_unidade.log', 'p2c_vida_sinapse.log']:
    err = horas(n, r'a unidade errada em (\d+) de 4110')
    hits = horas(n, r'acende a propria unidade em (\d+) de 10')
    m = re.search(r'acendeu a propria unidade antes do acontecimento: (.*)', vida_so(n))
    anun = [int(x) for x in re.findall(r' (-?\d+)', m.group(1))] if m else []
    acima = sum(1 for e in err if e > 93.5)
    print(f'{n:24s} errados por hora {err} -> min {min(err)} max {max(err)} ({100 * min(err) / 4110:.2f}% a {100 * max(err) / 4110:.2f}%); acima de 93,5 (2,3%): {acima} de {len(err)}')
    print(f'{"":24s} acende a propria por hora {hits}; anuncio em que acendeu: {anun} -> {min(anun)} a {max(anun)}')

print('\n== 6. A 2c: a vida com a regra da unidade repete a p2b numero por numero?')
def horarias(n):
    out = []
    for l in ler(n).splitlines():
        m = re.match(r'\s+(\d+) h de vida: a fala nunca ouvida acende a propria unidade em (\d+) de 10 \(as que param: (\w+)\); a unidade errada em (\d+) de 4110;.*?esquecimentos: (\d+) verdadeiros e (\d+) falsos', l)
        if m:
            out.append(m.groups())
    return out
a, b = horarias('p2b_vida.log'), horarias('p2c_vida_unidade.log')
print('  p2b horas:', len(a), ' p2c unidade horas:', len(b), ' identicas:', a == b)
fa = re.search(r'esquecimentos falsos: 18 \((.*)\)', ler('p2b_vida.log')).group(1).replace(' por palavra parecida', '')
fb = re.search(r'esquecimentos falsos: 18 \((.*)\)', ler('p2c_vida_unidade.log')).group(1).replace(' por palavra parecida', '')
print('  lista dos 18 esquecimentos falsos identica (sem a anotacao):', fa == fb)
print('  previsto na conta da 2a forma, regra nova:', re.search(r'regra nova: (\d+) ligacoes', ler('p2c_conta.log')).group(1),
      '| medido na vida da 2a forma:', re.search(r'ligacoes apagadas sem ter mudado: (\d+)', ler('p2c_vida_sinapse_b.log')).group(1),
      '| medido na vida da 3a forma:', re.search(r'ligacoes apagadas sem ter mudado: (\d+)', ler('p2c_vida_sinapse.log')).group(1))
for n in ['p2c_vida_sinapse_b.log', 'p2c_vida_sinapse.log']:
    for m in re.finditer(r'(você|mundo), dita (\d+) vezes sem o acontecimento: acendeu a unidade em (\d+) das 10 primeiras e em (\d+) de todas; a ultima vez que acendeu foi a (\d+)a', ler(n)):
        w, tot, p10, todas_, ult = m.groups()
        tot, p10, todas_ = int(tot), int(p10), int(todas_)
        print(f'  {n}: {w}: {todas_}/{tot} = {100 * todas_ / tot:.1f}% de todas; depois das 10 primeiras {todas_ - p10}/{tot - 10} = {100 * (todas_ - p10) / (tot - 10):.1f}%; ultima a {ult}a')
print('  costume acima do limiar (3a forma):', re.findall(r'o costume acima do limiar na (\w+) metade: ([\d.]+)%', ler('p2c_vida_sinapse.log')))
for n in ['p2c_vida_sinapse_b.log', 'p2c_diag_b.log']:
    pass
la, lb = ler('p2c_vida_sinapse_b.log').splitlines(), ler('p2c_diag_b.log').splitlines()
dif = [(i, x, y) for i, (x, y) in enumerate(zip(la, lb)) if x != y]
print('  p2c_vida_sinapse_b x p2c_diag_b: linhas', len(la), 'e', len(lb), '; diferentes nas linhas comuns:', [(i, x[:60], y[:60]) for i, x, y in dif])

print('\n== 7. Premissas 3 e 4')
def sentimentos(n):
    return {m.group(1): m.group(0) for m in re.finditer(r'\s+(\w+)\s+aceso em\s+([\d.]+)% da vida acordada;\s+(\d+) vezes; cada vez de ([\d.]+) a ([\d.]+) min \(mediana ([\d.]+)\)', ler(n))}
for n in ['p4_vida.log', 'p4b_vida.log', 'p4c_vida.log', 'p4d_vida.log', 'p4e_vida_dp3.log', 'p4e_vida_dp2.log', 'p4f_vida.log']:
    t = vida_so(n)
    print(' ---', n)
    for m in re.finditer(r'\s+(\w+)\s+aceso em\s+([\d.]+)% da vida acordada;\s+(\d+) vezes; cada vez de ([\d.]+) a ([\d.]+) min \(mediana ([\d.]+)\)', t):
        s, pct, vezes, mn, mx, med = m.groups()
        marca = ' <13,5' if float(med) < 13.5 else ''
        print(f'     {s:12s} {pct:>5s}% {vezes:>4s}x  {mn:>6s} a {mx:>6s} min  mediana {med}{marca}')
    est = re.search(r'o estalo acendeu [^:]+: (.*)', t).group(1)
    sim = [x.split()[1] for x in est.split(', ') if x.endswith('sim')]
    print('     estalo sim em:', ' '.join(sim))
    print('    ', re.search(r'esquecimentos pelo teste de Page: (.*)', t).group(0).strip())
    ch = re.findall(r'd(\d) ([\d.]+)h (\d+)%', (re.search(r'antes de cada chegada: (.*)', t) or re.search(r'x', 'x')).group(0)) if 'antes de cada chegada' in t else []
    if not ch:
        ch = [(d, h, p) for d, h, p in re.findall(r'chegada no dia (\d) as\s+([\d.]+) h: a procura acesa em\s+(\d+)%', t)]
    print('     procura antes das chegadas (dia hora %):', [(d, h, int(p)) for d, h, p in ch])
    sa = re.search(r'depois de cada saida: (.*)', t)
    if sa:
        s_ = re.findall(r'd(\d) ([\d.]+)h (\d+)%', sa.group(1))
        nz = [int(p) for _, _, p in s_ if int(p) > 0]
        print(f'     saidas com procura > 0: {len(nz)} de {len(s_)}; faixa {min(nz) if nz else None} a {max(nz) if nz else None}')
    for m in re.finditer(r'(dia \d): (.*)', t):
        print('    ', m.group(1), m.group(2)[:110])
    for k in ('a procura nas outras horas sem Gabriel, acordado', 'a procura no resto do tempo sem Gabriel, acordado', 'o contagio', 'o repassar', 'o narrador'):
        m = re.search(re.escape(k) + r'.*', t)
        if m:
            print('    ', m.group(0)[:160])

print('\n== 8. A p4f: "a espera acendeu em 7 das 10 chegadas de almoco e de noite"')
t = ler('p4f_vida.log')
ch = re.findall(r'd(\d) ([\d.]+)h (\d+)%', re.search(r'antes de cada chegada: (.*)', t).group(1))
alm_noite = [(int(d), float(h), int(p)) for d, h, p in ch if float(h) > 10 and int(d) >= 2]
print('  chegadas de almoco e noite dos dias 2 a 7:', alm_noite, '(', len(alm_noite), ')')
for lim, nome in ((0, '> 0%'), (2, '> 2%'), (49, '>= 50%')):
    print(f'  acesas com {nome}: {sum(1 for _, _, p in alm_noite if p > lim)} de {len(alm_noite)}')
d3 = [x for x in alm_noite if x[0] >= 3]
print('  so a partir do dia 3:', len(d3), 'chegadas; > 0%:', sum(1 for x in d3 if x[2] > 0), '; >= 50%:', sum(1 for x in d3 if x[2] >= 50))

print('\n== 9. Os commits citados no A_CONTA_15.md aparecem em algum arquivo do pacote?')
md = open(os.path.join(base, 'A_CONTA_15.md'), encoding='utf-8').read()
hashes = sorted(set(re.findall(r'`([0-9a-f]{8})`', md)))
print('  hashes citados:', len(hashes), hashes)
raiz = os.path.dirname(base.rstrip('/'))
achados = {h: [] for h in hashes}
for dp, _, fs in os.walk(raiz):
    for f in fs:
        p = os.path.join(dp, f)
        try:
            s = open(p, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        for h in hashes:
            if h in s and not p.endswith('A_CONTA_15.md'):
                achados[h].append(os.path.relpath(p, raiz))
print('  achados fora do A_CONTA_15.md:', {h: v for h, v in achados.items() if v} or 'nenhum')
