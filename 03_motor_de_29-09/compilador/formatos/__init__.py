"""Os formatos de artefato que o motor sabe gravar e conferir, cada um num módulo fora do núcleo.

A função exportar da IA devolve um dicionário; cada chave que é o nome de um formato registrado aqui vai para o módulo dele, que grava os
arquivos e os confere. Um formato novo é um módulo novo com gravar(pasta, conteudo) -> {"conferido", "erros", "arquivos", ...}; o núcleo
não muda. As chaves "arquivos" (texto gravado como está) e "descricao" são do núcleo e valem para qualquer artefato.
"""
import importlib

REGISTRADOS = ("primitivas",)


def gravar(nome, pasta, conteudo):
    return importlib.import_module(f"{__name__}.{nome}").gravar(pasta, conteudo)
