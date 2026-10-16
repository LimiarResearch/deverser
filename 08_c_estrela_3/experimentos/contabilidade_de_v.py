# -*- coding: utf-8 -*-
import math
import numpy as np
CLASSES_DA_EDICAO = ('quebra', 'neutra', 'muito_pior', 'pior', 'igual_na_distancia', 'melhora')
LIXO_DA_EDICAO = ('quebra', 'neutra', 'muito_pior')
LIXO_DA_SEMENTE = ('quebra', 'neutra')
MUITO_PIOR_PADRAO = 1000
FINALIDADE_SEM_ROTULO = 'sem rótulo'
FINALIDADE_TESTEMUNHAS = 'testemunhas (comparação, à parte)'
FINALIDADE_REMEDIDA_DO_ESTOURO = 'remedidas do estouro (sozinhas)'

def classe_da_edicao(pai_ver, ver, muito_pior=MUITO_PIOR_PADRAO):
    if ver['estado'] != 'ok':
        return 'quebra'
    d_pai, d_filho = (int(pai_ver['distancia']), int(ver['distancia']))
    iguais = np.allclose(np.asarray(ver['valores'], np.float32), np.asarray(pai_ver['valores'], np.float32), rtol=0.0, atol=1e-12, equal_nan=True)
    if iguais and d_filho == d_pai:
        return 'neutra'
    delta = d_filho - d_pai
    if delta < 0:
        return 'melhora'
    if delta == 0:
        return 'igual_na_distancia'
    return 'muito_pior' if delta >= int(muito_pior) else 'pior'

def e_lixo(classe, semente=False):
    return classe in (LIXO_DA_SEMENTE if semente else LIXO_DA_EDICAO)

def _erro_padrao(d):
    d = np.asarray(d, np.float64)
    return float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else float('nan')
PREFIXOS_DA_BUSCA = ('rodadas', 'sementes', 'reinício')

def custo_fixo_da_disciplina(por_finalidade):
    busca = sum((int(v) for k, v in por_finalidade.items() if str(k).startswith(PREFIXOS_DA_BUSCA)))
    remed = int(por_finalidade.get(FINALIDADE_REMEDIDA_DO_ESTOURO, 0))
    fora = {str(k): int(v) for k, v in por_finalidade.items() if not str(k).startswith(PREFIXOS_DA_BUSCA) and k not in (FINALIDADE_TESTEMUNHAS, FINALIDADE_REMEDIDA_DO_ESTOURO)}
    total = busca + remed + sum(fora.values())
    return {'na_busca': int(busca), 'fora_da_busca': int(sum(fora.values())), 'remedidas_do_estouro': remed, 'fracao_fora': round(sum(fora.values()) / max(1, total), 4), 'fora_por_finalidade': dict(sorted(fora.items(), key=lambda kv: -kv[1])), 'o_que_e': 'o custo fixo que uma busca sem esses laços (a evolução regularizada, por exemplo) não paga; a comparação justa com ela olha a busca e o total'}

class GastoDeV:

    def __init__(self):
        self.por_finalidade = {}

    def contar(self, finalidade, n):
        self.por_finalidade[finalidade] = self.por_finalidade.get(finalidade, 0) + int(n)

    def total_da_busca(self):
        return int(sum((v for k, v in self.por_finalidade.items() if k != FINALIDADE_TESTEMUNHAS)))

    def das_testemunhas(self):
        return int(self.por_finalidade.get(FINALIDADE_TESTEMUNHAS, 0))

    def total(self):
        return int(sum(self.por_finalidade.values()))

    def sem_rotulo(self):
        return int(self.por_finalidade.get(FINALIDADE_SEM_ROTULO, 0))

    def para_json(self):
        return dict(self.por_finalidade)

    @classmethod
    def de_json(cls, d):
        g = cls()
        g.por_finalidade = {str(k): int(v) for k, v in (d or {}).items()}
        return g

    def relatorio(self, consultas_desta_sessao=None, avaliador_medidos=None, por_braco=None, por_fonte=None):
        out = {'por_finalidade': dict(sorted(self.por_finalidade.items())), 'total_da_busca': self.total_da_busca(), 'testemunhas_a_parte': self.das_testemunhas(), 'total_consultado': self.total(), 'consultas_sem_rotulo': self.sem_rotulo(), 'orcamento_para_igualar_as_testemunhas_ajustadas': self.total_da_busca()}
        out['custo_fixo_da_disciplina'] = custo_fixo_da_disciplina(self.por_finalidade)
        if por_braco:
            out['rodadas_por_braco'] = por_braco
        if por_fonte:
            out['sementes_por_fonte'] = por_fonte
        if avaliador_medidos is not None and consultas_desta_sessao is not None:
            out['conferencia_desta_sessao'] = {'o_condutor_perguntou': int(consultas_desta_sessao), 'o_avaliador_recebeu': int(avaliador_medidos), 'bate': bool(int(consultas_desta_sessao) == int(avaliador_medidos))}
        out['obs'] = 'toda consulta a V passa por um lugar só e leva rótulo; o pré-treino (o levantamento da intenção) e as auditorias de integridade estão na conta da busca; as testemunhas ficam à parte, mas entram no total que o avaliador viu; as testemunhas ajustadas da prova (V2-9) recebem o MESMO número de medidas que o total da busca, pré-treino incluído'
        return out

class LixoDasEdicoes:

    def __init__(self, muito_pior=MUITO_PIOR_PADRAO):
        self.muito_pior = int(muito_pior)
        self.tabela = {}
        self.por_rodada = []

    @staticmethod
    def _chave(braco, origem):
        return f'{braco}|{origem}'

    def contar(self, braco, origem, pai_ver, ver, paga):
        c = self.tabela.setdefault(self._chave(braco, origem), dict.fromkeys(('pagas', 'repetidas') + CLASSES_DA_EDICAO, 0))
        if not paga:
            c['repetidas'] += 1
            return None
        cls = classe_da_edicao(pai_ver, ver, self.muito_pior)
        c['pagas'] += 1
        c[cls] += 1
        return cls

    def fechar_rodada(self, por_braco):
        r = {b: sum((1 for k in cl if e_lixo(k))) / len(cl) for b, cl in por_braco.items() if cl}
        self.por_rodada.append(r)
        del self.por_rodada[:-20000]

    def _somar(self, filtro):
        tot = dict.fromkeys(('pagas', 'repetidas') + CLASSES_DA_EDICAO, 0)
        for chave, c in self.tabela.items():
            braco, origem = chave.split('|', 1)
            if filtro(braco, origem):
                for k, v in c.items():
                    tot[k] += v
        return tot

    def _linha(self, tot, semente=False):
        pagas = max(tot['pagas'], 1)
        lixo = sum((tot[k] for k in (LIXO_DA_SEMENTE if semente else LIXO_DA_EDICAO)))
        out = {k: tot[k] for k in ('pagas', 'repetidas') + CLASSES_DA_EDICAO}
        out['lixo'] = int(lixo)
        out['taxa_de_lixo'] = round(lixo / pagas, 4) if tot['pagas'] else None
        out['taxa_de_edicoes_que_nao_mudam_nada'] = round(tot['neutra'] / pagas, 4) if tot['pagas'] else None
        out['taxa_de_quebra'] = round(tot['quebra'] / pagas, 4) if tot['pagas'] else None
        out['taxa_de_melhora'] = round(tot['melhora'] / pagas, 4) if tot['pagas'] else None
        return out

    def por_braco(self):
        bracos = sorted({k.split('|', 1)[0] for k in self.tabela})
        return {b: self._linha(self._somar(lambda br, o, b=b: br == b), semente=b.startswith('semente')) for b in bracos}

    def por_origem(self):
        origens = sorted({k.split('|', 1)[1] for k in self.tabela})
        return {o: self._linha(self._somar(lambda br, org, o=o: org == o), semente=o == 'semente') for o in origens}

    def comparar(self, a='aprendida', b='cega', minimo=5):
        d = [r[a] - r[b] for r in self.por_rodada if a in r and b in r]
        if len(d) < minimo:
            return None
        m, ep = (float(np.mean(d)), _erro_padrao(d))
        if not math.isfinite(ep):
            return None
        veredito = 'pior' if m - 2 * ep > 0 else 'ganho' if m + 2 * ep < 0 else 'nulo'
        return {'rodadas_pareadas': len(d), 'diferenca_da_fracao_de_lixo': round(m, 5), 'erro_padrao': round(ep, 5), 'veredito': veredito}

    def alarme(self):
        c = self.comparar('aprendida', 'cega')
        return (bool(c is not None and c['veredito'] == 'pior'), c)

    def relatorio(self):
        ligado, comp = self.alarme()
        return {'definicao': {'quebra': 'estouro de tempo, erro ou oráculo (V não mediu)', 'neutra': 'os mesmos valores de cláusula e a mesma distância que o pai', 'muito_pior': f'a distância subiu {self.muito_pior} milésimos (uma cláusula inteira) ou mais', 'pior': 'subiu menos que isso', 'igual_na_distancia': 'os valores mudaram e a distância ficou igual', 'melhora': 'a distância desceu', 'lixo': 'quebra + neutra + muito_pior (numa semente, só quebra + neutra: a distância total subir é o esperado, emenda 10)', 'pagas': 'edições cuja foto era nova e custou uma consulta a V', 'repetidas': 'edições cuja foto o arquivo já tinha (não custaram V)'}, 'por_braco': self.por_braco(), 'por_origem_da_edicao': self.por_origem(), 'aprendida_contra_cega': comp, 'alarme_a_escrita_aprendida_gasta_mais_lixo_que_a_cega': ligado, 'obs': 'legal não é útil: toda sequência de bits é um programa legal, e o que a corrida gasta de V em edição que não ensina nem aproxima é medido aqui, por braço e por origem, e não suposto'}

    def para_json(self):
        return {'muito_pior': self.muito_pior, 'tabela': self.tabela, 'por_rodada': self.por_rodada[-20000:]}

    @classmethod
    def de_json(cls, d, muito_pior=MUITO_PIOR_PADRAO):
        x = cls(muito_pior)
        if d:
            x.tabela = {k: {kk: int(vv) for kk, vv in v.items()} for k, v in d.get('tabela', {}).items()}
            x.por_rodada = [{k: float(v) for k, v in r.items()} for r in d.get('por_rodada', [])]
        return x
