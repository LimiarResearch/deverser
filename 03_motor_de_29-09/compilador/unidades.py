"""As unidades: dimensão e escala, para converter o que tem a mesma dimensão e recusar o que não tem.

Dimensões: comprimento (m), massa (kg), tempo (s), corrente (A), temperatura (K), quantidade (mol), intensidade (cd), informação
(B, byte) e moeda (BRL, sem câmbio: moedas diferentes não convertem). Uma unidade composta se escreve com * e /, e expoentes com ^:
"kg*m/s^2", "W/m^2", "kWh/m^2/d". Temperatura em °C só converte para °C (o deslocamento da escala não é tratado).
"""
import re

DIMS = ("m", "kg", "s", "A", "K", "mol", "cd", "B", "BRL", "degC")


def _u(escala, **d):
    return (escala, tuple(d.get(k, 0) for k in DIMS))


BASE = {
    "1": _u(1), "": _u(1), "%": _u(0.01), "rad": _u(1), "°": _u(3.141592653589793 / 180), "grau": _u(3.141592653589793 / 180), "sr": _u(1),
    "m": _u(1, m=1), "cm": _u(0.01, m=1), "mm": _u(0.001, m=1), "km": _u(1000, m=1), "um": _u(1e-6, m=1),
    "g": _u(0.001, kg=1), "kg": _u(1, kg=1), "t": _u(1000, kg=1),
    "s": _u(1, s=1), "ms": _u(0.001, s=1), "us": _u(1e-6, s=1), "ns": _u(1e-9, s=1), "min": _u(60, s=1), "h": _u(3600, s=1),
    "d": _u(86400, s=1), "dia": _u(86400, s=1), "ano": _u(365.25 * 86400, s=1), "mes": _u(365.25 * 86400 / 12, s=1),
    "Hz": _u(1, s=-1), "kHz": _u(1e3, s=-1), "MHz": _u(1e6, s=-1), "GHz": _u(1e9, s=-1),
    "N": _u(1, kg=1, m=1, s=-2), "kN": _u(1e3, kg=1, m=1, s=-2),
    "Pa": _u(1, kg=1, m=-1, s=-2), "kPa": _u(1e3, kg=1, m=-1, s=-2), "MPa": _u(1e6, kg=1, m=-1, s=-2), "GPa": _u(1e9, kg=1, m=-1, s=-2),
    "bar": _u(1e5, kg=1, m=-1, s=-2),
    "J": _u(1, kg=1, m=2, s=-2), "kJ": _u(1e3, kg=1, m=2, s=-2), "MJ": _u(1e6, kg=1, m=2, s=-2),
    "Wh": _u(3600, kg=1, m=2, s=-2), "kWh": _u(3.6e6, kg=1, m=2, s=-2), "MWh": _u(3.6e9, kg=1, m=2, s=-2),
    "W": _u(1, kg=1, m=2, s=-3), "kW": _u(1e3, kg=1, m=2, s=-3), "MW": _u(1e6, kg=1, m=2, s=-3),
    "L": _u(0.001, m=3), "l": _u(0.001, m=3), "mL": _u(1e-6, m=3),
    "K": _u(1, K=1), "°C": _u(1, degC=1), "degC": _u(1, degC=1),
    "B": _u(1, B=1), "byte": _u(1, B=1), "bit": _u(0.125, B=1), "kB": _u(1e3, B=1), "MB": _u(1e6, B=1), "GB": _u(1e9, B=1),
    "TB": _u(1e12, B=1), "KiB": _u(1024, B=1), "MiB": _u(2 ** 20, B=1), "GiB": _u(2 ** 30, B=1),
    "BRL": _u(1, BRL=1), "R$": _u(1, BRL=1),
    "kn": _u(0.514444, m=1, s=-1), "mol": _u(1, mol=1), "cd": _u(1, cd=1), "lm": _u(1, cd=1), "lx": _u(1, cd=1, m=-2),
}


class ErroDeUnidade(ValueError):
    pass


def analisar(u):
    """(escala, dimensão) de uma unidade escrita."""
    if u is None:
        raise ErroDeUnidade("unidade ausente")
    u = u.strip().replace(" ", "").replace("·", "*").replace("²", "^2").replace("³", "^3")
    if u in BASE:
        return BASE[u]
    escala, dim = 1.0, [0] * len(DIMS)
    partes = re.split(r"([*/])", u)
    sinal = 1
    for p in partes:
        if p == "*":
            sinal = 1
            continue
        if p == "/":
            sinal = -1
            continue
        if not p:
            continue
        m = re.fullmatch(r"(.+?)(?:\^(-?\d+))?", p)
        nome, exp = m.group(1), int(m.group(2) or 1)
        if nome not in BASE:
            raise ErroDeUnidade(f"unidade desconhecida: {nome!r} em {u!r}")
        e, d = BASE[nome]
        escala *= e ** (exp * sinal)
        dim = [a + b * exp * sinal for a, b in zip(dim, d)]
        sinal = 1 if sinal == 1 else 1   # cada "/" vale só para o termo seguinte
    return escala, tuple(dim)


def mesma_dimensao(a, b):
    return analisar(a)[1] == analisar(b)[1]


def converter(valor, de, para):
    ea, da = analisar(de)
    eb, db = analisar(para)
    if da != db:
        raise ErroDeUnidade(f"dimensões diferentes: {de!r} e {para!r}")
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        return [converter(v, de, para) for v in valor]
    return valor * ea / eb
