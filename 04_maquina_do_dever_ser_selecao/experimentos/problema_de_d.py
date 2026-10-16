"""O que o arquivo de fotos, o escritor de bits e o condutor precisam saber de um D, além da codificação da foto atômica (`foto_atomica.py`): a V e a foto comportamental. Um `Problema` junta as duas
metades (a codificação do corpus concorrente e o que V devolve dele) e é a única coisa que muda de um D para outro; o resto do motor não conhece D nenhum.

  codificacao            o contrato da foto atômica (`foto_atomica.CodificacaoBase`)
  predicados             os predicados fixos e versionados da foto comportamental (`len`, `duras`, `mascara_das_duras`, `duras_que_falham`, `descricao`)
  nomes_dos_predicados   o nome de cada predicado (para o relatório do que o aprendiz aprendeu)
  clausulas              as cláusulas de D: (id, medida, operador, limite, escala)
  classes                os nomes das classes de distância a D (a última é "sem classe")
  violacoes(valores)     a violação de cada cláusula para os valores medidos
  violacoes_de_coluna    a violação de uma cláusula para uma coluna de valores
  julgar(resultado)      o veredito de V (a distância a D, a classe, o comportamento...)
  calibrar()             (opcional) os controles de V (Cal): devolve {"ok": bool, ...}; o condutor não começa se ele reprova
  hash_de_v()            (opcional) o hash de V (laço 12): o condutor o confere na partida e a cada diagnóstico"""
import os


class Problema:
    def __init__(self, nome, codificacao, predicados, nomes_dos_predicados, clausulas, classes, violacoes, violacoes_de_coluna, julgar=None, calibrar=None, hash_de_v=None, selo_do_banco=None, exige_selo=False,
                 hashes_dos_oraculos=None):
        """`selo_do_banco` é o CAMINHO do arquivo do selo do banco retido da prova cega (só o caminho: a busca nunca importa nem abre o banco), `exige_selo` diz que a corrida só começa com ele gravado (o banco tem de estar
        selado ANTES da busca) e `hashes_dos_oraculos` é uma função sem argumentos com o hash de cada arquivo de oráculo (para a integridade do fim da corrida)."""
        self.selo_do_banco = selo_do_banco
        self.exige_selo = bool(exige_selo)
        self.hashes_dos_oraculos = hashes_dos_oraculos
        self.nome = nome
        self.codificacao = codificacao
        self.predicados = predicados
        self.nomes_dos_predicados = list(nomes_dos_predicados)
        self.n_definidos = len(self.nomes_dos_predicados)
        self.clausulas = list(clausulas)
        self.n_clausulas = len(self.clausulas)
        self.classes = tuple(classes)
        self.violacoes = violacoes
        self.violacoes_de_coluna = violacoes_de_coluna
        self.julgar = julgar
        self.calibrar = calibrar
        self.hash_de_v = hash_de_v
