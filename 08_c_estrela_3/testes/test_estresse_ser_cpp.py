# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
if os.name == 'nt':
    import shutil
    if shutil.which('g++'):
        os.add_dll_directory(os.path.dirname(shutil.which('g++')))
from experimentos import l_ser_cpp as LC
from experimentos import l_ser_interp as LI
from experimentos import l_ser_lang as L
from experimentos import l_ser_testemunhas as LT
PASSOS = int(os.environ.get('PASSOS_SER', '6000'))
if os.environ.get('ESTRESSE_EPS'):
    LI.definir_perturbacao(float(os.environ['ESTRESSE_EPS']), int(os.environ.get('ESTRESSE_SEMENTE_PERT', '777')))
    print(f"  com a perturbação: eps {LI.PERTURBACAO['eps']}, semente {LI.PERTURBACAO['semente']}")

def _lado_a_lado(bits, passos=PASSOS):
    from experimentos import desafio_v as V
    entrada = V.gerar_vidas(V.SEMENTE_DA_VIDA)
    fab_n, rest_n = LI.fabricar(bits)
    fab_c, rest_c = LC.fabricar(bits)
    d, c = (entrada['d_entrada'], entrada['classes'])
    a, b = (fab_n(d, c, np.random.default_rng(100)), fab_c(d, c, np.random.default_rng(100)))
    if getattr(a, 'usa_xi', False):
        return (None, 'usa ruído (o C++ sorteia com outro gerador): fora deste teste')
    ler = entrada['fluxos'][0]['abrir']()
    n, margem = (0, 1.0)
    while n < passos:
        ev = ler()
        if ev is None:
            break
        if ev[0] == 'treino':
            x = np.asarray(ev[1], np.float32)
            _apre, s_l, _, _ = a._frente(x[None, :])
            margem = min([float(np.min(np.abs(s))) for s in s_l] or [1.0])
            antes = a.diag['renascidas'] + a.diag['ativadas']
            a.aprender(x.copy(), ev[2])
            b.aprender_varios(x[None, :].copy(), np.asarray([ev[2]], np.int64))
            n += 1
            est = all((a.diag[k] == b.diag[k] for k in ('renascidas', 'ativadas', 'liberadas'))) and all((np.array_equal(ma, mb) for ma, mb in zip(a.mask, b.mask)))
            dw = max((float(np.max(np.abs(np.asarray(wa, np.float64) - np.asarray(wb, np.float64)))) / max(1.0, float(np.max(np.abs(wa)))) for wa, wb in zip(a.W, b.W)))
            if a.diag['renascidas'] + a.diag['ativadas'] > antes:
                return (n, ('sorteio', est, dw))
            if dw > 0.001 or not est:
                return (n, (dw, margem, est))
        elif ev[0] == 'sonda':
            pa, ea = a.prever(ev[1].copy())
            pb, eb = b.prever(ev[1].copy())
            if not np.array_equal(np.asarray(pa), np.asarray(pb)):
                return (n, (float('nan'), margem if n else 1.0, False))
        else:
            a, b = (rest_n(a.estado(), d, c), rest_c(b.estado(), d, c))
    return (n, None)

def _julgar(nome, n, sep):
    if sep is None:
        return f'  {nome}: {n} passos, sem separação'
    if isinstance(sep, str):
        return f'  {nome}: {sep}'
    if sep[0] == 'sorteio':
        msg = f"  {nome}: iguais até o passo {n}, o primeiro renascer ou ativar (as unidades escolhidas e as máscaras {('batem' if sep[1] else 'NÃO batem: ERRO')}; os pesos novos são outro sorteio)"
        assert sep[1], msg
        return msg
    dw, margem, est = sep
    ok = margem < 1e-06 and est
    msg = f"  {nome}: separou no passo {n} (dw {dw:.2e}, menor |pré-ativação| {margem:.1e}, estruturais iguais: {est}) -> {('arredondamento em cima de zero' if ok else 'ERRO: separou fora do limite')}"
    assert ok, msg
    return msg

def test_os_programas_densos_so_se_separam_em_cima_de_zero():
    g = np.random.default_rng(20261004)
    n_alvo, feitos, tent = (int(os.environ.get('ESTRESSE_SER', '12')), 0, 0)
    while feitos < n_alvo and tent < 50 * n_alvo:
        tent += 1
        prog_bits = L.CODIFICACAO.sortear(g, p_secao=1.0)
        if feitos % 2 == 0:
            for nome in ('REINIT', 'ATIVA'):
                prog_bits[L._POR_NOME[f'{nome}.presente']['inicio']] = 0
            prog_bits = L.canonizar_bits(prog_bits)
        prog = L.decodificar_bits(prog_bits)
        if prog.secoes['RETRO'] is None and g.random() < 0.5:
            continue
        n, sep = _lado_a_lado(prog_bits)
        if isinstance(sep, str):
            continue
        print(_julgar(f'denso {feitos}', n, sep), flush=True)
        feitos += 1
    assert feitos == n_alvo

def test_as_testemunhas_so_se_separam_em_cima_de_zero():
    for nome, bits in LT.testemunhas_em_bits().items():
        n, sep = _lado_a_lado(bits)
        print(_julgar(nome, n, sep), flush=True)

def test_as_fotos_da_nota_so_se_separam_em_cima_de_zero():
    caminho = os.environ.get('FOTOS_SER')
    if not caminho or not os.path.exists(caminho):
        print('  pulado: sem FOTOS_SER')
        return
    import json
    for nome, bits in json.load(open(caminho, encoding='utf-8')).items():
        n, sep = _lado_a_lado(np.array([int(c) for c in bits], np.uint8) if isinstance(bits, str) else np.asarray(bits, np.uint8))
        print(_julgar(nome, n, sep), flush=True)

def _veredito(bits, backend):
    from experimentos import desafio_v as DV
    from experimentos import desafio_v_ser as V
    DV.definir_backend(backend)
    av = V.AvaliadorReal(backend=backend)
    return (V.julgar(av.medir(np.asarray(bits, np.uint8))), V)

def test_o_veredito_da_v_nas_fotos_da_nota_e_igual_nos_dois_motores():
    import json
    alvos = []
    caminho = os.environ.get('FOTOS_SER')
    if caminho and os.path.exists(caminho):
        alvos += [(n, np.array([int(c) for c in b], np.uint8)) for n, b in json.load(open(caminho, encoding='utf-8')).items()]
    g = np.random.default_rng(404)
    alvos += [(f'denso v{i}', L.CODIFICACAO.sortear(g, p_secao=1.0)) for i in range(int(os.environ.get('VEREDITO_DENSOS', '0')))]
    diferentes = []
    for nome, bits in alvos:
        v1, V = _veredito(bits, 'numpy')
        v2, _ = _veredito(bits, 'cpp')
        if v1['estado'] != 'ok' or v2['estado'] != 'ok':
            print(f"  {nome}: estado numpy {v1['estado']}, C++ {v2['estado']}", flush=True)
            assert v1['estado'] == v2['estado'], nome
            continue
        ids = [c[0] for c in V.CLAUSULAS]
        x1, x2 = (np.asarray(v1['valores'], float), np.asarray(v2['valores'], float))
        resto = np.array([i != 'r_memoria_fixa' for i in ids])
        dif = float(np.max(np.abs(x1[resto] - x2[resto])))
        troca_ = {ids[i] for i, x in enumerate(v1['violacoes']) if x > 1e-09} ^ {ids[i] for i, x in enumerate(v2['violacoes']) if x > 1e-09}
        dd = abs(v1['distancia'] - v2['distancia']) / max(v1['distancia'], 1)
        ok = dif < 0.1 and len(troca_) <= 2 and (dd <= 0.15)
        grandes = {ids[i]: (round(float(x1[i]), 3), round(float(x2[i]), 3)) for i in range(len(ids)) if resto[i] and abs(x1[i] - x2[i]) >= 0.05}
        print(f"  {nome}: distância numpy {v1['distancia']}, C++ {v2['distancia']}; maior diferença numa cláusula {dif:.3f}; trocam de lado {sorted(troca_)}; cláusulas com diferença >= 0,05 (numpy, C++): {grandes} -> {('igual' if ok else 'DIFERENTE')}", flush=True)
        diferentes.append(nome) if not ok else None
    assert not diferentes, diferentes
    from experimentos import desafio_v as DV
    DV.definir_backend('numpy')
if __name__ == '__main__':
    for nome, f in list(globals().items()):
        if nome.startswith('test_'):
            f()
            print('ok', nome, flush=True)
