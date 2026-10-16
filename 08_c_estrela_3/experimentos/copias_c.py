# -*- coding: utf-8 -*-
import ctypes
import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, 'copias_c.c')
FLAGS = ['-O3', '-march=native', '-shared', '-fPIC', '-std=c99']
_LIB = [None, False]

def _biblioteca():
    if _LIB[1]:
        return _LIB[0]
    _LIB[1] = True
    gcc = shutil.which('gcc')
    if gcc is None:
        return None
    if os.name == 'nt':
        os.add_dll_directory(os.path.dirname(gcc))
    h = hashlib.sha256(open(FONTE, 'rb').read() + ' '.join(FLAGS).encode() + platform.machine().encode())
    h.update(subprocess.run([gcc, '--version'], capture_output=True, text=True).stdout.encode())
    pasta = os.environ.get('COPIAS_C_CACHE') or os.path.join(tempfile.gettempdir(), 'copias_c_cache')
    os.makedirs(pasta, exist_ok=True)
    alvo = os.path.join(pasta, f'libcopias_{h.hexdigest()[:20]}.so')
    if not os.path.exists(alvo):
        tmp = f'{alvo}.{os.getpid()}.tmp'
        r = subprocess.run([gcc, *FLAGS, '-o', tmp, FONTE], capture_output=True, text=True)
        if r.returncode != 0:
            return None
        try:
            os.replace(tmp, alvo)
        except OSError:
            if not os.path.exists(alvo):
                raise
            os.remove(tmp)
    lib = ctypes.CDLL(alvo)
    p = ctypes.POINTER(ctypes.c_float)
    lib.max_corr.argtypes = [p, ctypes.c_int, p, ctypes.c_int, ctypes.c_int, p]
    lib.max_corr.restype = None
    _LIB[0] = lib
    return lib

def max_corr(Wn, Xn):
    if np.asarray(Wn).shape[1] > 32:
        W = np.asarray(Wn, np.float32)
        X = np.asarray(Xn, np.float32)
        out = np.full(len(W), -2.0, np.float32)
        for i in range(0, len(W), 4096):
            for k in range(0, len(X), 4096):
                np.maximum(out[i:i + 4096], (W[i:i + 4096] @ X[k:k + 4096].T).max(1), out=out[i:i + 4096])
        return out
    lib = _biblioteca()
    if lib is None:
        return None
    W = np.ascontiguousarray(Wn, np.float32)
    Xt = np.ascontiguousarray(np.asarray(Xn, np.float32).T)
    out = np.empty(len(W), np.float32)
    p = ctypes.POINTER(ctypes.c_float)
    lib.max_corr(W.ctypes.data_as(p), int(W.shape[0]), Xt.ctypes.data_as(p), int(Xt.shape[1]), int(W.shape[1]), out.ctypes.data_as(p))
    return out
