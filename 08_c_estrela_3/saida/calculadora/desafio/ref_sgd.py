# -*- coding: utf-8 -*-
class _A:

    def __init__(s, d, c, r, lr=0.05, oculta=64):
        s.P, s.lr, s.d, s.c = (_mlp(r, d, int(oculta), c), float(lr), d, c)

    def aprender(s, x, y):
        g, _, _ = _grad_lote(s.P, x[None], np.array([y]))
        for k in s.P:
            s.P[k] -= s.lr * g[k]

    def prever(s, X):
        _, Z = _frente(s.P, X)
        Pr = np.exp(Z - Z.max(1, keepdims=True))
        Pr /= Pr.sum(1, keepdims=True)
        return (np.argmax(Z, axis=1), _etiquetas_por_confianca(Pr))

    def estado(s):
        return _empacotar({'P': s.P, 'lr': s.lr})

    @staticmethod
    def restaurar(b, d, c):
        o = _desempacotar(b)
        a = _A.__new__(_A)
        a.P, a.lr, a.d, a.c = (o['P'], o['lr'], d, c)
        return a

def executar(entrada, lr=0.05, oculta=64):
    return _rodar(entrada, lambda d, c, r: _A(d, c, r, lr, oculta), _A.restaurar)
