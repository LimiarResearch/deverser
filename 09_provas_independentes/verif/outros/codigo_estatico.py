# -*- coding: utf-8 -*-
"""Conferencias estaticas (sem importar nem executar nada do repositorio).
Uso: python3 -I codigo_estatico.py <raiz main_ro>
So usa ast.parse, tokenize e hashlib sobre os arquivos como texto/bytes."""
import ast
import hashlib
import io
import json
import os
import sys
import tokenize
import zipfile

R = sys.argv[1]


def p(*a):
    return os.path.join(R, *a)


def texto(caminho):
    with open(caminho, encoding='utf-8') as f:
        return f.read()


def arvore(caminho):
    return ast.parse(texto(caminho), filename=caminho)


print('== A. Conta 15: comentarios e docstrings em codigo/')
pasta = p('07_conta_15', 'codigo')
for n in sorted(os.listdir(pasta)):
    s = texto(os.path.join(pasta, n))
    coment = [t.string for t in tokenize.generate_tokens(io.StringIO(s).readline) if t.type == tokenize.COMMENT]
    t = ast.parse(s)
    docs = 0
    for no in ast.walk(t):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if ast.get_docstring(no, clean=False) is not None:
                docs += 1
    print(f'  {n:24s} linhas={s.count(chr(10)):4d} comentarios={coment} docstrings={docs}')

print('\n== B. C*3: a foto atomica (recalculada a mao a partir das constantes de l_ser_lang.py)')
t = arvore(p('08_c_estrela_3', 'experimentos', 'l_ser_lang.py'))
const = {}
for no in t.body:
    if isinstance(no, ast.Assign):
        for alvo in no.targets:
            try:
                v = ast.literal_eval(no.value)
            except Exception:
                continue
            if isinstance(alvo, ast.Name):
                const[alvo.id] = v
            elif isinstance(alvo, ast.Tuple) and isinstance(v, tuple):
                for a, x in zip(alvo.elts, v):
                    const[a.id] = x
K_NOS, BITS_OP, BITS_ARG, BITS_CONST = const['K_NOS'], const['BITS_OP'], const['BITS_ARG'], const['BITS_CONST']
OPS, SECOES = const['OPS'], const['SECOES']
BITS_NO = BITS_OP + 2 * BITS_ARG + BITS_CONST
# cabecalho do tecido, copiado de _montar_campos (n_camadas 2; 3 larguras de 7; 3 ativacoes de 2; 4 numeros de 8;
# lote 2; cada 3; semente 14; pol_padrao 2; 3 init_S de 2; 2 init_U de 2; 2 init_G de 1)
cab = 2 + 3 * 7 + 3 * 2 + 4 * 8 + 2 + 3 + 14 + 2 + 3 * 2 + 2 * 2 + 2 * 1
secoes = sum(1 + K_NOS * BITS_NO + (2 if tipo == 'pol' else 0) for _, tipo in SECOES)
print(f'  N_OPS={len(OPS)} (2^BITS_OP={2 ** BITS_OP}), secoes={len(SECOES)}, nos por secao={K_NOS}, bits por no={BITS_NO}')
print(f'  cabecalho={cab}, secoes={secoes}, total={cab + secoes}')
cap = arvore(p('08_c_estrela_3', 'experimentos', 'c3_capacidade.py'))
for no in cap.body:
    if isinstance(no, ast.Assign) and getattr(no.targets[0], 'id', '') == 'CAPACIDADE':
        print('  c3_capacidade.CAPACIDADE =', ast.literal_eval(no.value))
# conferir que _montar_campos tem exatamente os add() que eu copiei
src = texto(p('08_c_estrela_3', 'experimentos', 'l_ser_lang.py'))
ini = src.index('def _montar_campos')
fim = src.index('CAMPOS, N_BITS')
print('  linhas add( em _montar_campos:', src[ini:fim].count('add('), '(16 no cabecalho do codigo + 4 por secao + rotulo)')

print('\n== C. C*3: o D (clausulas e predicados) contado no codigo')
t = arvore(p('08_c_estrela_3', 'experimentos', 'montar_desafio_motor.py'))
D = [no for no in t.body if isinstance(no, ast.Assign) and getattr(no.targets[0], 'id', '') == 'D'][0]
piso = [e.args[0].value for e in D.value.elts]
print('  D do piso (montar_desafio_motor.D):', len(piso))
t = arvore(p('08_c_estrela_3', 'experimentos', 'desafio_v.py'))
extra_dv = 0
for no in t.body:
    if isinstance(no, ast.AugAssign) and getattr(no.target, 'id', '') == 'CLAUSULAS':
        extra_dv += len(no.value.elts)
print('  desafio_v acrescenta:', extra_dv)
t = arvore(p('08_c_estrela_3', 'experimentos', 'desafio_v_ser.py'))
extra_ser = 0
for no in t.body:
    if isinstance(no, ast.AugAssign) and getattr(no.target, 'id', '') == 'CLAUSULAS':
        extra_ser += len(no.value.elts)
        ids = [e.elts[0].value for e in no.value.elts]
print('  desafio_v_ser acrescenta:', extra_ser, ids)
n_cl = len(piso) + extra_dv + extra_ser
print('  total de clausulas:', n_cl)
# cauda dos predicados em desafio_v._nomes_dos_predicados: contar os range() e as listas literais
src = texto(p('08_c_estrela_3', 'experimentos', 'desafio_v.py'))
fn = [no for no in ast.parse(src).body if isinstance(no, ast.FunctionDef) and no.name == '_nomes_dos_predicados'][0]
cauda = 0
for no in ast.walk(fn):
    if isinstance(no, ast.Call) and getattr(no.func, 'id', '') == 'range':
        cauda += ast.literal_eval(no.args[0])
    if isinstance(no, ast.AugAssign) and isinstance(no.value, ast.List):
        cauda += len(no.value.elts)
print('  cauda dos predicados (alem de falha:/longe:):', cauda, '-> predicados definidos = 2 x', n_cl, '+', cauda, '=', 2 * n_cl + cauda)
print('  N_PREDICADOS (espaco reservado) =', [ast.literal_eval(no.value) for no in ast.parse(src).body if isinstance(no, ast.Assign) and getattr(no.targets[0], 'id', '') == 'N_PREDICADOS'])

print('\n== D. C*3: vidas por familia (lidas no codigo)')
cv = texto(p('08_c_estrela_3', 'saida', 'calculadora', 'desafio', 'carga_vida.py'))
linha = [l for l in cv.splitlines() if l.startswith('FLUXOS')][0]
print('  carga_vida:', linha)
print("  seq = carga(s) + carga(s+1) -> 2 x FLUXOS; ling = gerar_carga(..., 2); tri = comp, fam, reg com 2 e der com 1; age = gerar_carga(s, 2)")
print('  total = 2*2 + 2 + (2+2+2+1) + 2 =', 2 * 2 + 2 + 7 + 2)
selo = json.load(open(p('08_c_estrela_3', 'experimentos', 'banco_da_prova_cega_selo.json'), encoding='utf-8'))
print('  o selo do banco diz vidas_por_familia =', selo['vidas_por_familia'], 'soma', sum(selo['vidas_por_familia'].values()))

print('\n== E. C*3: o selo do banco da prova cega')
for k, arq in (('seq', 'oraculo_banco_seq_s424242.npz'), ('ling', 'oraculo_banco_ling_s424242.npz'), ('der', 'oraculo_banco_der_s424242.npz')):
    h = hashlib.sha256(open(p('08_c_estrela_3', 'experimentos', arq), 'rb').read()).hexdigest()
    print(f'  {arq}: sha256 {h[:16]}... selo {selo["hash_dos_oraculos"][k][:16]}... confere={h == selo["hash_dos_oraculos"][k]}')
corpo = {k: v for k, v in selo.items() if k != 'hash_do_selo'}
h = hashlib.sha256(json.dumps(corpo, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
print('  hash_do_selo recalculado confere =', h == selo['hash_do_selo'])

print('\n== F. C*3: a piscina, o desenvolvimento, eps e os oraculos presentes')
t = arvore(p('08_c_estrela_3', 'experimentos', 'c3_v_da_busca.py'))
src = texto(p('08_c_estrela_3', 'experimentos', 'c3_v_da_busca.py'))
for l in src.splitlines()[:9]:
    if l.startswith(('EPS', 'PISCINA_PADRAO', 'DESENVOLVIMENTO', 'PROIBIDAS')):
        print('  ', l)
piscina = [30000000 + 1009 * i for i in range(24)]
dev = [7391026, 58210473, 913004317]
print('  eps = 2**-17 =', 2.0 ** -17)
exp = os.listdir(p('08_c_estrela_3', 'experimentos'))
for nome, conj in (('piscina (24)', piscina), ('desenvolvimento (3)', dev), ('base', [1])):
    falta = [(s, f) for s in conj for f in ('vidas', 'ling', 'der') if f'oraculo_{f}_s{s}.npz' not in exp]
    print(f'  {nome}: oraculos vidas/ling/der faltando: {falta or "nenhum"}')
extras = sorted(f for f in exp if f.startswith('oraculo_') and not any(f == f'oraculo_{k}_s{s}.npz' for s in piscina + dev + [1] for k in ('vidas', 'ling', 'der')))
print('  outros oraculos:', extras)
for f in sorted(x for x in exp if x.endswith('.npz'))[:3]:
    with zipfile.ZipFile(p('08_c_estrela_3', 'experimentos', f)) as z:
        print('  conteudo de', f, '->', [i.filename for i in z.infolist()])

print('\n== G. C*3: a configuracao contra os campos da classe Config')
cfg = json.load(open(p('08_c_estrela_3', 'config_c3.json'), encoding='utf-8'))
t = arvore(p('08_c_estrela_3', 'experimentos', 'condutor_de_fotos.py'))
campos = set()
for no in ast.walk(t):
    if isinstance(no, ast.ClassDef) and no.name == 'Config':
        for b in no.body:
            if isinstance(b, ast.Assign):
                for a in b.targets:
                    if isinstance(a, ast.Name):
                        campos.add(a.id)
            elif isinstance(b, ast.AnnAssign):
                campos.add(b.target.id)
print('  campos de Config:', len(campos))
print('  chaves da config que nao existem em Config:', [k for k in cfg if k not in campos] or 'nenhuma')

print('\n== H. C*3: perturbacao igual em numpy e C++ (constantes)')
py = texto(p('08_c_estrela_3', 'experimentos', 'l_ser_interp.py'))
cpp = texto(p('08_c_estrela_3', 'experimentos', 'l_ser_nucleo.cpp'))
for c in (11400714819323198485, 13787848793156543929, 10723151780598845931):
    print(f'  {c} ({hex(c)}): no .py={str(c) in py}, no .cpp={hex(c)[2:].upper() in cpp.upper()}')
print('  >>30, >>27, >>31 e >>40 / 16777216 nos dois:', all(x in py for x in ('>> np.uint64(30)', '>> np.uint64(27)', '>> np.uint64(31)', '>> np.uint64(40)', '16777216.0')), all(x in cpp for x in ('z >> 30', 'z >> 27', 'z >> 31', 'z >> 40', '16777216.0')))

print('\n== I. Pecas da 04 comparadas com a C*3 (arvore sintatica, sem docstrings)')


def sem_doc(t):
    for no in ast.walk(t):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and no.body and isinstance(no.body[0], ast.Expr) and isinstance(getattr(no.body[0], 'value', None), ast.Constant) and isinstance(no.body[0].value.value, str):
            no.body = no.body[1:] or [ast.Pass()]
    return t


def defs(t):
    return {no.name: ast.dump(no) for no in t.body if isinstance(no, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))}


a = sem_doc(arvore(p('04_maquina_do_dever_ser_selecao', 'experimentos', 'foto_atomica.py')))
b = sem_doc(arvore(p('08_c_estrela_3', 'experimentos', 'foto_atomica.py')))
print('  foto_atomica 04 x 08: arvore identica =', ast.dump(a) == ast.dump(b))
a = defs(sem_doc(arvore(p('04_maquina_do_dever_ser_selecao', 'experimentos', 'problema_de_d.py'))))
b = defs(sem_doc(arvore(p('08_c_estrela_3', 'experimentos', 'problema_de_d.py'))))
print('  problema_de_d 04 x 08: so na 08 =', sorted(set(b) - set(a)), '; so na 04 =', sorted(set(a) - set(b)), '; comuns diferentes =', [k for k in a if k in b and a[k] != b[k]])
a = defs(sem_doc(arvore(p('04_maquina_do_dever_ser_selecao', 'experimentos', 'variacao.py'))))
b = defs(sem_doc(arvore(p('08_c_estrela_3', 'experimentos', 'escritor_de_fotos.py'))))
comuns = [k for k in a if k in b]
print('  variacao (04) x escritor_de_fotos (08): definicoes comuns', len(comuns), '; iguais', sum(a[k] == b[k] for k in comuns), '; diferentes', [k for k in comuns if a[k] != b[k]], '; so na 04', [k for k in a if k not in b])
h = hashlib.sha256(open(p('08_c_estrela_3', 'experimentos', 'escritor_de_fotos.py'), 'rb').read()).hexdigest()
print('  sha256 do escritor_de_fotos.py da 08:', h, '(o LEIA-ME da 04 cita o do original: ee71d10e...67ff65d)', h.startswith('ee71d10e') and h.endswith('67ff65d'))
a = sem_doc(arvore(p('05_tear_selecao', 'experimentos', 'foto_atomica.py')))
b = sem_doc(arvore(p('08_c_estrela_3', 'experimentos', 'foto_atomica.py')))
print('  foto_atomica 05 x 08: arvore identica =', ast.dump(a) == ast.dump(b))

print('\n== J. Provas: quantas funcoes test_ existem (contagem estatica, nada rodado)')
for d in ('03_motor_de_29-09/testes', '04_maquina_do_dever_ser_selecao/testes', '08_c_estrela_3/testes'):
    for n in sorted(os.listdir(p(d))):
        if n.endswith('.py'):
            t = arvore(p(d, n))
            k = sum(1 for no in ast.walk(t) if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name.startswith('test'))
            print(f'  {d}/{n}: {k}')
