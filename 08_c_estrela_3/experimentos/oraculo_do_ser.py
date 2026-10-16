# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
SEMENTE_DO_PAINEL = 21
CONFIG_LING = dict(largura=128, epocas=8, epocas_inicio=40, lote=256, lr=0.003, wd=0.001, conjunto=1)
CONFIG_DER = dict(largura=128, epocas=8, epocas_inicio=40, lote=256, lr=0.003, wd=0.003, conjunto=3)
PAINEL = [dict(largura=64, wd=0.0, conjunto=1), dict(largura=128, wd=0.0, conjunto=1), dict(largura=128, wd=0.01, conjunto=1), dict(largura=64, wd=0.003, conjunto=1), dict(largura=128, wd=0.001, conjunto=1), dict(largura=128, wd=0.003, conjunto=1), dict(largura=128, wd=0.003, conjunto=1, epocas=16), dict(largura=256, wd=0.003, conjunto=1), dict(largura=128, wd=0.003, conjunto=3)]
VARIANTES = tuple(range(0, 9))
CONFIG_DER_FIXADA = dict(largura=128, epocas=8, epocas_inicio=40, lote=256, lr=0.003, wd=0.01, conjunto=1)

def semente_da_linguagem(semente):
    return 100 + int(semente)

def caminho_ling(semente, variante=0):
    return os.path.join(RAIZ, 'experimentos', f"oraculo_ling_s{int(semente)}{('' if not variante else '_v%d' % int(variante))}.npz")

def caminho_der(semente, variante=0):
    return os.path.join(RAIZ, 'experimentos', f"oraculo_der_s{int(semente)}{('' if not variante else '_v%d' % int(variante))}.npz")

def vidas_de_linguagem(semente):
    from experimentos import vidas_do_ser as VS
    return VS.gerar_carga(VS.MundoDeLinguagem(), semente_da_linguagem(semente), 2)

def vida_da_deriva(semente):
    from experimentos import trilhas_do_ser as TR
    return TR.trilha_der(1000 * int(semente) + 4)

def oraculo_ling_da_vida(f, k, variante=0):
    from experimentos import desafio_oraculo as OR
    return OR.oraculo_da_vida(f, semente=int(k) + 50 * int(variante), **CONFIG_LING)

def oraculo_der_da_vida(vida, variante=0, config=None):
    from experimentos import trilhas_do_ser as TR
    c = dict(config or CONFIG_DER_FIXADA or CONFIG_DER)
    return TR.oraculo_da_deriva(vida, semente=50 * int(variante), **{k: v for k, v in c.items() if k in ('largura', 'epocas', 'epocas_inicio', 'lote', 'lr', 'wd', 'conjunto')})

def guardar_der(arquivo, orac):
    tmp = arquivo + '.tmp.npz'
    np.savez_compressed(tmp, O=orac['O'], tarefas=orac['tarefas'], pos=orac['pos'])
    os.replace(tmp, arquivo)

def carregar_der(arquivo):
    z = np.load(arquivo)
    return {'O': z['O'], 'tarefas': z['tarefas'], 'pos': z['pos'], 'G': np.zeros(z['O'].shape, np.int8)}

def _filho(argv):
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    return subprocess.Popen([sys.executable, '-B', os.path.abspath(__file__)] + [str(x) for x in argv], env=env)

def calcular_ling(semente=1, variantes=VARIANTES, processos=2, relato=print):
    from experimentos import desafio_oraculo as OR
    tarefas, parciais = ([], {})
    for v in variantes:
        arq = caminho_ling(semente, v)
        if os.path.exists(arq):
            continue
        parciais[v] = [f'{arq}.vida{k}.npz' for k in range(2)]
        tarefas += [(v, k, parciais[v][k]) for k in range(2) if not os.path.exists(parciais[v][k])]
    vivos, t0 = ([], time.time())
    for v, k, p in tarefas:
        while sum((1 for c, _ in vivos if c.poll() is None)) >= processos:
            time.sleep(1.0)
        vivos.append((_filho(['ling_vida', '--semente', semente, '--variante', v, '--vida', k, '--parcial', p]), p))
        relato(f'[{round(time.time() - t0)} s] lançado: linguagem, variante {v}, vida {k}')
    for c, p in vivos:
        c.wait()
        if c.returncode != 0:
            raise RuntimeError(f'o processo do oráculo falhou ({p})')
    for v, ps in parciais.items():
        out = []
        for p in ps:
            z = np.load(p)
            out.append({'O': z['O'], 'tarefas': z['tarefas'], 'pos': z['pos'], 'treino_acerto': z['treino']})
        OR.guardar_vidas(caminho_ling(semente, v), out)
        for p in ps:
            os.remove(p)
        relato(f'[{round(time.time() - t0)} s] guardado: {caminho_ling(semente, v)}')

def calcular_der(semente=1, variantes=VARIANTES, relato=print):
    vida = vida_da_deriva(semente)
    t0 = time.time()
    for v in variantes:
        arq = caminho_der(semente, v)
        if os.path.exists(arq):
            continue
        guardar_der(arq, oraculo_der_da_vida(vida, v))
        relato(f'[{round(time.time() - t0)} s] guardado: {arq}')

def painel_der(semente=SEMENTE_DO_PAINEL, relato=print):
    vida = vida_da_deriva(semente)
    out = []
    for cfg in PAINEL:
        c = dict(CONFIG_DER)
        c.update(cfg)
        t0 = time.time()
        o = oraculo_der_da_vida(vida, 0, c)
        r = {'config': cfg, 'acerto': float(np.nanmean(o['O'])), 's': round(time.time() - t0, 1)}
        out.append(r)
        relato(r)
    return out
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('comando', choices=['ling', 'der', 'painel_der', 'ling_vida'])
    ap.add_argument('--semente', type=int, default=1)
    ap.add_argument('--variantes', type=int, nargs='*', default=list(VARIANTES))
    ap.add_argument('--variante', type=int, default=0)
    ap.add_argument('--vida', type=int, default=0)
    ap.add_argument('--parcial', default=None)
    ap.add_argument('--processos', type=int, default=2)
    a = ap.parse_args()
    if a.comando == 'ling':
        calcular_ling(a.semente, a.variantes, a.processos)
    elif a.comando == 'der':
        calcular_der(a.semente, a.variantes)
    elif a.comando == 'painel_der':
        painel_der(a.semente)
    else:
        ent = vidas_de_linguagem(a.semente)
        o = oraculo_ling_da_vida(ent['fluxos'][a.vida], a.vida, a.variante)
        np.savez_compressed(a.parcial, O=o['O'], tarefas=o['tarefas'], pos=o['pos'], treino=o['treino_acerto'])
