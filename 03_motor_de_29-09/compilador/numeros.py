"""A conferência de um número que a IA trouxe: ele representa a grandeza que o modelo pede? Em que unidade? Com que procedência?

O modelo declara, para cada entrada, o descritor da grandeza que ela exige. O dado vem com o descritor do que ele é. As regras:
- toda chave do descritor exigido tem de estar no descritor do dado, com o mesmo valor (texto sem acento nem caixa; número igual,
  dentro de 1%);
- as chaves especiais:
  - "local" ({"lat", "lon", "raio_km"}): o dado tem de ser de um ponto dentro do raio;
  - "periodo" (["AAAA-MM-DD", "AAAA-MM-DD"]): o dado tem de cobrir o período;
  - "periodo_de_retorno_anos" e "altura_m": números iguais;
- a unidade tem de ter a mesma dimensão da unidade do modelo, e o valor é convertido;
- o tipo que o número recebe vem da fonte: medido (estação, instrumento, medição no alvo); aproximacao (reanálise, modelo publicado,
  estimativa com método); escolha (norma ou valor que o criador adota, com a fonte); hipotese (sem fonte, ou só a IA afirma).
Um dado de fonte oficial que não representa a grandeza é recusado, com o motivo: é o caso do vento médio horário quando o modelo
pede a rajada.
"""
import hashlib
import math
import os
import unicodedata

from .unidades import ErroDeUnidade, converter

TIPO_DA_FONTE = {"medido": "medido", "medicao": "medido", "estacao": "medido", "norma": "escolha", "escolha": "escolha",
                 "reanalise": "aproximacao", "modelo": "aproximacao", "estimativa": "aproximacao", "publicacao": "aproximacao",
                 "calibrado": "calibrado", "ia": "hipotese", "hipotese": "hipotese"}


def _norm(v):
    if isinstance(v, str):
        return unicodedata.normalize("NFKD", v).encode("ascii", "ignore").decode().lower().strip()
    return v


def _dist_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def conferir_grandeza(exigido, dado):
    """Os motivos de recusa (lista vazia: o dado representa a grandeza)."""
    motivos = []
    dado = dado or {}
    for k, v in (exigido or {}).items():
        if k not in dado:
            motivos.append(f"o dado não diz {k} (o modelo exige {v!r})")
            continue
        d = dado[k]
        if k == "local":
            try:
                km = _dist_km(v, d)
                if km > float(v.get("raio_km", 25)):
                    motivos.append(f"o dado é de um ponto a {km:.0f} km do lugar (o modelo aceita {v.get('raio_km', 25)} km)")
            except (KeyError, TypeError, ValueError):
                motivos.append("o local do dado não tem lat e lon")
        elif k == "periodo":
            if not (isinstance(d, (list, tuple)) and d[0] <= v[0] and d[1] >= v[1]):
                motivos.append(f"o dado cobre {d}, e o modelo pede {v}")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            if not isinstance(d, (int, float)) or abs(d - v) > 0.01 * max(abs(v), 1e-9):
                motivos.append(f"{k}: o dado tem {d!r}, e o modelo exige {v!r}")
        elif _norm(d) != _norm(v):
            motivos.append(f"{k}: o dado é {d!r}, e o modelo exige {v!r}")
    return motivos


def aceitar(entrada, candidato, pasta):
    """Confere um candidato a número para uma entrada do modelo. Devolve (número de Π ou None, motivos da recusa)."""
    motivos = conferir_grandeza(entrada.get("grandeza"), candidato.get("grandeza"))
    tipo = TIPO_DA_FONTE.get(_norm(candidato.get("tipo_de_fonte", "hipotese")), "hipotese")
    if not candidato.get("origem") and tipo != "hipotese":
        motivos.append("o dado não diz de onde veio: fica hipótese, e não o tipo que a IA declarou")
        tipo = "hipotese"
    num = {"tipo": tipo, "unidade": entrada.get("unidade"), "grandeza": entrada.get("grandeza"), "metodo": candidato.get("metodo"),
           "fonte": candidato.get("origem"), "data": candidato.get("data"), "vale_para": candidato.get("alcance"),
           "licenca": candidato.get("licenca"), "tipo_de_fonte_declarado": candidato.get("tipo_de_fonte")}
    if entrada.get("forma") == "serie":
        arq = candidato.get("arquivo")
        if not arq or not os.path.exists(os.path.join(pasta, arq)):
            motivos.append("a série não está no arquivo indicado")
            return None, motivos
        with open(os.path.join(pasta, arq), "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        if candidato.get("sha256") and candidato["sha256"] != h:
            motivos.append("o hash do arquivo não bate")
        if motivos:
            return None, motivos
        num.update(valor={"arquivo": arq, "sha256": h}, incerteza=None)
        return num, []
    try:
        v = converter(candidato["valor"], candidato["unidade"], entrada["unidade"])
        inc = converter(candidato.get("incerteza"), candidato["unidade"], entrada["unidade"]) if candidato.get("incerteza") else None
    except (ErroDeUnidade, KeyError, TypeError) as e:
        motivos.append(f"a unidade não serve: {e}")
        return None, motivos
    if motivos:
        return None, motivos
    num.update(valor=v, incerteza=sorted(inc) if inc else None)
    return num, []
