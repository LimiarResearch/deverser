"""O formato "primitivas": caixas e cilindros (metros, z para cima) -> glTF, OBJ e PNG, relidos e conferidos.

É um formato registrado em compilador/formatos, fora do núcleo do motor: o motor não sabe de geometria. A função exportar da IA devolve
{"primitivas": [...]}, e este módulo grava os três arquivos e confere o glTF e o OBJ contra as primitivas (tolerância de 1 mm).
- {"tipo": "caixa", "centro": [x, y, z], "dimensoes": [a, b, c], "rotacao_z_graus": 0, "nome", "cor"}
- {"tipo": "cilindro", "de": [x, y, z], "ate": [x, y, z], "raio", "nome", "cor"}
"""
import base64
import json
import math
import os

import numpy as np


def _caixa(p):
    c, (a, b, h) = np.array(p["centro"], float), p["dimensoes"]
    t = math.radians(p.get("rotacao_z_graus", 0))
    R = np.array([[math.cos(t), -math.sin(t), 0], [math.sin(t), math.cos(t), 0], [0, 0, 1]])
    vs, tri = [], []
    for sx, sy, sz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
        vs.append(c + R @ np.array([sx * a / 2, sy * b / 2, sz * h / 2]))
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)):
        tri += [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
    return np.array(vs), tri


def _cilindro(p, lados=16):
    a, b, r = np.array(p["de"], float), np.array(p["ate"], float), float(p["raio"])
    ex = (b - a) / max(np.linalg.norm(b - a), 1e-12)
    ref = np.array([0, 0, 1.0]) if abs(ex[2]) < 0.99 else np.array([1.0, 0, 0])
    ey = np.cross(ref, ex)
    ey /= np.linalg.norm(ey)
    ez = np.cross(ex, ey)
    vs, tri = [], []
    for k in range(lados):
        ang = 2 * math.pi * k / lados
        d = math.cos(ang) * ey + math.sin(ang) * ez
        vs += [a + r * d, b + r * d]
    for k in range(lados):
        i, j = 2 * k, 2 * ((k + 1) % lados)
        tri += [(i, j, i + 1), (j, j + 1, i + 1)]
    return np.array(vs), tri


def malha(p):
    return _caixa(p) if p["tipo"] == "caixa" else _cilindro(p)


def gltf(prims, caminho):
    buf, views, accs, meshes, nodes, mats = bytearray(), [], [], [], [], []
    cores = {}
    for i, p in enumerate(prims):
        v, t = malha(p)
        pos = np.array([[x[0], x[2], -x[1]] for x in v], dtype=np.float32)
        idx = np.array(t, dtype=np.uint32).ravel()
        acc = []
        for arr, alvo, tipo, comp in ((pos, 34962, "VEC3", 5126), (idx, 34963, "SCALAR", 5125)):
            while len(buf) % 4:
                buf.append(0)
            views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": arr.nbytes, "target": alvo})
            buf += arr.tobytes()
            a = {"bufferView": len(views) - 1, "componentType": comp, "count": int(arr.shape[0]), "type": tipo}
            if tipo == "VEC3":
                a["min"], a["max"] = pos.min(axis=0).tolist(), pos.max(axis=0).tolist()
            accs.append(a)
            acc.append(len(accs) - 1)
        cor = tuple(p.get("cor", [0.6, 0.62, 0.64]))
        if cor not in cores:
            cores[cor] = len(mats)
            mats.append({"pbrMetallicRoughness": {"baseColorFactor": list(cor) + [1.0], "metallicFactor": 0.1, "roughnessFactor": 0.6}})
        meshes.append({"name": p.get("nome", f"peca_{i}"), "primitives": [{"attributes": {"POSITION": acc[0]}, "indices": acc[1], "material": cores[cor]}]})
        nodes.append({"name": p.get("nome", f"peca_{i}"), "mesh": i})
    g = {"asset": {"version": "2.0", "generator": "compilador-bancada"}, "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes,
         "meshes": meshes, "accessors": accs, "bufferViews": views, "materials": mats,
         "buffers": [{"byteLength": len(buf), "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(buf)).decode()}]}
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        json.dump(g, f)


def obj(prims, caminho):
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        base = 1
        for i, p in enumerate(prims):
            v, t = malha(p)
            f.write(f"o {p.get('nome', f'peca_{i}')}\n")
            for x in v:
                f.write(f"v {x[0]:.6f} {x[1]:.6f} {x[2]:.6f}\n")
            for a, b, c in t:
                f.write(f"f {a + base} {b + base} {c + base}\n")
            base += len(v)


def conferir(prims, cam_gltf, cam_obj, tol=1e-3):
    erros = []
    with open(cam_gltf, encoding="utf-8") as f:
        g = json.load(f)
    buf = base64.b64decode(g["buffers"][0]["uri"].split(",", 1)[1])
    lidos_g = []
    for nd in g["nodes"]:
        pr = g["meshes"][nd["mesh"]]["primitives"][0]
        a = g["accessors"][pr["attributes"]["POSITION"]]
        bv = g["bufferViews"][a["bufferView"]]
        pos = np.frombuffer(buf, dtype=np.float32, count=a["count"] * 3, offset=bv["byteOffset"]).reshape(-1, 3)
        lidos_g.append(np.array([[p[0], -p[2], p[1]] for p in pos], float))
    grupos, vs = [], []
    with open(cam_obj, encoding="utf-8") as f:
        for l in f:
            if l.startswith("o "):
                grupos.append([])
            elif l.startswith("v "):
                grupos[-1].append([float(x) for x in l.split()[1:4]])
    for nome, lidos in (("glTF", lidos_g), ("OBJ", [np.array(x) for x in grupos])):
        if len(lidos) != len(prims):
            erros.append(f"{nome}: {len(lidos)} peças, esperadas {len(prims)}")
            continue
        for p, v in zip(prims, lidos):
            ve, _ = malha(p)
            if np.abs(v.mean(axis=0) - ve.mean(axis=0)).max() > tol or np.abs((v.max(0) - v.min(0)) - (ve.max(0) - ve.min(0))).max() > tol:
                erros.append(f"{nome}: a peça {p.get('nome')} não bate")
    return not erros, erros


def render(prims, caminho, largura=900, altura=700):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (largura, altura), (238, 240, 236))
    dr = ImageDraw.Draw(img)
    todos = np.vstack([malha(p)[0] for p in prims])
    c = (todos.max(0) + todos.min(0)) / 2
    raio = max(np.linalg.norm(todos - c, axis=1).max(), 1e-6)
    a, e = math.radians(225), math.radians(25)
    d = np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)])
    olho = c + 3.2 * raio * d
    fwd = (c - olho) / np.linalg.norm(c - olho)
    dir_ = np.cross(fwd, [0, 0, 1.0])
    dir_ /= np.linalg.norm(dir_)
    cima = np.cross(dir_, fwd)
    luz = np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8])
    foco = 1.2 * min(largura, altura)

    def proj(p):
        v = p - olho
        z = v @ fwd
        return (largura / 2 + foco * (v @ dir_) / z, altura / 2 - foco * (v @ cima) / z), z
    faces = []
    for p in prims:
        v, t = malha(p)
        cor = np.array(p.get("cor", [0.6, 0.62, 0.64])) * 255
        for tri in t:
            q = [v[k] for k in tri]
            n = np.cross(q[1] - q[0], q[2] - q[0])
            if np.linalg.norm(n) < 1e-12:
                continue
            n /= np.linalg.norm(n)
            pts, zs = zip(*(proj(x) for x in q))
            faces.append((max(zs), pts, tuple(int(x) for x in np.clip(cor * (0.45 + 0.55 * abs(float(n @ luz))), 0, 255))))
    for _, pts, cor in sorted(faces, key=lambda f: -f[0]):
        dr.polygon(pts, fill=cor)
    img.save(caminho)


def gravar(pasta, prims):
    cg, co, cp = (os.path.join(pasta, n) for n in ("objeto.gltf", "objeto.obj", "objeto.png"))
    gltf(prims, cg)
    obj(prims, co)
    render(prims, cp)
    ok, erros = conferir(prims, cg, co)
    return {"conferido": ok, "erros": erros, "pecas": len(prims), "arquivos": ["objeto.gltf", "objeto.obj", "objeto.png"]}
