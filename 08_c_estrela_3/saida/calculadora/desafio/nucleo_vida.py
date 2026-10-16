# -*- coding: utf-8 -*-
class _A:
    PARAMS = ('oculta', 'K', 'w', 'limiar', 'detector', 'marco', 'fusao', 'desempate', 'refutacao', 'combinador', 'auditoria', 'epistemico', 'lr')

    def __init__(s, d, c, r, **p):
        s.d, s.c, s.r = (d, c, r)
        s.p = dict(p)
        s.oc, s.K, s.w, s.lim, s.lr0 = (int(p['oculta']), int(p['K']), int(p['w']), float(p['limiar']), float(p['lr']))
        s.ock = [int(v) for v in p.get('ocultas') or [s.oc] * s.K]
        s.lr0k = np.array(p.get('lrs') or [s.lr0] * len(s.ock), np.float32)
        s.K = len(s.ock)
        s.dets = p.get('detectores') or [{'tipo': p['detector'], 'limiar': s.lim, 'cusum_k': float(p['cusum_k'])}]
        K, w = (s.K, s.w)
        s.E = [None] * K
        s.mu, s.var = (np.zeros((K, d), np.float32), np.ones((K, d), np.float32))
        s.n, s.erro, s.uso = (np.zeros(K, np.float32), np.full(K, 0.5, np.float32), np.zeros(K, np.float32))
        s.lrk, s.conflito_ate, s.erro_lento = (s.lr0k.copy(), np.zeros(K, np.float32), np.full(K, 0.5, np.float32))
        s.T = np.zeros((K, 16, c), np.float32)
        s.par = np.full((K, 2), -1, np.int64)
        s.erro_comb = np.full(K, 1.0, np.float32)
        s.JX, s.JY, s.JA = (np.zeros((w, d), np.float32), np.zeros(w, np.float32), np.zeros(w, np.float32))
        s.j, s.cheia, s.t, s.atual, s.S = (0, 0, 0, -1, np.zeros(len(s.dets)))
        s.marcos = []
        s.diag = {'trocas': 0, 'abertas': 0, 'reconhecidas': 0, 'voltas_ao_marco': 0, 'fusoes': 0, 'correcoes': 0, 'combinacoes': 0, 'ajustes_da_auditoria': 0}

    def _abrir(s):
        livres = [k for k in range(s.K) if s.E[k] is None]
        k = livres[0] if livres else int(np.argmin(s.uso))
        s.E[k] = _mlp(s.r, s.d, s.ock[k], s.c)
        s.n[k], s.erro[k], s.erro_lento[k], s.lrk[k], s.conflito_ate[k] = (0, 0.5, 0.5, s.lr0k[k], 0)
        s.par[k], s.erro_comb[k], s.T[k] = (-1, 1.0, 0)
        if s.cheia > 1:
            s.mu[k], s.var[k] = (s.JX[:s.cheia].mean(0), s.JX[:s.cheia].var(0) + 0.1)
        s.diag['abertas'] += 1
        return k

    def _z(s, k, m, n):
        return float(((m - s.mu[k]) ** 2 / (s.var[k] / max(n, 1))).mean())

    def _pred(s, k, X):
        return np.argmax(_frente(s.E[k], X)[1], axis=1)

    def _comb_pred(s, k, X):
        a, b = s.par[k]
        idx = s._pred(a, X) * 4 + s._pred(b, X)
        return (np.argmax(s.T[k][idx], axis=1), idx)

    def _treinar_comb(s, k, X, Y, passes=1):
        a, b = s.par[k]
        idx = s._pred(a, X) * 4 + s._pred(b, X)
        for _ in range(passes):
            for i, y in zip(idx, Y):
                z = s.T[k][i]
                p = np.exp(z - z.max())
                p /= p.sum()
                g = p.copy()
                g[int(y)] -= 1
                s.T[k][i] -= float(s.p['passo_comb']) * g

    def _marcar(s, k):
        s.marcos.append([{q: v.copy() for q, v in s.E[k].items()}, s.mu[k].copy(), s.var[k].copy(), float(s.erro[k]), s.t])
        s.marcos = s.marcos[-2:]

    def _voltar_ao_marco(s, k):
        antigos = [m for m in s.marcos if s.t - m[4] >= s.w]
        if antigos:
            P, mu, var, erro, _ = antigos[-1]
            s.E[k] = {q: v.copy() for q, v in P.items()}
            s.mu[k], s.var[k], s.erro[k] = (mu, var, erro)
            s.diag['voltas_ao_marco'] += 1
        s.marcos = []

    def _treinar_janela(s, k):
        X, Y = (s.JX[:s.cheia], s.JY[:s.cheia].astype(np.int64))
        for i in range(len(Y)):
            g, _, _ = _grad_lote(s.E[k], X[i:i + 1], Y[i:i + 1])
            for q in s.E[k]:
                s.E[k][q] -= s.lrk[k] * g[q]
        s.n[k] += len(Y)

    def _trocar(s, so_rotulo):
        s.diag['trocas'] += 1
        if s.p['marco']:
            s._voltar_ao_marco(s.atual)
        X, Y = (s.JX[:s.cheia], s.JY[:s.cheia].astype(np.int64))
        m = X.mean(0)
        melhor, custo = (None, None)
        for k in range(s.K):
            if s.E[k] is None or k == s.atual or s.n[k] < s.w or (s._z(k, m, s.cheia) > s.lim):
                continue
            e = float(np.mean(s._pred(k, X) != Y))
            if e <= s.erro[k] + float(s.p['tol_reconhecer']) and (custo is None or e < custo):
                melhor, custo = (k, e)
        if melhor is not None:
            s.diag['reconhecidas'] += 1
            if s.p['auditoria'] and custo > s.erro[melhor] + 0.1:
                s.lrk[melhor] *= 0.7
                s.diag['ajustes_da_auditoria'] += 1
            s.atual = melhor
        elif so_rotulo and s.p['combinador'] and (s.cheia >= 16):
            cand = [k for k in range(s.K) if s.E[k] is not None and s.n[k] >= 2 * s.w and (s._z(k, m, s.cheia) <= s.lim)]
            ok = False
            if len(cand) >= 2:
                cand = sorted(cand, key=lambda k: s._z(k, m, s.cheia))[:3]
                novo = s._abrir()
                for a in cand:
                    for b in cand:
                        if a == b:
                            continue
                        s.par[novo], s.T[novo] = ((a, b), 0)
                        h = len(Y) // 2
                        s._treinar_comb(novo, X[:h], Y[:h], passes=3)
                        e = float(np.mean(s._comb_pred(novo, X[h:])[0] != Y[h:]))
                        if e < s.erro_comb[novo]:
                            s.erro_comb[novo], melhor_par = (e, (a, b))
                if s.erro_comb[novo] < float(s.p['comb_limiar']):
                    s.par[novo], s.T[novo] = (melhor_par, 0)
                    s._treinar_comb(novo, X, Y, passes=3)
                    s.diag['combinacoes'] += 1
                    ok = True
                s._treinar_janela(novo)
                s.atual = novo
            if not ok and s.p['refutacao'] == 'corrigir':
                s._corrigir()
        elif so_rotulo and s.p['refutacao'] == 'corrigir':
            s._corrigir()
        else:
            s.atual = s._abrir()
            s._treinar_janela(s.atual)
        s.cheia, s.j, s.S = (0, 0, np.zeros(len(s.dets)))

    def _corrigir(s):
        k = s.atual
        s.conflito_ate[k] = s.t + int(s.p['conflito_dur']) * s.w
        s.lrk[k] = min(0.2, s.lr0k[k] * float(s.p['reforco_correcao']))
        s._treinar_janela(k)
        s.diag['correcoes'] += 1

    def _fundir(s):
        ativos = [k for k in range(s.K) if s.E[k] is not None and k != s.atual and (s.n[k] >= s.w)]
        if s.cheia < s.w or len(ativos) < 2:
            return
        X = s.JX[:s.cheia]
        for i, a in enumerate(ativos):
            for b in ativos[i + 1:]:
                if s.E[a] is None or s.E[b] is None:
                    continue
                if float(((s.mu[a] - s.mu[b]) ** 2 / ((s.var[a] + s.var[b]) / 2)).mean()) < 0.05 and float(np.mean(s._pred(a, X) == s._pred(b, X))) >= 0.9:
                    fica, sai = (a, b) if s.n[a] >= s.n[b] else (b, a)
                    s.E[sai] = None
                    s.n[fica] += s.n[sai]
                    s.diag['fusoes'] += 1

    def _auditar(s):
        k = s.atual
        if s.erro_lento[k] > 0.55 and s.n[k] > 10 * s.w:
            s.lrk[k] = min(0.2, s.lrk[k] * 1.5)
            s.diag['ajustes_da_auditoria'] += 1
        for q in range(s.K):
            if s.E[q] is not None and q != s.atual and (s.n[q] < s.w) and (s.t - s.uso[q] > 2000):
                s.E[q] = None
                s.diag['ajustes_da_auditoria'] += 1

    def aprender(s, x, y):
        s.t += 1
        if s.atual < 0:
            s.JX[0], s.JY[0], s.cheia, s.j = (x, y, 1, 1)
            s.atual = s._abrir()
        k = s.atual
        if s.par[k][0] >= 0 and s.E[s.par[k][0]] is not None and (s.E[s.par[k][1]] is not None):
            pc, idx = s._comb_pred(k, x[None])
            s._treinar_comb(k, x[None], [y])
            s.erro_comb[k] += 0.02 * (float(pc[0] != y) - s.erro_comb[k])
        g, _, Pr = _grad_lote(s.E[k], x[None], np.array([y]))
        acerto = float(np.argmax(Pr[0]) == y)
        for q in s.E[k]:
            s.E[k][q] -= s.lrk[k] * g[q]
        s.n[k] += 1
        s.uso[k] = s.t
        if any((dt['tipo'] == 'cusum' for dt in s.dets)):
            zx = float(((x - s.mu[k]) ** 2 / s.var[k]).mean())
            for i, dt in enumerate(s.dets):
                if dt['tipo'] == 'cusum':
                    s.S[i] = max(0.0, s.S[i] + zx - float(dt['cusum_k']))
        s.mu[k] += float(s.p['taxa_estatistica']) * (x - s.mu[k])
        s.var[k] += float(s.p['taxa_estatistica']) * ((x - s.mu[k]) ** 2 - s.var[k])
        s.erro[k] += float(s.p['taxa_erro']) * (1 - acerto - s.erro[k])
        s.erro_lento[k] += 0.001 * (1 - acerto - s.erro_lento[k])
        if s.t > s.conflito_ate[k] and s.lrk[k] > s.lr0k[k] and (s.conflito_ate[k] > 0):
            s.lrk[k], s.conflito_ate[k] = (s.lr0k[k], 0)
        s.JX[s.j], s.JY[s.j], s.JA[s.j] = (x, y, acerto)
        s.j = (s.j + 1) % s.w
        s.cheia = min(s.cheia + 1, s.w)
        if s.p['marco'] and s.t % s.w == 0:
            s._marcar(k)
        if s.cheia == s.w and s.t % 5 == 0 and (s.n[k] > 2 * s.w):
            zj = None
            muda_x = False
            for i, dt in enumerate(s.dets):
                if dt['tipo'] == 'cusum':
                    muda_x = muda_x or s.S[i] > float(dt['limiar'])
                else:
                    zj = s._z(k, s.JX.mean(0), s.cheia) if zj is None else zj
                    muda_x = muda_x or zj > float(dt['limiar'])
            muda_y = 1 - s.JA.mean() > s.erro[k] + float(s.p['salto_rotulo'])
            if muda_x or muda_y:
                s._trocar(so_rotulo=muda_y and (not muda_x))
        if s.p['fusao'] and s.t % 500 == 0:
            s._fundir()
        if s.p['auditoria'] and s.t % 1000 == 0:
            s._auditar()

    def prever(s, X):
        ativos = [k for k in range(s.K) if s.E[k] is not None]
        L = np.stack([-((X - s.mu[k]) ** 2 / s.var[k] + np.log(s.var[k])).sum(1) for k in ativos], 1)
        if s.p['desempate'] == 'recente':
            perto = L >= L.max(1, keepdims=True) - 2.0
            idx = np.argmax(np.where(perto, s.uso[ativos][None, :], -1.0), axis=1)
        else:
            idx = np.argmax(L, 1)
        dono = np.array(ativos)[idx]
        out, conf = (np.zeros(len(X), np.int64), np.zeros(len(X), np.float32))
        for k in ativos:
            m = dono == k
            if not m.any():
                continue
            _, Z = _frente(s.E[k], X[m])
            Pr = np.exp(Z - Z.max(1, keepdims=True))
            Pr /= Pr.sum(1, keepdims=True)
            out[m], conf[m] = (np.argmax(Z, 1), Pr.max(1))
            if s.par[k][0] >= 0 and s.E[s.par[k][0]] is not None and (s.E[s.par[k][1]] is not None) and (s.erro_comb[k] < s.erro[k]):
                out[m] = s._comb_pred(k, X[m])[0]
        if not s.p['epistemico']:
            return (out, np.where(conf >= 0.8, 0, np.where(conf < 0.4, 3, 1)).astype(np.int8))
        zr = np.array([float(((X[i] - s.mu[dono[i]]) ** 2 / s.var[dono[i]]).mean()) for i in range(len(X))])
        et = np.ones(len(X), np.int8)
        madura = (s.n[dono] > float(s.p['maturidade']) * s.w) & (s.erro[dono] < float(s.p['erro_validado']))
        et[madura & (zr < float(s.p['limiar_validado']))] = 0
        et[s.conflito_ate[dono] > s.t] = 2
        et[zr > float(s.p['limiar_investigar'])] = 3
        return (out, et)

    def diagnostico(s):
        return dict(s.diag)

    def estado(s):
        return _empacotar({'p': s.p, 'E': [e if e is not None else 0 for e in s.E], 'vivas': [e is not None for e in s.E], 'a': {k: getattr(s, k) for k in ('mu', 'var', 'n', 'erro', 'uso', 'lrk', 'conflito_ate', 'erro_lento', 'T', 'par', 'erro_comb', 'JX', 'JY', 'JA')}, 'e': [s.j, s.cheia, s.t, s.atual, s.S], 'marcos': s.marcos, 'diag': s.diag, 'rng': s.r.bit_generator.state})

    @staticmethod
    def restaurar(b, d, c):
        o = _desempacotar(b)
        a = _A(d, c, np.random.default_rng(0), **o['p'])
        a.E = [e if viva else None for e, viva in zip(o['E'], o['vivas'])]
        for k, v in o['a'].items():
            setattr(a, k, v)
        a.j, a.cheia, a.t, a.atual, a.S = o['e']
        a.marcos, a.diag = (o['marcos'], o['diag'])
        a.r.bit_generator.state = o['rng']
        return a
PADRAO = dict(w=30, limiar=9.0, detector='janela', marco=1, fusao=0, desempate='verossimilhanca', refutacao='corrigir', combinador=1, auditoria=1, epistemico=1, lr=0.05, conflito_dur=40, limiar_investigar=2.5, limiar_validado=1.6, comb_limiar=0.6, tol_reconhecer=0.15, salto_rotulo=0.25, taxa_estatistica=0.01, taxa_erro=0.005, cusum_k=1.25, maturidade=3, erro_validado=0.35, passo_comb=0.5, reforco_correcao=3.0)

def executar(entrada, tamanho='32x12', **genes):
    oculta, K = (int(v) for v in str(tamanho).split('x'))
    p = dict(PADRAO, oculta=oculta, K=K, **genes)
    return _rodar(entrada, lambda d, c, r: _A(d, c, r, **p), _A.restaurar)

def executar_composto(entrada, pecas, w=30, limiar=9.0, taxa_estatistica=0.01, taxa_erro=0.005, tol_reconhecer=0.15, salto_rotulo=0.25, **_genes_do_motor):
    tem = lambda n: [q for q in pecas if q['primitiva'] == n]
    gav = tem('gaveta') or [{'oculta': 32, 'lr': 0.05}]
    dets = [{'tipo': q['tipo'], 'limiar': float(q['limiar']), 'cusum_k': float(q.get('cusum_k', 1.25))} for q in tem('detector')] or [{'tipo': 'janela', 'limiar': float(limiar), 'cusum_k': 1.25}]
    ep, cb, rf, ro = (tem('epistemico'), tem('combinador'), tem('refutacao'), tem('roteador'))
    lrs = [float(q['lr']) for q in gav]
    p = dict(PADRAO, w=int(w), limiar=float(limiar), taxa_estatistica=float(taxa_estatistica), taxa_erro=float(taxa_erro), tol_reconhecer=float(tol_reconhecer), salto_rotulo=float(salto_rotulo), ocultas=[int(q['oculta']) for q in gav], lrs=lrs, oculta=int(gav[0]['oculta']), K=len(gav), lr=float(np.mean(lrs)), detectores=dets, detector=dets[0]['tipo'], marco=int(bool(tem('marco'))), fusao=int(bool(tem('fusao'))), auditoria=int(bool(tem('auditoria'))), epistemico=int(bool(ep)), combinador=int(bool(cb)), refutacao=rf[0]['politica'] if rf else 'nova', desempate=ro[0]['desempate'] if ro else 'verossimilhanca')
    for org in (ep, cb, rf):
        if org:
            p.update({k: v for k, v in org[0].items() if k not in ('primitiva', 'politica')})
    return _rodar(entrada, lambda d, c, r: _A(d, c, r, **p), _A.restaurar)
