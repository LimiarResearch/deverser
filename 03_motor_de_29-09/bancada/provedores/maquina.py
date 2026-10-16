"""O provedor de Π do modo "Design for a machine": mede a máquina de destino, local ou por SSH, e devolve os números com procedência.

Um alvo é a máquina e o interpretador em que o artefato vai rodar. O executor do adaptador vai até o alvo (copiado uma vez, conferido
pelo hash) e roda lá, com o Python de lá: o que existe ou falta no alvo (o NumPy, por exemplo) é medido, e não suposto.
"""
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time

from bancada.nucleo.modelo import Pi


class Alvo:
    def __init__(self, id, tipo="local", python=None, host=None, chave=None, pasta_remota=None, descricao=""):
        self.id, self.tipo, self.descricao = id, tipo, descricao
        self.python = python or (sys.executable if tipo == "local" else "python3")
        self.host, self.chave, self.pasta = host, chave, pasta_remota
        self._copiados = {}
        self.quedas_de_rede = []

    def _ssh(self):
        return ["ssh", "-i", os.path.expanduser(self.chave), "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", self.host]

    def _garantir(self, arquivo):
        """Copia o arquivo para o alvo quando ele ainda não está lá com o mesmo hash."""
        with open(arquivo, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        destino = f"{self.pasta}/{os.path.basename(arquivo)}"
        if self._copiados.get(arquivo) == h:
            return destino
        r = self._rodar(self._ssh() + [f"mkdir -p {self.pasta} && sha256sum {destino} 2>/dev/null | cut -c1-64"], 60)
        if r.stdout.strip() != h:
            r = self._rodar(["scp", "-i", os.path.expanduser(self.chave), "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-q", arquivo, f"{self.host}:{destino}"], 180)
            if r.returncode != 0:
                raise RuntimeError(f"não consegui copiar {arquivo} para o alvo depois de tentar de novo: {r.stderr[-300:]}")
        self._copiados[arquivo] = h
        return destino

    def _rodar(self, cmd, timeout):
        """Um comando de rede com reenvio: uma conexão que cai (saída 255) ou um tempo esgotado é tentado de novo, com espera
        crescente, e cada queda fica contada."""
        for espera in (15, 30, 60, None):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if r.returncode != 255 or espera is None:
                    return r
                motivo = r.stderr.strip()[-200:]
            except subprocess.TimeoutExpired:
                if espera is None:
                    return subprocess.CompletedProcess(cmd, 255, "", f"tempo esgotado ({timeout} s)")
                motivo = f"tempo esgotado ({timeout} s)"
            self.quedas_de_rede.append({"stderr": motivo, "espera_s": espera})
            time.sleep(espera)

    def enviar(self, arquivo):
        """Põe o arquivo no alvo e devolve o caminho dele lá (no alvo local, o próprio caminho)."""
        return os.path.abspath(arquivo) if self.tipo == "local" else self._garantir(arquivo)

    def executar(self, arquivo, *args, timeout=600):
        """Roda `arquivo` (um script autossuficiente) no alvo e devolve o JSON da última linha da saída."""
        if self.tipo == "local":
            r = subprocess.run([self.python, "-B", arquivo, *map(str, args)], capture_output=True, text=True, timeout=timeout,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        else:
            destino = self._garantir(arquivo)
            cmd = " ".join([self.python, "-B", destino, *(shlex.quote(str(x)) for x in args)])
            # a rede é ambiente: uma conexão que cai (o ssh sai com 255, ou o tempo esgota) é tentada de novo, e cada queda fica contada
            r = self._rodar(self._ssh() + [cmd], timeout)
        if r.returncode != 0:
            return {"erro": "execucao", "codigo": r.returncode, "stderr": r.stderr[-800:]}
        return json.loads(r.stdout.strip().splitlines()[-1])

    def descrever(self):
        return {"id": self.id, "tipo": self.tipo, "python": self.python, "host": self.host, "descricao": self.descricao}


def medir_perfil(alvo, executor):
    """O Π da máquina de destino, medido lá."""
    p = alvo.executar(executor, "perfil")
    agora = dt.datetime.now().astimezone().isoformat(timespec="seconds")

    def medido(valor, unidade, metodo, incerteza=None):
        return {"valor": valor, "unidade": unidade, "tipo": "medido", "incerteza": incerteza, "metodo": metodo,
                "fonte": f"executor no alvo {alvo.id}", "licenca": None, "data": agora, "vale_para": {"maquina": alvo.id}}
    numeros = {
        "maquina_id": {"valor": alvo.id, "unidade": None, "tipo": "escolha", "incerteza": None, "metodo": "o criador escolheu o alvo",
                       "fonte": "criador", "licenca": None, "data": agora, "vale_para": {"maquina": alvo.id}},
        "python_versao": medido(p["python"], None, "platform.python_version() no alvo"),
        "python_implementacao": medido(p["implementacao"], None, "platform.python_implementation() no alvo"),
        "sistema": medido(p["sistema"], None, "platform.system() no alvo"),
        "numpy_disponivel": medido(p["numpy"] is not None, None, "import numpy no alvo"),
        "numpy_versao": medido(p["numpy"], None, "numpy.__version__ no alvo"),
        "cpus": medido(p["cpus"], "núcleos lógicos", "os.cpu_count() no alvo"),
        "alimentacao": medido(p.get("alimentacao"), None, "GetSystemPowerStatus no Windows, /sys/class/power_supply no Linux"),
        "ram_total_mb": medido(p.get("ram_total_mb"), "MiB", "sysconf ou GlobalMemoryStatusEx no alvo"),
        "ram_livre_mb": medido(p.get("ram_livre_mb"), "MiB", "sysconf ou GlobalMemoryStatusEx no alvo, no instante da medida"),
        "ns_por_insercao_em_conjunto": medido(p["ns_por_insercao_em_conjunto"][0], "ns", "set() de 100 mil inteiros, 7 repetições: mediana, intervalo mín-máx",
                                              p["ns_por_insercao_em_conjunto"][1:]),
        "ns_por_hash_splitmix": medido(p["ns_por_hash_splitmix"][0], "ns", "splitmix64 em Python puro, 20 mil chamadas, 7 repetições: mediana, intervalo mín-máx",
                                       p["ns_por_hash_splitmix"][1:]),
    }
    return Pi({"provedor": "maquina", "alvo": alvo.descrever(), "numeros": numeros, "processador": p.get("processador")})
