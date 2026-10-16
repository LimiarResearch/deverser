# -*- coding: utf-8 -*-
import json
import os
import sys
import time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
REPETICOES = 8
SEMENTE_DOS_NULOS = 10000

def para_cima(x, piso=0.02):
    return float(np.maximum(piso, np.ceil(np.round(np.asarray(x, np.float64), 6) / 0.01 - 1e-09) * 0.01))

def media_mais_3dp(v):
    v = np.asarray(v, np.float64)
    return float(v.mean() + 3.0 * v.std(ddof=1)) if len(v) > 1 else float(v.mean())

def _dados_dos_blocos(f):
    from experimentos import desafio_oraculo as OR
    xs, ys, _ = OR.ler_vida(f)
    OR.zerar_registro(f)
    av = f['_avaliacao'].abrir()
    return {b['id']: (xs[b['ini']:b['ini'] + b['n']], ys[b['ini']:b['ini'] + b['n']]) for b in av['blocos']}

def _fresco_do_bloco(b, dados, semente):
    from experimentos import trilhas_do_ser as TR
    x, y = dados[b['id']]
    return TR._fresco_curva(x, y, b['X'], b['y'], b['grade'], semente)

def nulo_das_trilhas(entrada, repeticoes=REPETICOES, relato=None):
    from experimentos import trilhas_do_ser as TR
    vidas = {t: [f for f in entrada['fluxos'] if f['tipo'] == t] for t in ('comp', 'fam', 'reg')}
    dados = {t: [_dados_dos_blocos(f) for f in fs] for t, fs in vidas.items()}
    out = {'compoe_8': [], 'compoe_32': [], 'melhora_com_o_uso': [], 'latencia_de_adaptacao': [], 'custo_da_volta': []}
    t0 = time.time()
    for rep in range(repeticoes):
        base = SEMENTE_DOS_NULOS + 997 * rep
        g8, g32, mel, lat, vol = ([], [], [], [], [])
        for k, f in enumerate(vidas['comp']):
            av = f['_avaliacao'].abrir()
            ganhos = {8: [], 32: []}
            for b in av['blocos']:
                cur = _fresco_do_bloco(b, dados['comp'][k], base + 31 * b['id'] + 5000 * k)
                for i, n in enumerate(b['grade']):
                    if n in ganhos:
                        ganhos[n].append(cur[i] - b['fresco'][i])
            g8.append(float(np.mean(ganhos[8])))
            g32.append(float(np.mean(ganhos[32])))
        for k, f in enumerate(vidas['fam']):
            av = f['_avaliacao'].abrir()
            ganhos = [float(np.mean(np.asarray(_fresco_do_bloco(b, dados['fam'][k], base + 31 * b['id'] + 5000 * k)) - np.asarray(b['fresco']))) for b in av['blocos']]
            mel.append(float(np.mean(ganhos[-3:]) - np.mean(ganhos[:3])))
        for k, f in enumerate(vidas['reg']):
            av = f['_avaliacao'].abrir()
            curvas = {b['id']: _fresco_do_bloco(b, dados['reg'][k], base + 31 * b['id'] + 5000 * k) for b in av['blocos']}
            novas = [b for b in av['blocos'] if b['papel'] == 'nova']
            ganhos = [float(np.mean(np.asarray(curvas[b['id']]) - np.asarray(b['fresco']))) for b in novas]
            lat.append(float(np.mean(ganhos[:6]) - np.mean(ganhos[-6:])))
            razoes = []
            for b in av['blocos']:
                if b['papel'] != 'volta':
                    continue
                p = novas[b['primeira']]
                nivel = float(np.mean(curvas[p['id']][-3:]))
                e_primeira = TR.exemplos_ate(curvas[p['id']], p['grade'], nivel=nivel)
                e_volta = 0.0 if curvas[b['id']][0] >= TR.FRACAO_DO_NIVEL * nivel else TR.exemplos_ate(curvas[b['id']], b['grade'], nivel=nivel)
                razoes.append(e_volta / max(e_primeira, 1.0))
            vol.append(float(np.mean(razoes)))
        out['compoe_8'].append(max(g8))
        out['compoe_32'].append(max(g32))
        out['melhora_com_o_uso'].append(max(mel))
        out['latencia_de_adaptacao'].append(max(lat))
        out['custo_da_volta'].append(min(vol))
        if relato:
            relato(f'repetição {rep + 1}/{repeticoes}  {round(time.time() - t0)} s')
    r = {'por_repeticao': {k: [round(x, 5) for x in v] for k, v in out.items()}}
    r['media'] = {k: round(float(np.mean(v)), 5) for k, v in out.items()}
    r['desvio'] = {k: round(float(np.std(v, ddof=1)), 5) for k, v in out.items()}
    r['media_mais_3_desvios'] = {k: round(media_mais_3dp(v), 5) for k, v in out.items()}
    r['tolerancia_pela_regra'] = {'compoe_8': para_cima(media_mais_3dp(out['compoe_8'])), 'compoe_32': para_cima(media_mais_3dp(out['compoe_32'])), 'melhora_com_o_uso': para_cima(media_mais_3dp(out['melhora_com_o_uso'])), 'latencia_de_adaptacao': para_cima(media_mais_3dp(out['latencia_de_adaptacao']))}
    return r

def eta_da_deriva(semente=1, variantes=range(1, 9)):
    from experimentos import desafio_oraculo as OR
    from experimentos import oraculo_do_ser as OS
    o0 = OS.carregar_der(OS.caminho_der(semente, 0))
    v = [float(OR.variacao_entre_recomecos([o0], [OS.carregar_der(OS.caminho_der(semente, k))])[0][0]) for k in variantes]
    return {'variacao_por_recomeco': [round(x, 5) for x in v], 'media': round(float(np.mean(v)), 5), 'desvio': round(float(np.std(v, ddof=1)), 5), 'media_mais_3_desvios': round(media_mais_3dp(v), 5), 'tolerancia_pela_regra': para_cima(media_mais_3dp(v))}

def medir(semente=1, repeticoes=REPETICOES, relato=print):
    from experimentos import trilhas_do_ser as TR
    entrada = TR.gerar_trilhas(semente)
    return {'o_que_e': 'o nulo de cada medida nova da V do Ser: o que um aprendiz sem a capacidade obtém (um fresco contra outro), em oito repetições; a tolerância é a média mais três desvios, para cima em 0,01 (piso 0,02)', 'semente': int(semente), 'repeticoes': int(repeticoes), 'trilhas': nulo_das_trilhas(entrada, repeticoes, relato), 'deriva': eta_da_deriva(semente)}
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--semente', type=int, default=1)
    ap.add_argument('--repeticoes', type=int, default=REPETICOES)
    ap.add_argument('--saida', default=os.path.join(RAIZ, 'bancada_patches', 'dados', 'nulos_da_v_ser.json'))
    a = ap.parse_args()
    r = medir(a.semente, a.repeticoes)
    os.makedirs(os.path.dirname(a.saida), exist_ok=True)
    json.dump(r, open(a.saida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'trilhas': r['trilhas']['tolerancia_pela_regra'], 'deriva': r['deriva']['tolerancia_pela_regra'], 'media_dos_nulos': r['trilhas']['media']}, ensure_ascii=False, indent=1))
