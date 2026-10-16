# -*- coding: utf-8 -*-
import sys
sys.argv.append('--dp=2')
import p4e_exato as E
E.VIDA_FASE = int(round(10 * 60 / E.DT))

def conta():
    print("A CONTA DA VIDA DE DENTRO COM d' = 2 E SEM A CONTAGEM DUPLA (antes da vida): alfa %.5f, costume de %d, Page %.2f, conhecido em %d, a fase vive %d passos" % (E.ALFA_C, E.N_GUARDA, E.LIM_PAGE, E.CONHECE, E.VIDA_FASE), flush=True)
    print("  previsto: o medo do estalo aceso do 2o ou 3o estalo ate o fim do dia 3 e esquecido nos dias 4 a 7 depois de uns 3 a 5 estalos sem estrondo, como com d' = 2 na p4e", flush=True)
    print("  previsto: a espera de antes da chegada acesa no almoco e na noite a partir do dia 3, como na p4e com d' = 2, talvez um pouco menos, porque cada chegada agora conta uma vez so", flush=True)
    print("  previsto: a procura em vao no resto do tempo sem Gabriel abaixo dos 29,8% da p4e com d' = 2, entre 10 e 30%, porque as fases ja nao somam o mesmo contato duas vezes", flush=True)
    print('  previsto: o apego, o querer, a frustracao, a saudade, o contagio, o filhote e o narrador como na p4e', flush=True)

def main():
    conta()
    if '--vida' in sys.argv:
        E.relatorio(*E.vida())
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
