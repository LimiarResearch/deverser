# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

def _argumentos(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--modo', required=True, choices=['corrida', 'fumaca'])
    ap.add_argument('--saida', required=True)
    ap.add_argument('--autorizacao', default=None, help='a frase (e a data) em que a corrida foi autorizada: obrigatória nos dois modos; fica na declaração')
    ap.add_argument('--processos', type=int, default=4)
    ap.add_argument('--backend', default='numpy', choices=['numpy', 'cpp'], help='o interpretador do Ser que V usa; a fumaça só roda com cpp')
    ap.add_argument('--semente', type=int, default=1)
    ap.add_argument('--tempo', type=float, default=None, help='fusível em segundos (o padrão da corrida é sem teto; o da fumaça é 600)')
    ap.add_argument('--max-rodadas', dest='max_rodadas', type=int, default=0)
    ap.add_argument('--celula', default=None, choices=[None, 'aprende'], help='(C★2) a célula: o D restrito ao grupo "aprende" (a mesma V); sem isso, o D inteiro')
    ap.add_argument('--v2', action='store_true', help='(C★3) a V da busca v2: a piscina, a perturbação, a sonda, o sal e a pior de k para quem decide (exige --backend cpp)')
    ap.add_argument('--migrar-hash', dest='migrar_hash', nargs=3, default=None, metavar=('DE', 'PARA', 'PROVA'), help='(04/10) na retomada: o hash de V gravado (DE) passa ao atual (PARA), com a prova de que os vereditos são os mesmos; só o par exato vale, e a troca fica no registro')
    ap.add_argument('--replicas', type=int, default=2, help='(C★3) em quantos trabalhadores mora cada conjunto da piscina; a medida vai ao menos ocupado (o roteamento não muda nenhuma medida)')
    ap.add_argument('--doadoras', nargs='*', default=None, help='(C★3) as pastas de corridas anteriores cujas melhores fotos entram como doadoras (rótulo de origem doadora_da_celula; nunca pai nem recorde)')
    ap.add_argument('--config', default=None, help='um json com campos de Config a trocar (os padrões são escolhas da IA, confirmadas em 01/10; trocar um deles é uma nova escolha para o Ok dele)')
    return ap.parse_args(argv)

def main(argv=None):
    a = _argumentos(argv)
    if not (a.autorizacao and a.autorizacao.strip()):
        sys.exit('RECUSADO: sem a autorização (--autorizacao "<a frase e a data>") nada é lançado, nem a fumaça.')
    if a.v2 and a.backend != 'cpp':
        sys.exit('RECUSADO: a V da busca v2 só roda no interpretador em C++ (a perturbação e a sonda foram feitas nele). Use --backend cpp.')
    if a.modo == 'fumaca' and a.backend != 'cpp':
        sys.exit('RECUSADO: a fumaça só roda depois do interpretador em C++ (decisão de 30/09): sem ele a vazão medida é a do numpy. Use --backend cpp.')
    if a.backend == 'cpp':
        from experimentos import l_ser_cpp
        l_ser_cpp.compilar()
    from experimentos import condutor_de_fotos as C
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_testemunhas as LT
    from experimentos import problema_de_d as PD
    kw = json.load(open(a.config, encoding='utf-8')) if a.config else {}
    kw.setdefault('semente', a.semente)
    if a.modo == 'fumaca':
        kw.setdefault('tempo', 600.0)
    elif a.tempo is not None:
        kw['tempo'] = a.tempo
    if a.modo == 'fumaca' and a.tempo is not None:
        kw['tempo'] = a.tempo
    if a.max_rodadas:
        kw['max_rodadas'] = a.max_rodadas
    if a.v2:
        kw.setdefault('v2_nivel_decisao', 3)
        kw.setdefault('testemunhas_doadoras', True)
    if a.doadoras:
        kw['doadoras_de_corridas'] = tuple(a.doadoras)
    cfg = C.Config(**kw)
    os.makedirs(a.saida, exist_ok=True)
    if a.v2:
        if a.celula:
            sys.exit('RECUSADO: a célula ainda não tem a V v2.')
        from experimentos import c3_v_repartida as VR
        problema = PD.problema_do_ser_v2(processos_do_cal=a.processos)
        cal = problema.calibrar()
        problema.calibrar = lambda: cal
        from experimentos import c3_v_compartilhada as CC
        avaliador = CC.avaliador(trabalhadores=a.processos, replicas=a.replicas, backend=a.backend)
    else:
        problema = PD.problema_do_ser_restrito(PD.GRUPO_APRENDE, 'aprende') if a.celula == 'aprende' else PD.problema_do_ser()
        avaliador = V.Avaliacoes(processos=a.processos, alvo='ser', backend=a.backend)
    try:
        corrida = C.Corrida(problema, avaliador, a.saida, cfg, testemunhas=LT.testemunhas_em_bits(), ok_de_gabriel=a.autorizacao.strip(), modo=a.modo)
        if a.migrar_hash:
            corrida.migracao_do_hash = {'de': a.migrar_hash[0], 'para': a.migrar_hash[1], 'prova': a.migrar_hash[2]}
        corrida.rodar()
        print('fim:', json.dumps({'parada': corrida.parada, 'rodadas': corrida.rodada_n, 'fotos': len(corrida.fotos), 'menor_distancia': None if corrida.melhor is None else corrida.melhor[0]}), flush=True)
    finally:
        avaliador.fechar()
if __name__ == '__main__':
    main()
