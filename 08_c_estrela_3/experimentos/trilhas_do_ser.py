# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
import carga_vida as CV
CLASSES = CV.CLASSES
ACASO = 1.0 / CLASSES
D_BASE, D_CONTEXTO, CONTEXTO_ESC, CONTEXTO_RUIDO = (CV.D_ENTRADA, CV.D_CONTEXTO, CV.CONTEXTO_ESC, CV.CONTEXTO_RUIDO)
LINHAS = 256
GRADE = (10, 20, 35, 55, 80, 115, 160, 230, 320, 450)
N_BLOCO = GRADE[-1]
GRADE_COMPOSTA, N_COMPOSTA = ((0, 8, 32, 150), 150)
GRADE_VOLTA, N_VOLTA = ((0, 5, 10, 20, 40, 100), 100)
PARES_COMP, TAREFAS_FAM, TAREFAS_REG = (10, 12, 24)
VOLTAS_REG = (4, 8, 12, 16)
INTERROMPER_A_CADA = CV.INTERROMPER_A_CADA
FRACAO_DO_NIVEL = 0.9
DERIVA_TOTAL, DERIVA_GIRO, DERIVA_SONDA_A_CADA, DERIVA_JANELA = (12000, 6000, 500, 1500)

def _professor(r, compartilhado=None, mu=None):
    if compartilhado is None:
        return CV._prof(r, mu=mu)
    return {'W1': compartilhado['W1'], 'b1': compartilhado['b1'], 'W2': r.normal(0, 1.0, (CV.OCULTA_PROF, CLASSES)), 'b2': r.normal(0, 0.7, CLASSES), 'mu': r.normal(0, 0.8, D_BASE) if mu is None else mu}

def _estrutura(r):
    esc = r.uniform(0.8, 1.6)
    return {'W1': r.normal(0, esc, (D_BASE, CV.OCULTA_PROF)), 'b1': r.normal(0, 0.3, CV.OCULTA_PROF)}

class _Construtor:

    def __init__(self, semente):
        self.r = np.random.default_rng(semente)
        self.rc = np.random.default_rng(semente + 7777)
        self.eventos, self.N = ([], 0)
        self.sondas_em, self.verdade, self.linhas, self.interr = ([], [], [], [])
        self.blocos = []

    def contexto(self, codigo, n):
        return (self.ctx[codigo][None, :] + self.rc.normal(0, CONTEXTO_RUIDO, (n, D_CONTEXTO))).astype(np.float32)

    def treino(self, x, y):
        for i in range(len(y)):
            self.eventos.append(('treino', x[i], int(y[i])))
            self.N += 1
            if self.N % INTERROMPER_A_CADA == 0:
                self.eventos.append(('interromper',))
                self.interr.append(self.N - 1)

    def sonda(self, X, y):
        self.eventos.append(('sonda', X))
        self.sondas_em.append(self.N - 1)
        self.verdade.append(np.asarray(y, np.int64))
        self.linhas.append(len(y))

    def fechar(self):
        if self.eventos and self.eventos[-1][0] == 'interromper':
            self.eventos.pop()
            self.interr.pop()

def _bloco(c, tarefa_id, papel, x_fun, y_fun, codigo, n, grade, extra=None):
    Xt_base = x_fun(LINHAS)
    yt = y_fun(Xt_base)
    Xt = np.hstack([Xt_base, c.contexto(codigo, LINHAS)]).astype(np.float32)
    xs = x_fun(n)
    ys = y_fun(xs).astype(np.int64)
    xs = np.hstack([xs, c.contexto(codigo, n)]).astype(np.float32)
    ini, feitos = (c.N, 0)
    sondas = []
    for g in grade:
        if g > feitos:
            c.treino(xs[feitos:g], ys[feitos:g])
            feitos = g
        sondas.append(len(c.sondas_em))
        c.sonda(Xt, yt)
    if feitos < n:
        c.treino(xs[feitos:], ys[feitos:])
    b = {'id': len(c.blocos), 'tarefa': tarefa_id, 'papel': papel, 'n': int(n), 'ini': int(ini), 'grade': list(grade), 'sondas': sondas, 'codigo': int(codigo), 'X': Xt, 'y': yt, 'x_treino': xs, 'y_treino': ys}
    if extra:
        b.update(extra)
    c.blocos.append(b)
    return b

def _fresco_curva(x, y, xt, yt, grade, semente, oculta=64, lr=0.05):
    r = np.random.default_rng(semente)
    W1 = r.normal(0, 1 / np.sqrt(x.shape[1]), (x.shape[1], oculta)).astype(np.float32)
    b1 = np.zeros(oculta, np.float32)
    W2 = r.normal(0, 1 / np.sqrt(oculta), (oculta, CLASSES)).astype(np.float32)
    b2 = np.zeros(CLASSES, np.float32)
    out, feito = ([], 0)
    for g in grade:
        for i in range(feito, g):
            h = np.maximum(0, x[i] @ W1 + b1)
            z = h @ W2 + b2
            p = np.exp(z - z.max())
            p /= p.sum()
            gz = p.copy()
            gz[y[i]] -= 1
            gh = W2 @ gz * (h > 0)
            W2 -= lr * np.outer(h, gz)
            b2 -= lr * gz
            W1 -= lr * np.outer(x[i], gh)
            b1 -= lr * gh
        feito = g
        out.append(float(np.mean(np.argmax(np.maximum(0, xt @ W1 + b1) @ W2 + b2, axis=1) == yt)))
    return out

def _fresco_medio(b, semente, inits=3):
    return list(np.mean([_fresco_curva(b['x_treino'], b['y_treino'], b['X'], b['y'], b['grade'], semente + 11 * j) for j in range(inits)], axis=0))

def _embrulhar(c, tipo, extra=None):
    c.fechar()
    registro = {'aberturas': 0, 'completos': 0}
    blocos = [{k: v for k, v in b.items() if k not in ('x_treino', 'y_treino')} for b in c.blocos]
    av = {'tipo': tipo, 'blocos': blocos, 'sondas_em': list(c.sondas_em), 'verdade': list(c.verdade), 'linhas': list(c.linhas), 'interromper_em': list(c.interr), 'registro': registro, 'total': int(c.N)}
    if extra:
        av.update(extra)
    eventos = c.eventos
    return {'abrir': lambda: CV._leitor(eventos, registro), '_avaliacao': CV._Cofre(av), 'tipo': tipo}

def _codigos(c, n):
    c.ctx = c.rc.normal(0, CONTEXTO_ESC, (n, D_CONTEXTO))

def trilha_comp(semente):
    c = _Construtor(semente)
    _codigos(c, 3 * PARES_COMP)
    for k in range(PARES_COMP):
        a = _professor(c.r)
        b = _professor(c.r, mu=a['mu'])
        ca, cb, cc = (3 * k, 3 * k + 1, 3 * k + 2)
        xf = lambda p: lambda n: CV._x(p, c.r, n)
        for prof, cod, n in ((a, ca, 600), (b, cb, 600), (a, ca, 300), (b, cb, 300)):
            x = CV._x(prof, c.r, n)
            y = CV._rot(prof, x)
            c.treino(np.hstack([x, c.contexto(cod, n)]).astype(np.float32), y)
        comp = lambda x: (CV._rot(a, x) + CV._rot(b, x)) % CLASSES
        _bloco(c, cc, 'composta', xf(a), comp, cc, N_COMPOSTA, GRADE_COMPOSTA, {'par': k})
    vida = _embrulhar(c, 'comp')
    semente_f = semente + 401
    for bl, b in zip(vida['_avaliacao'].abrir()['blocos'], c.blocos):
        bl['fresco'] = _fresco_medio(b, semente_f + 17 * bl['id'])
    return vida

def _referencias_frescas(vida, c, semente):
    for bl, b in zip(vida['_avaliacao'].abrir()['blocos'], c.blocos):
        if b['papel'] == 'nova':
            bl['fresco'] = _fresco_medio(b, semente + 401 + 17 * bl['id'])

def trilha_fam(semente):
    c = _Construtor(semente)
    _codigos(c, TAREFAS_FAM)
    est = _estrutura(c.r)
    for i in range(TAREFAS_FAM):
        p = _professor(c.r, compartilhado=est)
        _bloco(c, i, 'nova', (lambda p: lambda n: CV._x(p, c.r, n))(p), (lambda p: lambda x: CV._rot(p, x))(p), i, N_BLOCO, GRADE)
    vida = _embrulhar(c, 'fam')
    _referencias_frescas(vida, c, semente)
    return vida

def trilha_reg(semente):
    c = _Construtor(semente)
    _codigos(c, TAREFAS_REG)
    profs = []
    for i in range(TAREFAS_REG):
        p = _professor(c.r)
        profs.append(p)
        _bloco(c, i, 'nova', (lambda p: lambda n: CV._x(p, c.r, n))(p), (lambda p: lambda x: CV._rot(p, x))(p), i, N_BLOCO, GRADE)
    for i in VOLTAS_REG:
        p = profs[i]
        _bloco(c, i, 'volta', (lambda p: lambda n: CV._x(p, c.r, n))(p), (lambda p: lambda x: CV._rot(p, x))(p), i, N_VOLTA, GRADE_VOLTA, {'primeira': i})
    vida = _embrulhar(c, 'reg')
    _referencias_frescas(vida, c, semente)
    return vida

def _rot_girada(A, B, b1, W2, b2, theta, x):
    W1 = np.cos(theta) * A + np.sin(theta) * B
    return np.argmax(np.tanh(x @ W1 + b1) @ W2 + b2, axis=1)

def trilha_der(semente):
    c = _Construtor(semente)
    _codigos(c, 1)
    esc = c.r.uniform(0.8, 1.6)
    A, B = (c.r.normal(0, esc, (D_BASE, CV.OCULTA_PROF)), c.r.normal(0, esc, (D_BASE, CV.OCULTA_PROF)))
    b1, W2, b2 = (c.r.normal(0, 0.3, CV.OCULTA_PROF), c.r.normal(0, 1.0, (CV.OCULTA_PROF, CLASSES)), c.r.normal(0, 0.7, CLASSES))
    mu = c.r.normal(0, 0.8, D_BASE)
    x = (c.r.normal(0, 1, (DERIVA_TOTAL, D_BASE)) + mu).astype(np.float32)
    theta = np.pi / 2 * np.arange(DERIVA_TOTAL) / DERIVA_GIRO
    y = np.empty(DERIVA_TOTAL, np.int64)
    for i in range(0, DERIVA_TOTAL, 250):
        sl = slice(i, i + 250)
        y[sl] = [int(_rot_girada(A, B, b1, W2, b2, theta[k], x[k][None, :])[0]) for k in range(i, min(i + 250, DERIVA_TOTAL))]
    xc = np.hstack([x, c.contexto(0, DERIVA_TOTAL)]).astype(np.float32)
    Xt_base = (c.r.normal(0, 1, (LINHAS, D_BASE)) + mu).astype(np.float32)
    Xt = np.hstack([Xt_base, c.contexto(0, LINHAS)]).astype(np.float32)
    feitos = 0
    for fim in range(DERIVA_SONDA_A_CADA, DERIVA_TOTAL + 1, DERIVA_SONDA_A_CADA):
        c.treino(xc[feitos:fim], y[feitos:fim])
        feitos = fim
        th = theta[fim - 1]
        c.sonda(Xt, _rot_girada(A, B, b1, W2, b2, th, Xt_base))
    return _embrulhar(c, 'der', {'x_treino': xc, 'y_treino': y.astype(np.int64), 'janela': DERIVA_JANELA, 'X_sonda': Xt})
TRILHAS = {'comp': trilha_comp, 'fam': trilha_fam, 'reg': trilha_reg, 'der': trilha_der}

def gerar_trilhas(semente, tipos=('comp', 'fam', 'reg', 'der'), fluxos=2):
    vidas = []
    for t in tipos:
        for k in range(1 if t == 'der' else fluxos):
            vidas.append(TRILHAS[t](1000 * semente + 37 * k + {'comp': 1, 'fam': 2, 'reg': 3, 'der': 4}[t]))
    return {'fluxos': vidas, 'classes': CLASSES, 'd_entrada': D_BASE + D_CONTEXTO, 'orcamento_bytes': 65536}

def exemplos_ate(curva, grade, nivel=None, fracao=FRACAO_DO_NIVEL):
    curva = np.asarray(curva, float)
    if nivel is None:
        nivel = float(np.mean(curva[-2:]))
    alvo = fracao * nivel
    g = np.asarray(grade, float)
    for i, v in enumerate(curva):
        if v >= alvo:
            if i == 0:
                return float(g[0])
            v0 = curva[i - 1]
            return float(g[i - 1] + (g[i] - g[i - 1]) * (alvo - v0) / max(v - v0, 1e-09))
    return float(g[-1])

def curva_do_bloco(av, resp, b):
    V = av['verdade']
    return [float(np.mean(np.asarray(resp[j]) == V[j])) for j in b['sondas']]

def ganho_sobre_o_fresco(av, resp, b):
    return float(np.mean(np.asarray(curva_do_bloco(av, resp, b), float) - np.asarray(b['fresco'], float)))

def oraculo_da_deriva(vida, largura=128, epocas=8, epocas_inicio=40, lote=256, lr=0.003, wd=0.003, conjunto=3, semente=0):
    from experimentos import desafio_oraculo as OR
    av = vida['_avaliacao'].abrir()
    x, y = (np.asarray(av['x_treino'], np.float32), np.asarray(av['y_treino'], np.int64))
    V, pos, W = (av['verdade'], av['sondas_em'], int(av['janela']))
    Xs = np.asarray(av['X_sonda'], np.float32)
    d = x.shape[1]
    redes = [OR._Mlp(d, CLASSES, largura, 1000 + 97 * semente + 13 * e) for e in range(conjunto)]
    gs = [np.random.default_rng(2000 + 97 * semente + 13 * e) for e in range(conjunto)]
    O = np.full((len(pos), 1), np.nan, np.float32)
    for j, p in enumerate(pos):
        ii = np.arange(max(0, p + 1 - W), p + 1)
        mu, sd = (x[ii].mean(0), x[ii].std(0) + 1e-06)
        xn, Xn = ((x[ii] - mu) / sd, (Xs - mu) / sd)
        for net, g in zip(redes, gs):
            for _ in range(epocas_inicio if j == 0 else epocas):
                ordem = g.permutation(len(ii))
                for k in range(0, len(ordem), lote):
                    b = ordem[k:k + lote]
                    net.passo(xn[b], y[ii][b], lr, wd)
        O[j, 0] = float(np.mean(np.argmax(sum((net.probs(Xn) for net in redes)), 1) == V[j]))
    return {'O': O, 'tarefas': np.asarray([0]), 'pos': np.asarray(pos), 'G': np.zeros((len(pos), 1), np.int8)}

def medir_trilha(av, resp, orac=None):
    tipo = av['tipo']
    blocos = av['blocos']
    out = {}
    if tipo == 'comp':
        ganhos = {k: [] for k in GRADE_COMPOSTA}
        for b in blocos:
            cur = curva_do_bloco(av, resp, b)
            for i, k in enumerate(b['grade']):
                ganhos[k].append(cur[i] - b['fresco'][i])
        for k in GRADE_COMPOSTA:
            out[f'compoe_{k}'] = float(np.mean(ganhos[k]))
    elif tipo == 'fam':
        ganhos = [ganho_sobre_o_fresco(av, resp, b) for b in blocos]
        out['ganho_por_tarefa'] = ganhos
        out['exemplos_ate_0_9'] = [exemplos_ate(curva_do_bloco(av, resp, b), b['grade']) for b in blocos]
        out['melhora_com_o_uso'] = float(np.mean(ganhos[-3:]) - np.mean(ganhos[:3]))
    elif tipo == 'reg':
        novas = [b for b in blocos if b['papel'] == 'nova']
        ganhos = [ganho_sobre_o_fresco(av, resp, b) for b in novas]
        out['ganho_por_tarefa'] = ganhos
        out['exemplos_ate_0_9'] = [exemplos_ate(curva_do_bloco(av, resp, b), b['grade']) for b in novas]
        out['latencia_de_adaptacao'] = float(np.mean(ganhos[:6]) - np.mean(ganhos[-6:]))
        soma_volta, soma_primeira = (0.0, 0.0)
        for b in blocos:
            if b['papel'] != 'volta':
                continue
            p = novas[b['primeira']]
            cur_p = curva_do_bloco(av, resp, p)
            nivel_saida = float(cur_p[-1])
            margem = 2.0 * float(np.sqrt(2.0 * nivel_saida * (1.0 - nivel_saida) / LINHAS))
            ref = max(nivel_saida - margem, 0.0)
            e_primeira = exemplos_ate(cur_p, p['grade'], nivel=nivel_saida)
            cur_v = curva_do_bloco(av, resp, b)
            e_volta = 0.0 if cur_v[0] >= FRACAO_DO_NIVEL * ref else exemplos_ate(cur_v, b['grade'], nivel=ref)
            soma_volta += e_volta
            soma_primeira += e_primeira
        out['custo_da_volta'] = float(soma_volta / max(soma_primeira, 1.0)) if soma_primeira or soma_volta else 0.0
    elif tipo == 'der':
        from experimentos import desafio_oraculo as OR
        V = av['verdade']
        A = np.array([[float(np.mean(np.asarray(resp[j]) == V[j]))] for j in range(len(V))], np.float32)
        d = OR.deficit(A, orac, orac['G'])
        out['deficit_de_deriva'] = float(d[0]) if np.isfinite(d[0]) else 0.0
    return out

def _responder(r, V, p):
    p = float(np.clip(p, 0.0, 1.0))
    certo = r.random(len(V)) < p
    return np.where(certo, V, (V + r.integers(1, CLASSES, len(V))) % CLASSES).astype(np.int8)

def simular_trilha(entrada, ganho=0.25, melhora=0.0, perda=0.0, retem=1.0, tau_volta=15.0, deficit=0.0, orac=None, semente=1):
    out = {'respostas': [], 'etiquetas': [], 'bytes_por_interrupcao': [], 'restauracao_fiel': [], 'diagnostico': []}
    n_der = 0
    for k, f in enumerate(entrada['fluxos']):
        av = f['_avaliacao'].abrir()
        r = np.random.default_rng(1000 * int(semente) + k)
        tipo, V = (av['tipo'], av['verdade'])
        resp = [None] * len(V)
        if tipo == 'comp':
            for b in av['blocos']:
                for i, j in enumerate(b['sondas']):
                    resp[j] = _responder(r, V[j], b['fresco'][i] + ganho)
        elif tipo in ('fam', 'reg'):
            niveis = {}
            novas = [b for b in av['blocos'] if b['papel'] == 'nova']
            for b in novas:
                i = novas.index(b)
                extra = (melhora if tipo == 'fam' else -perda) * i / max(len(novas) - 1, 1)
                niveis[b['id']] = float(np.clip(b['fresco'][-1] + extra, 0.0, 1.0))
                for g, j, fr in zip(b['grade'], b['sondas'], b['fresco']):
                    resp[j] = _responder(r, V[j], fr + extra)
            for b in av['blocos']:
                if b['papel'] != 'volta':
                    continue
                nivel = niveis[b['primeira']]
                a0 = ACASO + retem * (nivel - ACASO)
                for g, j in zip(b['grade'], b['sondas']):
                    resp[j] = _responder(r, V[j], a0 + (nivel - a0) * (1.0 - np.exp(-g / max(tau_volta, 1e-09))))
        elif tipo == 'der':
            O = orac[n_der]['O'][:, 0]
            for j in range(len(V)):
                resp[j] = _responder(r, V[j], O[j] - deficit * (O[j] - ACASO))
            n_der += 1
        out['respostas'].append(resp)
        out['etiquetas'].append([np.zeros(len(v), np.int8) for v in V])
        out['bytes_por_interrupcao'].append([1000] * len(av['interromper_em']))
        out['restauracao_fiel'].append([True] * len(av['interromper_em']))
    return out

def conferir_trilha(entrada, saida):
    if any((f['_avaliacao'].lido for f in entrada['fluxos'])):
        return (False, 'o candidato leu a parte de avaliação')
    for k in ('respostas', 'etiquetas', 'bytes_por_interrupcao', 'restauracao_fiel'):
        if len(saida.get(k, [])) != len(entrada['fluxos']):
            return (False, f'{k}: um por fluxo')
    for f, resp, etq, bts in zip(entrada['fluxos'], saida['respostas'], saida['etiquetas'], saida['bytes_por_interrupcao']):
        av = f['_avaliacao'].abrir()
        reg = av['registro']
        if reg['aberturas'] < 1 or reg['completos'] != reg['aberturas']:
            return (False, 'a vida não foi lida de ponta a ponta em cada abertura')
        if len(resp) != len(av['linhas']) or len(etq) != len(av['linhas']):
            return (False, 'uma resposta e uma etiqueta por sonda')
        if len(bts) != len(av['interromper_em']):
            return (False, 'um estado em bytes por interrupção')
        for r, e, n in zip(resp, etq, av['linhas']):
            r, e = (np.asarray(r), np.asarray(e))
            if r.shape != (n,) or e.shape != (n,) or r.min() < 0 or (r.max() >= entrada['classes']) or (e.min() < 0) or (e.max() > 3):
                return (False, 'resposta ou etiqueta fora da forma')
    return (True, 'ok')
