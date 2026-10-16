# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
import carga_vida as CV
N = 5
CELULAS = N * N
ACOES = CV.CLASSES
D_OBS = CELULAS + 1 + CV.D_CONTEXTO
T_MAX, T_MAX_COMPOSTA, EPS, GAMA = (10, 20, 0.3, 0.9)
SONDA_A_CADA, INTERROMPER_A_CADA = (100, 800)
EPISODIOS_BASE = (30, 90)
EPISODIOS_COMPOSTA = 15
BASE, PARES, REFUTADAS = (CV.BASE, CV.PARES, CV.REFUTADAS)
MOVIMENTOS = ((-1, 0), (1, 0), (0, -1), (0, 1))

def mover(pos, m, n=N):
    r, c = divmod(int(pos), n)
    dr, dc = MOVIMENTOS[int(m)]
    r2, c2 = (r + dr, c + dc)
    return pos if not (0 <= r2 < n and 0 <= c2 < n) else r2 * n + c2

def d_da_observacao(n=N):
    return n * n + 1 + CV.D_CONTEXTO

def movimentos_otimos(pos, alvo, n=N):
    r, c = divmod(int(pos), n)
    ra, ca = divmod(int(alvo), n)
    out = []
    if r > ra:
        out.append(0)
    if r < ra:
        out.append(1)
    if c > ca:
        out.append(2)
    if c < ca:
        out.append(3)
    return out

def conjunto_otimo(pos, alvo, n=N):
    v = np.zeros(ACOES, bool)
    for m in movimentos_otimos(pos, alvo, n):
        v[m] = True
    return v

def movimento_canonico(pos, alvo, n=N):
    opt = movimentos_otimos(pos, alvo, n)
    return opt[(int(pos) * 7 + int(alvo) * 13) % len(opt)]

def observacao(pos, fase, ctx, r, n=N):
    x = np.zeros(d_da_observacao(n), np.float32)
    x[pos] = 1.0
    x[n * n] = float(fase)
    x[n * n + 1:] = ctx + r.normal(0, CV.CONTEXTO_RUIDO, CV.D_CONTEXTO)
    return x

def credito(ações, sucesso):
    n = len(ações)
    T = np.zeros((n, ACOES), np.float32)
    for s, a in enumerate(ações):
        if sucesso:
            w = GAMA ** (n - 1 - s)
            T[s] = (1.0 - w) / ACOES
            T[s, a] += w
        else:
            T[s] = 1.0 / (ACOES - 1)
            T[s, a] = 0.0
    return T

def rodar_episodio_cpp(aprendiz, spec, ctx, semente_do_episodio):
    r = np.random.default_rng(semente_do_episodio)
    lado = int(spec.get('grade', N))
    tmax = int(spec.get('tmax', T_MAX))
    ruido = np.zeros((tmax, CV.D_CONTEXTO))
    explora = np.zeros(tmax)
    sorteio = np.zeros(tmax, np.int32)
    for t in range(tmax):
        ruido[t] = r.normal(0, CV.CONTEXTO_RUIDO, CV.D_CONTEXTO)
        explora[t], sorteio[t] = (r.random(), int(r.integers(0, ACOES)))
    X, acoes, sucesso = aprendiz.episodio(lado, int(spec['inicio']), [int(x) for x in spec['alvos']], int(spec['rot']), tmax, np.asarray(ctx, np.float64), ruido, explora, sorteio, EPS)
    return (X, credito([int(a) for a in acoes], sucesso), sucesso)

def rodar_episodio(prever, spec, ctx, semente_do_episodio):
    r = np.random.default_rng(semente_do_episodio)
    lado = int(spec.get('grade', N))
    pos, fase, alvos, rot = (int(spec['inicio']), 0, spec['alvos'], int(spec['rot']))
    xs, acoes, sucesso = ([], [], False)
    for _ in range(int(spec.get('tmax', T_MAX))):
        x = observacao(pos, fase, ctx, r, lado)
        a = int(prever(x))
        explora, sorteio = (r.random(), int(r.integers(0, ACOES)))
        if explora < EPS:
            a = sorteio
        xs.append(x)
        acoes.append(a)
        pos = mover(pos, (a - rot) % ACOES, lado)
        if pos == alvos[fase]:
            if fase + 1 < len(alvos):
                fase += 1
            else:
                sucesso = True
                break
    return (np.stack(xs), credito(acoes, sucesso), sucesso)

def _leitor(eventos, registro):
    pos = {'i': 0}
    registro['aberturas'] += 1

    def proximo():
        i = pos['i']
        if i >= len(eventos):
            if i == len(eventos):
                pos['i'] += 1
                registro['completos'] += 1
            return None
        pos['i'] = i + 1
        ev = eventos[i]
        if ev[0] == 'episodio':
            return ('episodio', dict(ev[1]))
        if ev[0] == 'sonda':
            return ('sonda', ev[1].copy())
        return ('interromper',)
    return proximo

def gerar_vida(semente, lado=N):
    celulas = lado * lado
    r = np.random.default_rng(semente)
    rc = np.random.default_rng(semente + 7777)
    alvos = [int(v) for v in r.choice(celulas, BASE + 1, replace=False)]
    CTX = rc.normal(0, CV.CONTEXTO_ESC, (BASE + 1 + len(PARES), CV.D_CONTEXTO))
    ordem = []
    for _ in range(6):
        ordem += list(r.permutation(BASE))
    vistas, ordem2, comp_feitas, ref_feitas = ({}, [], set(), set())
    for k, t in enumerate(ordem):
        ordem2.append(('base', int(t)))
        vistas[int(t)] = vistas.get(int(t), 0) + 1
        for c, (a, b) in enumerate(PARES):
            if c not in comp_feitas and vistas.get(a, 0) >= 2 and (vistas.get(b, 0) >= 2) and (r.random() < 0.5):
                ordem2.append(('composta', c))
                comp_feitas.add(c)
        if k > len(ordem) // 2:
            for t2 in REFUTADAS:
                if t2 not in ref_feitas and r.random() < 0.08:
                    ordem2.append(('refutada', t2))
                    ref_feitas.add(t2)
    ordem2 += [('composta', c) for c in range(len(PARES)) if c not in comp_feitas]
    ordem2 += [('refutada', t) for t in REFUTADAS if t not in ref_feitas]
    ordem2.append(('nova', BASE))
    eventos, segmentos, tarefa_do_episodio, refutada_desde, gira = ([], [], [], {}, {})
    for tipo, t in ordem2:
        n = EPISODIOS_COMPOSTA if tipo == 'composta' else int(r.integers(*EPISODIOS_BASE))
        if tipo == 'composta':
            a, b = PARES[t]
            ident, codigo, alvos_t = (BASE + 1 + t, BASE + 1 + t, (alvos[a], alvos[b]))
            rot = 0
        elif tipo == 'nova':
            ident, codigo, alvos_t, rot = (BASE, BASE, (alvos[BASE],), 0)
        else:
            ident, codigo, alvos_t = (t, t, (alvos[t],))
            if tipo == 'refutada':
                gira[t] = True
                refutada_desde[t] = len(tarefa_do_episodio)
            rot = 1 if gira.get(t, False) else 0
        for _ in range(n):
            inicio = int(r.integers(0, celulas))
            if inicio == alvos_t[0]:
                inicio = (inicio + 1) % celulas
            spec = {'alvos': alvos_t, 'rot': rot, 'inicio': inicio, 'codigo': int(codigo), 'tarefa': int(ident), 'tmax': T_MAX_COMPOSTA if len(alvos_t) == 2 else T_MAX, 'semente': int(r.integers(0, 2 ** 31 - 1))}
            if lado != N:
                spec['grade'] = lado
            eventos.append(('episodio', spec))
            tarefa_do_episodio.append(ident)
            if len(tarefa_do_episodio) % INTERROMPER_A_CADA == 0:
                eventos.append(('interromper',))
        segmentos.append((tipo, t, n))
    return _fechar(eventos, segmentos, np.asarray(tarefa_do_episodio), refutada_desde, alvos, CTX, semente, lado)

def _fechar(eventos, segmentos, tarefa, refutada_desde, alvos, CTX, semente, lado=N):
    rc = np.random.default_rng(semente + 9999)
    celulas = lado * lado
    linhas_x, ts, conj, canon = ([], [], [], [])
    for t in range(BASE):
        for cel in range(celulas):
            if cel != alvos[t]:
                linhas_x.append(observacao(cel, 0, CTX[t], rc, lado))
                ts.append(t)
                conj.append(conjunto_otimo(cel, alvos[t], lado))
                canon.append(movimento_canonico(cel, alvos[t], lado))
    for c, (a, b) in enumerate(PARES):
        for fase, alvo in ((0, alvos[a]), (1, alvos[b])):
            for cel in range(celulas):
                if cel != alvo:
                    linhas_x.append(observacao(cel, fase, CTX[BASE + 1 + c], rc, lado))
                    ts.append(BASE + 1 + c)
                    conj.append(conjunto_otimo(cel, alvo, lado))
                    canon.append(movimento_canonico(cel, alvo, lado))
    for cel in range(celulas):
        if cel != alvos[BASE]:
            linhas_x.append(observacao(cel, 0, CTX[BASE], rc, lado))
            ts.append(BASE)
            conj.append(conjunto_otimo(cel, alvos[BASE], lado))
            canon.append(movimento_canonico(cel, alvos[BASE], lado))
    X_sonda, ts, conj, canon = (np.stack(linhas_x), np.asarray(ts), np.stack(conj), np.asarray(canon, np.int64))
    emb = rc.permutation(len(ts))
    X_sonda, ts, conj, canon = (X_sonda[emb], ts[emb], conj[emb], canon[emb])
    saida, sondas_em, verdade, rot_sonda, interr_em, n_ep = ([], [], [], [], [], 0)
    N_TOTAL = len(tarefa)
    for ev in eventos:
        saida.append(ev)
        if ev[0] == 'interromper':
            interr_em.append(n_ep - 1)
            continue
        n_ep += 1
        if n_ep % SONDA_A_CADA == 0 or n_ep == N_TOTAL:
            saida.append(('sonda', X_sonda))
            sondas_em.append(n_ep - 1)
            rot = np.zeros(len(ts), np.int64)
            for t, desde in refutada_desde.items():
                if n_ep - 1 >= desde:
                    rot[ts == t] = 1
            rot_sonda.append(rot)
            verdade.append((canon + rot) % ACOES)
    if saida and saida[-1][0] == 'interromper':
        saida.pop()
        interr_em.pop()
    inicio = {int(t): int(np.flatnonzero(tarefa == t)[0]) for t in np.unique(tarefa)}
    maj = {int(t): float(np.bincount(canon[ts == t], minlength=ACOES).max() / int((ts == t).sum())) for t in np.unique(ts)}
    av = {'tarefa_sonda': ts, 'verdade': np.array(verdade, np.int64), 'sondas_em': sondas_em, 'interromper_em': interr_em, 'tarefa': tarefa, 'inicio': inicio, 'majoritaria': maj, 'refutada_desde': refutada_desde, 'segmentos': segmentos, 'base': BASE, 'compostas': [BASE + 1 + c for c in range(len(PARES))], 'conj': conj, 'rot_por_sonda': np.array(rot_sonda, np.int64), 'alvos': alvos, 'CTX': CTX, 'X_sonda': X_sonda, 'ref_nova': None, 'ref_composta': {}, 'grade': lado}
    registro = {'aberturas': 0, 'completos': 0}
    av['registro'] = registro
    return {'abrir': lambda: _leitor(saida, registro), '_avaliacao': av, 'tipo': 'age'}

class AgenteFresco:

    def __init__(self, d, c, r, oculta=64, lr=0.05):
        self.lr = lr
        self.W1 = r.normal(0, 1 / np.sqrt(d), (d, oculta)).astype(np.float32)
        self.b1 = np.zeros(oculta, np.float32)
        self.W2 = r.normal(0, 1 / np.sqrt(oculta), (oculta, c)).astype(np.float32)
        self.b2 = np.zeros(c, np.float32)

    def aprender_varios(self, X, T):
        for x, t in zip(X, T):
            h = np.maximum(0, x @ self.W1 + self.b1)
            z = h @ self.W2 + self.b2
            p = np.exp(z - z.max())
            p /= p.sum()
            g = p - t
            gh = self.W2 @ g * (h > 0)
            self.W2 -= self.lr * np.outer(h, g)
            self.b2 -= self.lr * g
            self.W1 -= self.lr * np.outer(x, gh)
            self.b1 -= self.lr * gh

    def prever(self, X):
        z = np.maximum(0, np.asarray(X, np.float32) @ self.W1 + self.b1) @ self.W2 + self.b2
        return (np.argmax(z, axis=1), np.zeros(len(z), np.int8))

def ajustar_respostas(av, resp):
    conj, rot, V = (av['conj'], av['rot_por_sonda'], av['verdade'])
    out = []
    for j, R in enumerate(resp):
        R = np.asarray(R, np.int64)
        base = (R - rot[j]) % ACOES
        no_conjunto = conj[np.arange(len(R)), base]
        out.append(np.where(no_conjunto, V[j], R).astype(np.int8))
    return out

def _acerto_do_fresco(av, tarefa_ids, n_episodios, tipo, codigo, alvos, rot, semente, inits=3):
    lado = int(av.get('grade', N))
    celulas = lado * lado
    'O acerto de um agente fresco, treinado só em `n_episodios` episódios da tarefa, nas linhas de sonda de `tarefa_ids` (no instante final da vida).'
    ts = av['tarefa_sonda']
    m = np.isin(ts, tarefa_ids)
    Xs, V_fim = (av['X_sonda'][m], av['verdade'][-1][m])
    conj = av['conj'][m]
    accs = []
    for j in range(inits):
        r = np.random.default_rng(semente + 11 * j)
        a = AgenteFresco(d_da_observacao(lado), ACOES, r)
        er = np.random.default_rng(semente + 101 * j)
        for e in range(n_episodios):
            ini = int(er.integers(0, celulas))
            spec = {'alvos': alvos, 'rot': rot, 'inicio': (ini + 1) % celulas if ini == alvos[0] else ini, 'codigo': codigo, 'tmax': T_MAX_COMPOSTA if len(alvos) == 2 else T_MAX}
            if lado != N:
                spec['grade'] = lado
            X, T, _ = rodar_episodio(lambda x: a.prever(x[None, :])[0][0], spec, av['CTX'][codigo], int(er.integers(0, 2 ** 31 - 1)))
            a.aprender_varios(X, T)
        p = a.prever(Xs)[0]
        rot_f = av['rot_por_sonda'][-1][m]
        base = (p - rot_f) % ACOES
        certo = conj[np.arange(len(p)), base]
        accs.append(float(np.mean(certo)))
    return float(np.mean(accs))

def gerar_carga(semente, fluxos=2, lado=N):
    vidas = [gerar_vida(1000 * semente + 53 * k + 5, lado) for k in range(fluxos)]
    for k, v in enumerate(vidas):
        av = v['_avaliacao']
        seg = av['segmentos']
        n_nova = next((n for tipo, t, n in seg if tipo == 'nova'))
        av['ref_nova'] = _acerto_do_fresco(av, [BASE], n_nova, 'nova', BASE, (av['alvos'][BASE],), 0, 1000 * semente + k)
        for c, (a, b) in enumerate(PARES):
            av['ref_composta'][BASE + 1 + c] = _acerto_do_fresco(av, [BASE + 1 + c], EPISODIOS_COMPOSTA, 'composta', BASE + 1 + c, (av['alvos'][a], av['alvos'][b]), 0, 1000 * semente + k + 17 * c)
        v['_avaliacao'] = CV._Cofre(av)
    return {'fluxos': vidas, 'classes': ACOES, 'd_entrada': d_da_observacao(lado), 'orcamento_bytes': 65536}

def _entregar(aprendiz, X, T):
    if hasattr(aprendiz, 'aprender_varios'):
        aprendiz.aprender_varios(X, T)
    else:
        for x, t in zip(X, T):
            aprendiz.aprender(x, t)

def rodar_agentes(entrada, fabrica, restaurar):
    from experimentos import desafio_memoria as MEM
    out = {'respostas': [], 'etiquetas': [], 'bytes_por_interrupcao': [], 'restauracao_fiel': [], 'diagnostico': [], 'memoria': [], 'copias': [], 'tamanho_logico': [], 'flops': [], 'sucessos': []}
    d, c = (entrada['d_entrada'], entrada['classes'])
    for k, f in enumerate(entrada['fluxos']):
        CTX = f['_avaliacao'].abrir()['CTX']
        a = fabrica(d, c, np.random.default_rng(100 + k))
        sombra = None
        ler, resp, etq, bts, fiel, tam, flo, suc = (f['abrir'](), [], [], [], [], [], [], [])
        while True:
            ev = ler()
            if ev is None:
                break
            if ev[0] == 'episodio':
                spec = ev[1]
                atual = a
                if hasattr(atual, 'episodio') and (not os.environ.get('AGENTES_SEM_CPP')):
                    X, T, ok = rodar_episodio_cpp(atual, spec, CTX[spec['codigo']], spec['semente'])
                else:
                    X, T, ok = rodar_episodio(lambda x: atual.prever(x[None, :])[0][0], spec, CTX[spec['codigo']], spec['semente'])
                suc.append(bool(ok))
                _entregar(a, X, T)
                if sombra is not None:
                    _entregar(sombra, X.copy(), T.copy())
            elif ev[0] == 'sonda':
                p, e = a.prever(ev[1])
                if sombra is not None:
                    ps, es = sombra.prever(ev[1])
                    fiel.append(bool(np.array_equal(np.asarray(p), np.asarray(ps)) and np.array_equal(np.asarray(e), np.asarray(es))))
                    sombra = None
                resp.append(np.asarray(p, np.int8))
                etq.append(np.asarray(e, np.int8))
            else:
                b = a.estado()
                bts.append(len(b))
                tensores, _ = MEM.tensores_do_estado(b)
                tam.append(int(sum((t.nbytes for t in tensores))))
                fl = getattr(a, 'flops_por_interacao', None)
                if fl is not None and fl() is not None:
                    flo.append(float(fl()))
                sombra = a
                a = restaurar(b, d, c)
        out['respostas'].append(resp)
        out['etiquetas'].append(etq)
        out['bytes_por_interrupcao'].append(bts)
        out['restauracao_fiel'].append(fiel)
        out['memoria'].append([])
        out['copias'].append([])
        out['tamanho_logico'].append(tam)
        out['flops'].append(flo)
        out['sucessos'].append(suc)
        if hasattr(a, 'diagnostico'):
            out['diagnostico'].append(a.diagnostico())
    return out
