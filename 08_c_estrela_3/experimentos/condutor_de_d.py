# -*- coding: utf-8 -*-
import argparse
import importlib
import json
import os
import sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

def _argumentos(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--problema', required=True, help='`modulo:funcao` (a função, sem argumentos, devolve `(problema, avaliador)` ou `(problema, avaliador, testemunhas)`)')
    ap.add_argument('--saida', required=True, help='a pasta da corrida (relançar com a mesma pasta retoma)')
    ap.add_argument('--autorizacao', default=None, help='a frase (e a data) em que quem manda na corrida a autorizou: obrigatória; fica na declaração')
    ap.add_argument('--modo', default='corrida', choices=['corrida', 'fumaca'])
    ap.add_argument('--semente', type=int, default=1)
    ap.add_argument('--tempo', type=float, default=None, help='fusível em segundos (o padrão da corrida é sem teto: roda até achar D; o da fumaça é 600)')
    ap.add_argument('--max-rodadas', dest='max_rodadas', type=int, default=0, help='fusível de rodadas (0 = sem teto)')
    ap.add_argument('--config', default=None, help='um json com campos de `condutor_de_fotos.Config` a trocar (cada campo está explicado em `Config` e no manual, apêndice B)')
    ap.add_argument('--sem-bateria', dest='sem_bateria', action='store_true', help='não roda a bateria do contrato da codificação (só para quem já a rodou: o condutor não a repete)')
    ap.add_argument('--guardar-resultado-inteiro', dest='resultado_inteiro', action='store_true', help='(C★2, degrau 3b) guarda o resultado inteiro de V de cada foto (por vida), ao lado do arquivo, em `resultado_inteiro_de_V/`; V e o veredito não mudam')
    return ap.parse_args(argv)

def carregar(spec):
    modulo, _, funcao = spec.partition(':')
    if not modulo or not funcao:
        sys.exit(f'RECUSADO: --problema deve ser `modulo:funcao` (veio `{spec}`).')
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    try:
        f = getattr(importlib.import_module(modulo), funcao)
    except (ImportError, AttributeError) as e:
        sys.exit(f'RECUSADO: não achei `{funcao}` em `{modulo}`: {e!r}')
    r = f()
    if not (isinstance(r, (tuple, list)) and len(r) in (2, 3)):
        sys.exit(f'RECUSADO: `{spec}` deve devolver (problema, avaliador) ou (problema, avaliador, testemunhas).')
    problema, avaliador = (r[0], r[1])
    if not hasattr(avaliador, 'medir'):
        sys.exit('RECUSADO: o avaliador não tem `medir(lista_de_bits)`.')
    return (problema, avaliador, dict(r[2]) if len(r) == 3 and r[2] else None)

def main(argv=None):
    a = _argumentos(argv)
    if not (a.autorizacao and a.autorizacao.strip()):
        sys.exit('RECUSADO: sem a autorização (--autorizacao "<quem autorizou e quando>") nada é lançado, nem a fumaça: a máquina não começa uma corrida sozinha.')
    from experimentos import condutor_de_fotos as C
    from experimentos import foto_atomica as FA
    problema, avaliador, testemunhas = carregar(a.problema)
    if a.resultado_inteiro:
        from experimentos import resultado_inteiro_de_v as RV
        avaliador = RV.AvaliadorQueGuarda(avaliador, a.saida, problema.codificacao)
    try:
        if not a.sem_bateria:
            rel = FA.verificar_codificacao(problema.codificacao)
            print('bateria do contrato da foto atômica:', json.dumps(rel['resumo'], ensure_ascii=False), flush=True)
            if not rel['ok']:
                sys.exit('RECUSADO: a codificação reprova a bateria do contrato (nenhuma medida foi feita): ' + '; '.join(rel['falhas']))
        kw = json.load(open(a.config, encoding='utf-8')) if a.config else {}
        kw.setdefault('semente', a.semente)
        if a.modo == 'fumaca':
            kw.setdefault('tempo', 600.0)
        if a.tempo is not None:
            kw['tempo'] = a.tempo
        if a.max_rodadas:
            kw['max_rodadas'] = a.max_rodadas
        cfg = C.Config(**kw)
        os.makedirs(a.saida, exist_ok=True)
        corrida = C.Corrida(problema, avaliador, a.saida, cfg, testemunhas=testemunhas, ok_de_gabriel=a.autorizacao.strip(), modo=a.modo)
        corrida.rodar()
        print('fim:', json.dumps({'parada': corrida.parada, 'rodadas': corrida.rodada_n, 'fotos': len(corrida.fotos), 'menor_distancia': None if corrida.melhor is None else corrida.melhor[0]}), flush=True)
    finally:
        fechar = getattr(avaliador, 'fechar', None)
        if callable(fechar):
            fechar()
if __name__ == '__main__':
    main()
