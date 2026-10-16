"""O contrato de adaptador: tudo o que é do domínio entra por aqui, e o núcleo não sabe mais nada do domínio.

Um adaptador define:
- formulacoes(D, Pi): as formulações completas do domínio, na ordem em que vale tentá-las (a família declarada);
- elimina(restricao, formulacao): se uma restrição tirada de um nulo elimina a formulação (sem construí-la);
- construir(formulacao, D, Pi, contexto): o corpo inteiro, ou um veredito de impossibilidade sem consultar o verificador;
- verificar(corpo, formulacao, D, Pi, contexto): o veredito delimitado (ver abaixo); o contexto traz as evidências que valem, e o
  verificador pode reusar uma medida cujas hipóteses continuam de pé em vez de medir de novo;
- restricoes(veredito, formulacao, D, Pi): o que o nulo elimina, cada restrição com as hipóteses (cláusulas e números de Π) de que
  depende, para a regra de transferência;
- medidas_de_objetivo(veredito): os valores dos objetivos de D medidos no corpo aprovado;
- exportar(corpo, formulacao, pasta, D, Pi, ver) e conferir_exportado(arquivos, corpo, formulacao, D, Pi, ver): o artefato e a prova de
  que ele é o corpo verificado.

Veredito: {"aprovado": bool, "medidas": {...}, "escopo": texto do que foi provado ou simulado, "nulo": None ou {"classe" (uma de
CLASSES_DE_NULO), "clausula", "condicao", "medida", "motivo"}, "custo": {nome: quantidade} do que a verificação gastou (medições
no alvo, segundos de simulação), "evidencias": [...] medidas novas, cada uma com as hipóteses de que depende}.
"""


class Adaptador:
    nome = "abstrato"

    def formulacoes(self, D, Pi):
        raise NotImplementedError

    def elimina(self, restricao, formulacao):
        return False

    def construir(self, formulacao, D, Pi, contexto):
        raise NotImplementedError

    def verificar(self, corpo, formulacao, D, Pi, contexto=None):
        raise NotImplementedError

    def restricoes(self, veredito, formulacao, D, Pi):
        return []

    def medidas_de_objetivo(self, veredito):
        return veredito.get("medidas", {})

    def exportar(self, corpo, formulacao, pasta, D=None, Pi=None, ver=None):
        return []

    def conferir_exportado(self, arquivos, corpo, formulacao, D=None, Pi=None, ver=None):
        return None, "sem conferência de exportação neste adaptador"
