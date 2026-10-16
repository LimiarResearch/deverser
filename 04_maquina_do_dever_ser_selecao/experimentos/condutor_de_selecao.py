"""A Máquina do Dever-Ser 4.3.1 só com a seleção: a fórmula com a variação às cegas, sem o aprendiz (a condição F0 da fórmula).

A corrida, em uma frase: as fotos atômicas de partida são sorteadas e medidas por V; a cada rodada um pai é escolhido entre as fotos já medidas
(pelo posto de distância a D, ou ao acaso numa fração das rodadas), cada braço propõe `K` filhos do MESMO pai, V mede todos, toda foto medida
fica guardada, e quando uma foto cumpre D inteiro a corrida para e espera o Ok de uma pessoa. V é o único juiz.

  os braços     "cega"      a escrita às cegas da 4.3.1 (`variacao.amostrar_cego`)
                "operador"  o operador de mutação da codificação (`variacao.amostrar_operador`, que chama `codificacao.mutar`)
                "sorteio"   (opcional) fotos novas sorteadas da codificação, sem pai: o acaso puro, a condição R0 da fórmula
  o pai         o mesmo critério da 4.3.1 sem a parte do aprendiz: pelo posto de distância a D (exponencial, entre as `k_melhores`) e, numa
                fração `frac_acaso` das rodadas (nunca menos de 25%), sorteado entre todas as fotos medidas
  a parada      D cumprido (espera o Ok), ou um fusível declarado (`max_rodadas`, `tempo`)
  o registro    `declaracao.json` (a corrida inteira: a autorização, a configuração, a conta de V por finalidade e por braço, a melhor foto e a
                curva), `fotos.jsonl` (cada foto que V mediu, com a origem e o veredito), `eventos.jsonl` e `candidata_<k>.json`

REGRAS (as da 4.3.1):
  - nada é lançado sem `--autorizacao` (quem autorizou e quando); a frase fica na declaração;
  - a codificação passa pela bateria do contrato da foto atômica antes de qualquer medida;
  - se o Problema traz `calibrar()`, a corrida só começa se V passa nos próprios controles; se traz `hash_de_v()`, o hash é conferido na
    partida e no fim;
  - a máquina nunca declara recorde nem entrega a solução sozinha.

Diferente da 4.3.1: não há rede, memória de edições, biblioteca, motivos, piscinas, sementes do aprendiz, catraca nem retomada (uma pasta que já
tem uma corrida é recusada). Esta versão foi escrita em 16/10/2026 a partir da 4.3.1 e não rodou antes dessa data.

  python -B -m experimentos.condutor_de_selecao --problema exemplos.novo_d_do_zero:criar --saida <pasta> --autorizacao "<quem e quando>"
                                               [--semente 2] [--max-rodadas 2000] [--tempo <s>] [--config <json>]

Só numpy e a biblioteca padrão."""
import argparse
import importlib
import json
import os
import sys
import time

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from experimentos import foto_atomica as FA  # noqa: E402
from experimentos import variacao as VA  # noqa: E402

VERSAO = "4.3.1-selecao"
BRACOS_POSSIVEIS = ("cega", "operador", "sorteio")
FRACAO_ACASO_MINIMA = 0.25


class Config:
    """Os números da corrida. Os que vêm da 4.3.1 têm o mesmo valor padrão de lá."""
    semente = 1
    K = 10                          # filhos por braço por rodada (o mesmo orçamento de V para todos os braços)
    bracos = ("cega", "operador")
    n_partida = 64                  # fotos sorteadas de partida
    k_melhores = 200                # o pai por posto vem destas (as de menor distância a D)
    escala_do_posto = 12.0          # o posto do pai é exponencial com esta média
    frac_acaso = 0.25               # a fração das rodadas em que o pai é sorteado entre todas as fotos medidas (nunca menos de 25%)
    max_tentativas_por_pai = 6
    max_rodadas = 0                 # fusível de rodadas (0 = sem teto)
    tempo = None                    # fusível em segundos (None = sem teto)
    declaracao_cada = 300.0         # segundos entre duas declarações parciais
    imprimir_cada = 60.0

    def __init__(self, **kw):
        for k, v in kw.items():
            if not hasattr(Config, k) or k.startswith("_") or k == "para_json":
                raise TypeError(f"configuração desconhecida: {k}")
            setattr(self, k, tuple(v) if k == "bracos" else v)
        ruins = [b for b in self.bracos if b not in BRACOS_POSSIVEIS]
        if ruins or not self.bracos:
            raise ValueError(f"braços desconhecidos {ruins}: os possíveis são {BRACOS_POSSIVEIS}")

    def para_json(self):
        return {k: (list(v) if isinstance(v, tuple) else v) for k in dir(Config) if not k.startswith("_") and k != "para_json" for v in [getattr(self, k)]}


def _gravar(caminho, obj):
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=_json_padrao)
        f.write("\n")
    os.replace(tmp, caminho)


def _json_padrao(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def _texto_dos_bits(bits):
    return "".join(str(int(x)) for x in bits)


class Arquivo:
    """Toda foto que V mediu, guardada (nenhuma é liberada): a foto canônica, o veredito, a origem, o pai e a rodada. Uma foto já medida não é
    medida de novo."""

    def __init__(self, cod):
        self.cod = cod
        self.bits, self.ver, self.origem, self.pai, self.rodada = [], [], [], [], []
        self.indice = {}

    def __len__(self):
        return len(self.bits)

    def buscar(self, bits):
        return self.indice.get(self.cod.chave(bits), -1)

    def adicionar(self, bits, ver, origem, pai, rodada):
        ch = self.cod.chave(bits)
        if ch in self.indice:
            return self.indice[ch], False
        k = len(self.bits)
        self.indice[ch] = k
        self.bits.append(np.asarray(bits, np.uint8))
        self.ver.append(ver)
        self.origem.append(origem)
        self.pai.append(int(pai))
        self.rodada.append(int(rodada))
        return k, True

    def melhores(self, n):
        ids = [k for k, v in enumerate(self.ver) if v["estado"] == "ok"]
        ids.sort(key=lambda k: (self.ver[k]["distancia"], k))
        return ids[:n]

    def gravar(self, caminho):
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            for k, b in enumerate(self.bits):
                v = self.ver[k]
                f.write(json.dumps({"id": k, "chave": int(self.cod.chave(b)), "origem": self.origem[k], "pai": self.pai[k], "rodada": self.rodada[k],
                                    "estado": v["estado"], "distancia": int(v["distancia"]), "nfal": int(v["nfal"]), "classe": int(v["classe"]),
                                    "bits": _texto_dos_bits(b)}, ensure_ascii=False) + "\n")


class Corrida:
    def __init__(self, problema, avaliador, saida, config=None, autorizacao=None, modo="corrida"):
        if not (autorizacao and str(autorizacao).strip()):
            raise PermissionError("sem a autorização (quem autorizou e quando) nada é lançado: a máquina não começa uma corrida sozinha")
        if os.path.exists(os.path.join(saida, "declaracao.json")):
            raise FileExistsError(f"a pasta {saida} já tem uma corrida: esta versão não retoma; use outra pasta")
        self.problema, self.avaliador, self.saida = problema, avaliador, saida
        self.cfg = config or Config()
        self.autorizacao, self.modo = str(autorizacao).strip(), modo
        self.cod = problema.codificacao
        self.mapa = VA.Mapa(self.cod)
        self.g = np.random.default_rng(self.cfg.semente)
        self.fotos = Arquivo(self.cod)
        self.rodada_n = 0
        self.tentativas = {}
        self.melhor = None                          # (distância, id)
        self.curva_da_melhor = []                   # (avaliações de V até ali, distância)
        self.parada = None
        self.candidatas = []
        self.avaliacoes = {}                        # finalidade -> avaliações de V
        self.braco = {b: {"propostas": 0, "repetidas_sem_medida": 0, "avaliacoes_de_V": 0, "melhoras_sobre_o_pai": 0, "soma_da_variacao": 0.0} for b in self.cfg.bracos}
        self.pais = {"acaso": 0, "posto": 0}
        self.hash_de_v = {"partida": None, "fim": None}
        self.calibracao = None
        self.inicio = None
        os.makedirs(saida, exist_ok=True)
        self._eventos = open(os.path.join(saida, "eventos.jsonl"), "a", encoding="utf-8", newline="\n")

    # ------------------------------------------------------------------ V
    def _medir(self, lista_de_bits, finalidade):
        if not lista_de_bits:
            return []
        res = self.avaliador.medir(lista_de_bits)
        if len(res) != len(lista_de_bits):
            raise RuntimeError("o avaliador devolveu um número de resultados diferente do de fotos")
        self.avaliacoes[finalidade] = self.avaliacoes.get(finalidade, 0) + len(lista_de_bits)
        return [self.problema.julgar(r) for r in res]

    def total_de_avaliacoes(self):
        return int(sum(self.avaliacoes.values()))

    def _evento(self, obj):
        obj = dict(obj, rodada=self.rodada_n, segundos=round(self.segundos(), 3))
        self._eventos.write(json.dumps(obj, ensure_ascii=False, default=_json_padrao) + "\n")
        self._eventos.flush()

    def segundos(self):
        return 0.0 if self.inicio is None else time.time() - self.inicio

    # ------------------------------------------------------------------ o arquivo e a candidata
    def _guardar(self, bits, ver, origem, pai=-1):
        k, nova = self.fotos.adicionar(bits, ver, origem, pai, self.rodada_n)
        if nova and ver["estado"] == "ok":
            if self.melhor is None or ver["distancia"] < self.melhor[0]:
                self.melhor = (int(ver["distancia"]), int(k))
                self.curva_da_melhor.append((self.total_de_avaliacoes(), int(ver["distancia"])))
                self._evento({"evento": "melhor", "id": int(k), "distancia": int(ver["distancia"]), "nfal": int(ver["nfal"]), "origem": origem})
            if ver["nfal"] == 0 and ver["distancia"] == 0:
                self._candidata(k, ver)
        return k, nova

    def _candidata(self, k, ver):
        """Uma foto cumpre D inteiro: a corrida para e espera o Ok humano (o escolhido, o veredito e a foto, em bits). O mesmo arquivo da 4.3.1."""
        bits = self.fotos.bits[k]
        _gravar(os.path.join(self.saida, f"candidata_{k}.json"), {"id": int(k), "chave": int(self.cod.chave(bits)),
                                                                  "veredito": {c: ver[c] for c in ("estado", "distancia", "nfal", "classe", "valores")},
                                                                  "bits": _texto_dos_bits(bits), "espera": "o Ok de uma pessoa: a corrida não a entrega nem a declara sozinha"})
        self.candidatas.append(int(k))
        self._evento({"evento": "candidata", "id": int(k), "distancia": int(ver["distancia"])})
        if self.parada is None:
            self.parada = "D cumprido: espera o Ok"

    # ------------------------------------------------------------------ a partida
    def _sortear_distintas(self, n):
        novas, vistas = [], set()
        for _ in range(50 * max(n, 1)):
            if len(novas) >= n:
                break
            b = self.cod.sortear(self.g)
            ch = self.cod.chave(b)
            if ch not in vistas and self.fotos.buscar(b) < 0:
                vistas.add(ch)
                novas.append(b)
        return novas

    def _partida(self):
        novas = self._sortear_distintas(self.cfg.n_partida)
        for b, v in zip(novas, self._medir(novas, "partida (sorteio)")):
            self._guardar(b, v, "sorteio de partida")
        self._evento({"evento": "partida", "fotos_sorteadas": len(novas), "menor_distancia": None if self.melhor is None else self.melhor[0]})

    # ------------------------------------------------------------------ o pai (o critério da 4.3.1 sem a parte do aprendiz)
    def _livres(self):
        ok = [k for k, v in enumerate(self.fotos.ver) if v["estado"] == "ok"]
        if not ok:
            raise RuntimeError("nenhuma foto medida para ser pai")
        livres = [k for k in ok if self.tentativas.get(k, 0) < self.cfg.max_tentativas_por_pai]
        if not livres:                                                        # todos esgotados: volta a valer
            self.tentativas.clear()
            livres = ok
        return livres

    def _escolher_pai(self):
        cfg, g = self.cfg, self.g
        livres = self._livres()
        if g.random() < max(cfg.frac_acaso, FRACAO_ACASO_MINIMA):
            pai, politica = int(livres[g.integers(len(livres))]), "acaso"
        else:
            melhores = [k for k in self.fotos.melhores(cfg.k_melhores) if self.tentativas.get(k, 0) < cfg.max_tentativas_por_pai] or livres
            pai, politica = int(melhores[min(int(g.exponential(cfg.escala_do_posto)), len(melhores) - 1)]), "posto"
        self.pais[politica] += 1
        self.tentativas[pai] = self.tentativas.get(pai, 0) + 1
        return pai, politica

    # ------------------------------------------------------------------ a rodada
    def _propor(self, braco, molde, ja):
        K = int(self.cfg.K)
        if braco == "cega":
            return [c.bits for c in VA.amostrar_cego(molde, self.mapa, K, self.g, ja=ja)]
        if braco == "operador":
            return [c.bits for c in VA.amostrar_operador(molde, self.mapa, K, self.g)]
        return [self.cod.sortear(self.g) for _ in range(K)]                    # "sorteio": o acaso puro, sem pai

    def rodada(self):
        self.rodada_n += 1
        pai, politica = self._escolher_pai()
        molde = VA.Molde(self.mapa, self.fotos.bits[pai], self.fotos.ver[pai])
        propostas = []                                                        # (braço, bits)
        vistas = set()
        for b in self.cfg.bracos:
            ja = set(vistas)
            for filho in self._propor(b, molde, ja):
                self.braco[b]["propostas"] += 1
                ch = self.cod.chave(filho)
                if ch in vistas or self.fotos.buscar(filho) >= 0:             # uma foto já medida não vai a V de novo
                    self.braco[b]["repetidas_sem_medida"] += 1
                    continue
                vistas.add(ch)
                propostas.append((b, filho))
        vers = self._medir([f for _, f in propostas], "rodadas")
        for (b, filho), ver in zip(propostas, vers):
            self.braco[b]["avaliacoes_de_V"] += 1
            k, nova = self._guardar(filho, ver, b, pai=-1 if b == "sorteio" else pai)
            if ver["estado"] == "ok" and b != "sorteio":
                delta = int(ver["distancia"]) - molde.dist
                self.braco[b]["soma_da_variacao"] += float(delta)
                if delta < 0:
                    self.braco[b]["melhoras_sobre_o_pai"] += 1
        return politica

    # ------------------------------------------------------------------ a corrida
    def declaracao(self, final=False):
        return {"maquina": "Máquina do Dever-Ser", "versao": VERSAO, "modo": self.modo, "final": bool(final),
                "autorizacao": self.autorizacao, "problema": self.problema.nome, "codificacao": self.cod.descricao(),
                "clausulas_de_D": [c[0] for c in self.problema.clausulas], "config": self.cfg.para_json(),
                "calibracao_de_V": self.calibracao, "hash_de_V": self.hash_de_v,
                "rodadas": self.rodada_n, "segundos": round(self.segundos(), 3), "fotos_medidas": len(self.fotos),
                "avaliacoes_de_V": {"total": self.total_de_avaliacoes(), "por_finalidade": dict(self.avaliacoes)},
                "bracos": self.braco, "pais": self.pais,
                "melhor": None if self.melhor is None else {"id": self.melhor[1], "distancia": self.melhor[0], "nfal": int(self.fotos.ver[self.melhor[1]]["nfal"]),
                                                             "bits": _texto_dos_bits(self.fotos.bits[self.melhor[1]])},
                "curva_da_melhor": self.curva_da_melhor, "candidatas": self.candidatas, "parada": self.parada,
                "o_que_esta_versao_nao_tem": "o aprendiz (a rede, a memória de edições, a biblioteca, os motivos, as piscinas, as sementes da rede), a catraca e a retomada"}

    def rodar(self):
        cfg = self.cfg
        self.inicio = time.time()
        if callable(getattr(self.problema, "calibrar", None)):
            self.calibracao = self.problema.calibrar()
            if not self.calibracao.get("ok", False):
                self.parada = "V reprovou nos próprios controles: a corrida não começa"
                self._fechar()
                return self
        if callable(getattr(self.problema, "hash_de_v", None)):
            self.hash_de_v["partida"] = self.problema.hash_de_v()
        self._evento({"evento": "inicio", "versao": VERSAO, "autorizacao": self.autorizacao, "config": cfg.para_json()})
        self._partida()
        ultima_decl, ultima_impr = time.time(), time.time()
        while self.parada is None:
            if cfg.max_rodadas and self.rodada_n >= cfg.max_rodadas:
                self.parada = f"fusível: {cfg.max_rodadas} rodadas"
                break
            if cfg.tempo is not None and self.segundos() >= cfg.tempo:
                self.parada = f"fusível: {cfg.tempo} s"
                break
            self.rodada()
            agora = time.time()
            if agora - ultima_decl >= cfg.declaracao_cada:
                _gravar(os.path.join(self.saida, "declaracao.json"), self.declaracao())
                ultima_decl = agora
            if agora - ultima_impr >= cfg.imprimir_cada:
                print(f"rodada {self.rodada_n}: {len(self.fotos)} fotos, menor distância {self.melhor[0] if self.melhor else None}", flush=True)
                ultima_impr = agora
        if callable(getattr(self.problema, "hash_de_v", None)):
            self.hash_de_v["fim"] = self.problema.hash_de_v()
            if self.hash_de_v["fim"] != self.hash_de_v["partida"]:
                self.parada = f"{self.parada}; INTEGRIDADE: o hash de V mudou durante a corrida, e nada dela vale"
        self._fechar()
        return self

    def _fechar(self):
        self.fotos.gravar(os.path.join(self.saida, "fotos.jsonl"))
        _gravar(os.path.join(self.saida, "declaracao.json"), self.declaracao(final=True))
        self._evento({"evento": "fim", "parada": self.parada, "menor_distancia": None if self.melhor is None else self.melhor[0]})
        self._eventos.close()


# ------------------------------------------------------------------ a linha de comando
def carregar(spec):
    """`modulo:funcao` -> `(problema, avaliador)`. A função, sem argumentos, devolve `(problema, avaliador)` (um terceiro item, se houver, é ignorado)."""
    modulo, _, funcao = spec.partition(":")
    if not modulo or not funcao:
        sys.exit(f"RECUSADO: --problema deve ser `modulo:funcao` (veio `{spec}`).")
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    try:
        f = getattr(importlib.import_module(modulo), funcao)
    except (ImportError, AttributeError) as e:
        sys.exit(f"RECUSADO: não achei `{funcao}` em `{modulo}`: {e!r}")
    r = f()
    if not (isinstance(r, (tuple, list)) and len(r) in (2, 3)):
        sys.exit(f"RECUSADO: `{spec}` deve devolver (problema, avaliador).")
    if not hasattr(r[1], "medir"):
        sys.exit("RECUSADO: o avaliador não tem `medir(lista_de_bits)`.")
    return r[0], r[1]


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--problema", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--autorizacao", default=None)
    ap.add_argument("--modo", default="corrida", choices=["corrida", "fumaca"])
    ap.add_argument("--semente", type=int, default=1)
    ap.add_argument("--tempo", type=float, default=None)
    ap.add_argument("--max-rodadas", dest="max_rodadas", type=int, default=0)
    ap.add_argument("--config", default=None, help="um json com campos de `Config` a trocar")
    a = ap.parse_args(argv)
    if not (a.autorizacao and a.autorizacao.strip()):
        sys.exit("RECUSADO: sem a autorização (--autorizacao \"<quem autorizou e quando>\") nada é lançado.")
    problema, avaliador = carregar(a.problema)
    try:
        rel = FA.verificar_codificacao(problema.codificacao)
        print("bateria do contrato da foto atômica:", json.dumps(rel["resumo"], ensure_ascii=False), flush=True)
        if not rel["ok"]:
            sys.exit("RECUSADO: a codificação reprova a bateria do contrato (nenhuma medida foi feita): " + "; ".join(rel["falhas"]))
        kw = json.load(open(a.config, encoding="utf-8")) if a.config else {}
        kw.setdefault("semente", a.semente)
        if a.modo == "fumaca":
            kw.setdefault("tempo", 600.0)
        if a.tempo is not None:
            kw["tempo"] = a.tempo
        if a.max_rodadas:
            kw["max_rodadas"] = a.max_rodadas
        c = Corrida(problema, avaliador, a.saida, Config(**kw), autorizacao=a.autorizacao, modo=a.modo).rodar()
        print("fim:", json.dumps({"parada": c.parada, "rodadas": c.rodada_n, "fotos": len(c.fotos), "avaliacoes_de_V": c.total_de_avaliacoes(),
                                  "menor_distancia": None if c.melhor is None else c.melhor[0], "candidatas": c.candidatas}, ensure_ascii=False), flush=True)
    finally:
        fechar = getattr(avaliador, "fechar", None)
        if callable(fechar):
            fechar()


if __name__ == "__main__":
    main()
