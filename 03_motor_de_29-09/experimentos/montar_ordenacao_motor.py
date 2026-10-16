"""Monta as rotinas curtas de ordenação (n = 6 e n = 8) para o motor fechado na VPS, com as respostas que a IA dá pelo criador, cada uma
marcada. Decisão de 29/09/2026: um corpo digital num meio real, que exercita as voltas da fórmula; o laço muda quando a busca empaca, sem ciclo fixo.

  python -B -m experimentos.montar_ordenacao_motor [ruido_medido]
"""
import itertools
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = "/home/iro/bancada-criacao/venv/bin/python"

# as redes conhecidas de menor tamanho (lembradas pela IA; cada uma só entra se passar no princípio 0-1 abaixo)
OTIMAS = {6: [(0, 5), (1, 3), (2, 4), (1, 2), (3, 4), (0, 3), (2, 5), (0, 1), (2, 3), (4, 5), (1, 2), (3, 4)],
          7: [(0, 6), (2, 3), (4, 5), (0, 2), (1, 4), (3, 6), (0, 1), (2, 5), (3, 4), (1, 2), (4, 6), (2, 3), (4, 5), (1, 2), (3, 4), (5, 6)],
          8: [(0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7), (0, 1), (2, 3), (4, 5), (6, 7), (2, 4), (3, 5), (1, 4), (3, 6), (1, 2), (3, 4), (5, 6)]}


def ordena(n, rede):
    """O princípio 0-1: uma rede de comparadores ordena tudo se ordena os 2^n vetores de zeros e uns."""
    for x in itertools.product((0, 1), repeat=n):
        v = list(x)
        for i, j in rede:
            if v[i] > v[j]:
                v[i], v[j] = v[j], v[i]
        if any(v[q] > v[q + 1] for q in range(n - 1)):
            return False
    return True


def batcher(n):
    p = 1
    while p < n:
        p *= 2
    out = []
    t = 1
    while t < p:
        k = t
        while k >= 1:
            for j in range(k % t, p - k, 2 * k):
                for i in range(min(k, p - j - k)):
                    a, b = i + j, i + j + k
                    if (a // (2 * t)) == (b // (2 * t)) and b < n:
                        out.append((a, b))
            k //= 2
        t *= 2
    return out


def insercao(n):
    return [(j - 1, j) for i in range(1, n) for j in range(i, 0, -1)]


CANDIDATO = '''
def _niveis(rede, n):
    ultimo, out = [0] * n, []
    for i, j in rede:
        nv = max(ultimo[i], ultimo[j]) + 1
        ultimo[i] = ultimo[j] = nv
        out.append(nv)
    return out


def executar(entrada, base, variante, registradores, taxa_de_mutacao=None, pecas=None, **genes):
    import ferramenta_ordenacao
    n = entrada["n"]
    if pecas is not None:
        # L que compõe: a rede é a própria lista de comparadores
        rede = [(int(q["i"]), int(q["j"])) for q in pecas if q.get("primitiva") == "comparador"]
    else:
        # L0: uma rede conhecida, com a ordem dentro de cada nível (o paralelismo) e a retirada de comparadores como genes
        b = entrada["redes"][base]
        niv = _niveis(b, n)
        mantidos = [k for k in range(len(b)) if not int(genes.get(f"rem_{k}", 0))]
        mantidos.sort(key=lambda k: (niv[k], float(genes.get(f"pri_{k}", 0.5)), k))
        rede = [tuple(b[k]) for k in mantidos]
    r = ferramenta_ordenacao.medir(n, rede, variante, int(registradores), entrada["referencia"], entrada["repeticoes"])
    r["rede"] = [list(c) for c in rede]
    return r
'''
METRICAS = '''def metricas(entrada, saida):
    return {k: saida[k] for k in ("erro_de_ordenacao", "razao_vs_rede", "razao_vs_simd", "razao_vs_melhor", "ciclos_simd", "razao_ref_contra_ref", "ciclos_por_vetor", "ciclos_referencia", "ns_std_sort", "ruido", "comparadores")} | {"efeito_no_meio": {}}
'''
ORACULO = '''import itertools


def conferir(entrada, saida):
    """A integridade da medida, independente do medidor: a rede devolvida é conferida pelo princípio 0-1, e o medidor em C tem de concordar
    (erro zero se e só se a rede ordena, porque os vetores de zeros e uns estão entre os n^n que ele confere). Se a rede ordena ou não, quem
    julga é a cláusula r_correto do D, pela métrica erro_de_ordenacao."""
    n = entrada["n"]
    ordena = True
    for x in itertools.product((0, 1), repeat=n):
        v = list(x)
        for i, j in saida["rede"]:
            if v[i] > v[j]:
                v[i], v[j] = v[j], v[i]
        if any(v[q] > v[q + 1] for q in range(n - 1)):
            ordena = False
            break
    if saida.get("vetores_conferidos") != n ** n:
        return False, "o medidor não conferiu os n^n vetores"
    if ordena != (saida["erro_de_ordenacao"] == 0):
        return False, "o medidor em C e o princípio 0-1 discordam: a medida não é confiável"
    return True, "a medida concorda com o princípio 0-1 (a rede " + ("ordena" if ordena else "não ordena") + ")"
'''


def gravar(pasta, nome, obj):
    with open(os.path.join(pasta, nome), "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def numeros(m):
    return {"numeros": {n: {"clausulas": c, "unidade": u, "grandeza": {"quantidade": n.replace("_", " ")}, "onde": "no alvo", "por_que": p}
                        for n, (c, u, p) in m.items()}}


def main():
    ruido = float(sys.argv[1]) if len(sys.argv) > 1 else None
    piso = float(sys.argv[2]) if len(sys.argv) > 2 else None      # o maior desvio da referência contra a cópia dela mesma, medido
    V = lambda nome, tipo, **k: dict({"nome": nome, "tipo": tipo}, **k)
    for n in (6, 8):
        redes = {"batcher": batcher(n), "insercao": insercao(n)}
        if ordena(n, OTIMAS[n]):
            redes["otima"] = OTIMAS[n]
        for k, rd in redes.items():
            assert ordena(n, rd), (n, k)
        ref = redes.get("otima") or redes["batcher"]
        maxc = max(len(r) for r in redes.values())
        comum = [V("base", "categoria", valores=sorted(redes)), V("variante", "categoria", valores=["ternario", "mascara", "simd", "simd_imediato"]),
                 V("registradores", "categoria", valores=[0, 1]), V("taxa_de_mutacao", "real", min=0.1, max=0.6)]
        genes = comum + [V(f"rem_{k}", "categoria", valores=[0, 0, 0, 1]) for k in range(maxc)] + [V(f"pri_{k}", "real", min=0.0, max=1.0) for k in range(maxc)]
        carga = f"def gerar_carga(semente):\n    return {json.dumps({'n': n, 'redes': redes, 'referencia': ref, 'repeticoes': 21})}\n"
        base_modelo = {"entradas": [], "carga": carga, "metricas": METRICAS, "oraculo": ORACULO, "semente": 1, "tempo_limite_s": 600,
                       "modelos": [{"id": "principal", "saidas": [{"nome": x, "unidade": "1"} for x in ("erro_de_ordenacao", "razao_vs_rede", "razao_vs_simd", "razao_vs_melhor", "ciclos_simd", "razao_ref_contra_ref", "ciclos_por_vetor",
                                                                                                       "ciclos_referencia", "ns_std_sort", "ruido", "comparadores", "efeito_no_meio")]}],
                       "testes": [], "exportacao": {"codigo": "def exportar(x, p, saidas):\n    return {'arquivos': {'rotina.txt': repr({k: v for k, v in x.items() if not str(k).startswith('_')})}, "
                                                               "'descricao': {'arquetipo': x.get('_arquetipo')}}\n"},
                       "numeros_excluidos": {"latencia_das_instrucoes_de_troca": "entra pela medida do tempo contra a referência no mesmo processo",
                                             "custo_de_desvio_errado": "as rotinas são sem desvio; entra pela medida",
                                             "ruido_da_medida_de_tempo": "medido pelo próprio medidor (ruido) e conferido antes da busca",
                                             "frequencia_do_processador": "cancelada na razão contra a referência medida junto",
                                             "versao_do_gxx": "declarada pelo sha256 do g++ na ferramenta",
                                             "cache_de_instrucoes_de_quem_chama": "premissa: o efeito do tamanho do código no cache de quem chama não é medido nesta versão; vai declarado",
                                             "profundidade_da_rede": "entra pela medida do tempo", "pressao_de_registradores": "entra pela medida do tempo",
                                             "numero_de_comparadores": "entra pela medida (comparadores)"}}
        m0 = dict(base_modelo, dominio={"arquetipos": ["rede"]},
                  representacao={"arquetipos": [{"nome": "rede", "descricao": "uma rede conhecida, com a ordem dentro dos níveis, a retirada de comparadores, a variante da troca e o uso de registradores",
                                                 "variaveis": genes, "codigo": CANDIDATO}]})
        m1 = dict(base_modelo, dominio={"arquetipos": ["rede", "composicao"]},
                  representacao={"arquetipos": m0["representacao"]["arquetipos"],
                                 "composicao": {"primitivas": [{"nome": "comparador", "variaveis": [V("i", "inteiro", min=0, max=n - 1, passo=1), V("j", "inteiro", min=0, max=n - 1, passo=1)]}],
                                                "min_pecas": len(ref) - 2, "max_pecas": 2 * len(ref), "variaveis": comum, "codigo": CANDIDATO,
                                                "descricao": "a rede livre: qualquer lista de comparadores, fora das redes conhecidas"}})
        out = os.path.join(RAIZ, "saida", "calculadora", "ordenacao", f"motor_respostas_{n}")
        os.makedirs(out, exist_ok=True)
        gravar(out, "propor_modelo.json", {"modelo": m0, "motivo": f"as rotinas de {n} elementos: L0 são as redes conhecidas com a ordem e a troca como genes"})
        gravar(out, "revisar_1.json", {"modelo": m1, "motivo": "abertura de L preparada antes da corrida (ordem das causas: L primeiro): a rede livre, uma lista de "
                                                              "comparadores que compõe, para achar topologias fora das redes conhecidas"})
        D = [{"id": "r_correto", "tipo": "rigida", "natureza": "intencao", "enunciado": f"ordena certo todo vetor de {n} inteiros, com empates",
              "teste": {"medida": "erro_de_ordenacao", "op": "<=", "valor": 0, "unidade": "1", "escala": 1.0}},
             {"id": "r_mais_rapida", "tipo": "rigida", "natureza": "intencao",
              "enunciado": "pelo menos 3% mais rápida no alvo que a mais rápida das referências (a rede escalar e a rede SIMD em AVX2), medida no mesmo processo",
              "teste": {"medida": "razao_vs_melhor", "op": "<=", "valor": 0.97, "unidade": "1", "escala": 0.1}},
             {"id": "o_tempo", "tipo": "objetivo", "natureza": "intencao", "enunciado": "a menor razão de tempo contra a rede de referência",
              "teste": {"medida": "razao_vs_melhor", "sentido": "min", "resolucao": 0.01}},
             {"id": "o_tamanho", "tipo": "objetivo", "natureza": "intencao", "enunciado": "o menor número de comparadores", "teste": {"medida": "comparadores", "sentido": "min", "resolucao": 1}}]
        gravar(out, "formular_D.json", {"clausulas": D, "escopo": {"alvo": "vps-local", "n": n, "referencias": "a melhor rede conhecida escrita à mão, a mesma rede em SIMD (AVX2) e o std::sort do libstdc++"},
                                         "ambiguidades": [], "condicoes_de_uso": ["vale para o processador medido; outro processador é outro cenário de U"]})
        gravar(out, "confirmar_D.json", {"clausulas": {c["id"]: {"acao": "confirmar", "justificativa": "o pedido de Gabriel de 29/09; o limite de 3% foi posto pela IA pelo criador"} for c in D}})
        gravar(out, "mapear_D.json", numeros({"latencia_das_instrucoes_de_troca": (["r_mais_rapida"], "ciclos", "o custo de cada troca"),
                                              "custo_de_desvio_errado": (["r_mais_rapida"], "ciclos", "quanto custa a rotina que desvia"),
                                              "ruido_da_medida_de_tempo": (["r_mais_rapida"], "1", "o que é distinguível"),
                                              "frequencia_do_processador": (["r_mais_rapida"], "GHz", "o tempo absoluto"),
                                              "versao_do_gxx": (["r_mais_rapida"], "versão", "o código gerado"),
                                              "cache_de_instrucoes_de_quem_chama": (["r_mais_rapida"], "bytes", "o efeito do corpo no meio")}))
        gravar(out, "mapear_L.json", numeros({"profundidade_da_rede": (["r_mais_rapida"], "níveis", "o paralelismo que o processador aproveita"),
                                              "pressao_de_registradores": (["r_mais_rapida"], "registradores", "quando os valores saem dos registradores"),
                                              "numero_de_comparadores": (["o_tamanho", "r_mais_rapida"], "comparadores", "o trabalho da rotina")}))
        gravar(out, "distinguibilidade.json", {"clausulas": {
            "r_correto": {"distinguivel": True, "prova": "V confere todos os n^n vetores e a rede pelo princípio 0-1", "medida": {"vetores": n ** n}},
            "r_mais_rapida": {"distinguivel": bool(ruido is not None and piso is not None and ruido + piso < 0.03),
                              "prova": "a diferença pedida (3%) passa o ruído da razão mais o desvio da referência contra a cópia dela mesma, os dois medidos na VPS",
                              "medida": {"ruido_medido": ruido, "desvio_ref_contra_ref": piso, "diferenca_pedida": 0.03}}}})
        prob = {"id": f"ordenacao_{n}_motor_vps", "titulo": f"Ordenar {n} inteiros mais rápido", "mundo": "silicio", "execucao": "medida", "tipo": "maquina",
                "intencao": f"Pedido de Gabriel, 29/09/2026: uma rotina sem desvio que ordene {n} inteiros de 32 bits mais rápido, no processador real, que a melhor rede "
                            "conhecida escrita à mão (continuação da AlphaDev, que fez 3 a 5 elementos), pelo motor fechado, com o laço mudando sempre que empacar.",
                "alvos": [{"id": "vps-local", "tipo": "local", "python": PY, "descricao": "a VPS: AMD EPYC, 3 dos 6 núcleos para este problema"}],
                "avaliador": False, "ia_responde_pelo_criador": True, "paralelo_no_alvo": 3, "rodadas": 1, "repeticoes": 1, "mudancas_planejadas": False,
                "orcamento": {"pedidos_ia": 40, "consultas_de_dados": 10, "avaliacoes": 10000000, "candidatos_por_criacao": 60},
                "busca": "concorrencia", "populacao": "sigma", "teto_s_da_concorrencia": 604800, "reformulacoes_max": 5, "conferir_distinguibilidade": True}
        gravar(os.path.join(RAIZ, "protocolos", "calculadora"), f"ordenacao_{n}_motor_vps.json", prob)
        print("ok", n, sorted(redes), "referência", "otima" if "otima" in redes else "batcher", len(ref), "comparadores")


if __name__ == "__main__":
    main()
