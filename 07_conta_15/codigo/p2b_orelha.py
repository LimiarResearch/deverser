# -*- coding: utf-8 -*-
import sys
sys.argv.append('--dp=2')
import numpy as np
import p1_aprender as P
import p1b_limiar as B
import p4e_exato as E
import p2_orelha as O2
_pesos = P.pesos

def pesos_exato(a, b, N1, N0):
    w = _pesos(a, b, N1, N0)
    p0 = (b + P.PRIOR) / (N0 + 2 * P.PRIOR)
    n1 = np.broadcast_to(N1, np.shape(a))
    i = np.clip(np.searchsorted(E.GRADE, n1 * p0), 0, len(E.GRADE) - 1)
    ai = np.floor(a + 1e-09)
    voto = (ai >= E.CIMA[i]) | (ai <= E.BAIXO[i])
    return np.where(voto & (n1 > 0), w, 0.0)
P.pesos = pesos_exato
B.ALFA = E.ALFA_C
B.N_GUARDA = E.N_GUARDA
B.LIM_PAGE = E.LIM_PAGE

def main():
    print("A ORELHA COM d' = 2 E A SINAPSE EXATA: alfa %.5f, costume de %d, Page %.2f (a p2 tinha 0,00135, 6.668 e 6,61)" % (E.ALFA_C, E.N_GUARDA, E.LIM_PAGE), flush=True)
    print('  previsto, contra a p2: aprender mais cedo (menos anuncios para a fala nunca ouvida acender); os acendimentos errados sobem, porque o criterio agora aceita 2,3% (93,5 de 4.110), e ficam abaixo dele; mais esquecimentos falsos, porque o limite de Page cai de 6,61 para 3,76; a conta abaixo diz quanto', flush=True)
    PAL, f, _, S = P.carregar()
    V, nev, durs = O2.carregar2(PAL)
    O2.conta2(PAL, f, V, S, nev, durs)
    if '--vida' in sys.argv:
        O2.vida2(PAL, f, V, S)
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
