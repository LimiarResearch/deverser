# z3, o comparador isolado

- Pacote: `z3-solver` 5.1.0.0, roda `z3_solver-5.1.0.0-py3-none-win_amd64.whl` (17.040.097 bytes), baixada do PyPI em 28/09/2026 com autorização do responsável pela pesquisa.
- sha256 da roda: `1561efd36e06f4cb7cbf11b63a2fba8fc8fdeb9c5754df90c84f9bd7a4864552`.
- `z3.get_version_string()` = 5.1.0.
- Instalado só no ambiente isolado `.venv-z3` (Python 3.13.3 do notebook), sem dependências, a partir da roda guardada: `.venv-z3/Scripts/python -m pip install --no-deps --no-index dados/z3/roda/z3_solver-5.1.0.0-py3-none-win_amd64.whl`.
- A roda não entra no git nem no pacote (é binária e grande); o hash acima permite conferir a mesma roda baixada de novo.
- O z3 não é importado pela bancada. Ele roda num processo à parte (`bancada/adaptadores/mealy/z3_limite.py`), que recebe o problema em JSON e devolve SAT, UNSAT ou desconhecido.
