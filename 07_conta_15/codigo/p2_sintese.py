# -*- coding: utf-8 -*-
import io
import json
import sys
import time
import numpy as np
sys.path.insert(0, '/home/iro/casa/cerebro')
from ferramentas_iro import Boca
COC = json.load(io.open('/home/iro/casa/cerebro/coclea14_bandas.json', encoding='utf-8'))
F_LO, F_HI, ERB_LO, NB = (COC['F_LO'], COC['F_HI'], COC['ERB_LO'], int(COC['N_BANDAS']))
WIN_MS, HOP_MS, PAUSA_S, FALAS = (25.0, 11.6, 0.5, 5)
VOZ = '/home/iro/casa/mundo/voz/pt_BR-faber-medium.onnx'

def erb(f):
    return 21.4 * np.log10(1.0 + 0.00437 * np.asarray(f, float))

def energias(x, taxa):
    n, h = (int(round(WIN_MS / 1000.0 * taxa)), int(round(HOP_MS / 1000.0 * taxa)))
    f = np.fft.rfftfreq(n, 1.0 / taxa)
    dentro = (f >= F_LO) & (f < F_HI)
    canal = np.minimum((erb(f) - ERB_LO).astype(int), NB - 1)
    jan = np.hanning(n)
    nq = max(0, (len(x) - n) // h + 1)
    E = np.zeros((nq, NB), np.float32)
    for q in range(nq):
        s = np.abs(np.fft.rfft(x[q * h:q * h + n] * jan)) ** 2
        E[q] = np.bincount(canal[dentro], weights=s[dentro], minlength=NB)
    return E

def main():
    t0 = time.time()
    PAL = list(json.load(io.open('/home/iro/bancada/vozes/fonetica.json', encoding='utf-8'))['palavras'])
    boca = Boca(VOZ, sorteio=True)
    Es, rot, rep = ([], [], [])
    for i, w in enumerate(PAL):
        fon = boca.fonemas(w)
        for r in range(FALAS):
            x, taxa, _ = boca.dizer_fonemas(fon)
            x = np.asarray(x, np.float64)
            z = np.zeros(int(PAUSA_S * taxa))
            Es.append(energias(np.concatenate([z, x, z]), taxa))
            rot.append(i)
            rep.append(r)
        if i % 50 == 0:
            print('  %d de %d palavras, %.0f s' % (i, len(PAL), time.time() - t0), flush=True)
    comp = np.array([len(E) for E in Es])
    np.savez_compressed('p2_mundo.npz', E=np.concatenate(Es), comp=comp, rot=np.array(rot), rep=np.array(rep), taxa=taxa)
    print('FIM: %d falas de %d palavras, %d quadros, em %.0f s' % (len(Es), len(PAL), int(comp.sum()), time.time() - t0), flush=True)
if __name__ == '__main__':
    main()
