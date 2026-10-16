# -*- coding: utf-8 -*-
import numpy as np

def conferir(entrada, saida):
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
        if len(resp) != len(av['sondas_em']) or len(etq) != len(av['sondas_em']):
            return (False, 'uma resposta e uma etiqueta por sonda')
        if len(bts) != len(av['interromper_em']):
            return (False, 'um estado em bytes por interrupção')
        n = len(av['tarefa_sonda'])
        for r, e in zip(resp, etq):
            r, e = (np.asarray(r), np.asarray(e))
            if r.shape != (n,) or e.shape != (n,) or r.min() < 0 or (r.max() >= entrada['classes']) or (e.min() < 0) or (e.max() > 3):
                return (False, 'resposta ou etiqueta fora da forma')
    return (True, 'ok')
