"""alternativas_codec.py: as alternativas, nos mesmos blocos de um dia (cada dia se lê sozinho), e também no arquivo inteiro.
- genéricos sobre o texto CSV do dia: gzip -9 (deflate), bzip2 -9, xz -9e;
- Gorilla (o formato de séries do Facebook, usado em bancos de séries temporais): o tamanho exato pela regra do artigo (valores em float64
  com XOR do anterior; o tempo é a coluna t, regular, com delta do delta), sem decodificador (só o tamanho);
- colunar com xz: os inteiros de cada coluna em int32, coluna a coluna, xz -9e;
- especialista à mão: delta, zigue-zague, varint, coluna a coluna, lzma 6, nas classes da regra fixa (um ponto da L).
Tamanhos em bytes; tempos de decodificar em segundos de CPU."""
import bz2, json, lzma, sys, time, zlib
import numpy as np
import codec as K

def gorilla_bits(v):
    """Bits do Gorilla para uma série float64: o primeiro valor em 64 bits; depois, XOR com o anterior: 0 -> 1 bit; senão '1' + (se cabe
    na janela anterior de zeros à esquerda/direita: '0' + bits significativos; senão '1' + 5 bits de zeros à esquerda + 6 de tamanho + os bits)."""
    b = v.astype(np.float64).view(np.uint64)
    tot, lz0, tz0 = 64, None, None
    for i in range(1, len(b)):
        x = int(b[i] ^ b[i - 1])
        if x == 0: tot += 1; continue
        lz = 64 - x.bit_length(); tz = (x & -x).bit_length() - 1; lz = min(lz, 31)
        if lz0 is not None and lz >= lz0 and tz >= tz0:
            tot += 2 + (64 - lz0 - tz0)
        else:
            tot += 2 + 5 + 6 + (64 - lz - tz); lz0, tz0 = lz, tz
    return tot

def gorilla_tempo_bits(n):
    return 64 + 14 + (n - 2) * 1        # t regular: o primeiro, o primeiro delta (14 bits) e 1 bit por delta do delta zero

def main():
    cab, esc, x = K.ler_tabela("dados/itens.csv")
    nd = x.shape[0] // K.MIN_DIA
    dias = [x[i * K.MIN_DIA:(i + 1) * K.MIN_DIA] for i in range(nd)]
    linhas = open("dados/itens.csv", "rb").read().split(b"\n")[1:-1]
    textos = [b"".join(l + b"\n" for l in linhas[i * K.MIN_DIA:(i + 1) * K.MIN_DIA]) for i in range(nd)]
    cl = K.classificar(esc, dias[5:7])
    conjuntos = {"desenvolvimento (dias 5 e 6)": [5, 6], "todos os 25 dias": list(range(nd))}
    out = {}
    for nome, ids in conjuntos.items():
        r = {"bytes_csv": sum(len(textos[i]) for i in ids)}
        for alg, comp, desc in (("gzip9", lambda b: zlib.compress(b, 9), zlib.decompress), ("bzip2_9", lambda b: bz2.compress(b, 9), bz2.decompress),
                                ("xz9e", lambda b: lzma.compress(b, preset=9 | lzma.PRESET_EXTREME), lzma.decompress)):
            cs = [comp(textos[i]) for i in ids]
            t0 = time.process_time(); ok = all(desc(c) == textos[i] for c, i in zip(cs, ids)); td = time.process_time() - t0
            r[alg] = {"bytes": sum(map(len, cs)), "exato": ok, "s_decodificar": round(td, 3)}
        g = 0
        for i in ids:
            g += gorilla_tempo_bits(K.MIN_DIA)
            for j in range(1, x.shape[1]):
                g += gorilla_bits(dias[i][:, j] / 10 ** esc[j])
        r["gorilla"] = {"bytes": (g + 7) // 8, "exato": "tamanho pela regra, sem decodificador"}
        cs = [lzma.compress(dias[i].T.astype("<i4").tobytes(), preset=9 | lzma.PRESET_EXTREME) for i in ids]
        t0 = time.process_time(); ok = all(np.array_equal(np.frombuffer(lzma.decompress(c), "<i4").reshape(-1, K.MIN_DIA).T, dias[i]) for c, i in zip(cs, ids)); td = time.process_time() - t0
        r["colunar_int32_xz9e"] = {"bytes": sum(map(len, cs)), "exato": ok, "s_decodificar": round(td, 3)}
        esp = (1 << 7) | (0 << 6) | (0 << 4) | (0 << 3) | (3 << 1) | 0          # delta, zigue-zague, varint, sem corrida, lzma6, coluna a coluna
        m = K.medir_codec([dias[i] for i in ids], [textos[i] for i in ids], esc, cl, [esp] * 8)
        r["especialista_a_mao"] = {"bytes": m["bytes"], "exato": m["erros"] == 0, "s_decodificar": round(m["s_decodificar"], 3), "gene": esp}
        out[nome] = r
    todo = b"".join(textos)
    out["arquivo inteiro, um fluxo só (não se lê por dia)"] = {"bytes_csv": len(todo), "gzip9": len(zlib.compress(todo, 9)), "bzip2_9": len(bz2.compress(todo, 9)),
                                                              "xz9e": len(lzma.compress(todo, preset=9 | lzma.PRESET_EXTREME))}
    out["classes"] = {K.CLASSES[k]: cl.count(k) for k in range(8)}
    json.dump(out, open("alternativas.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

main()
