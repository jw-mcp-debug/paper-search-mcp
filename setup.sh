#!/usr/bin/env bash
set -e

# 1. Alle PyPI-Abhängigkeiten (paper-search + OPAC)
pip install -r requirements.txt

# 2. PyZ3950 – nicht auf PyPI, Python-3-Fork von GitHub
pip install "git+https://github.com/asl2/PyZ3950.git"

# 3. ccl.py-Stub-Patch (Python-3.12-Kompatibilität)
#    Der Original-CCL-Lexer scheitert beim Import unter Python 3.11+.
#    Da nur PQF genutzt wird, genügt ein Stub mit den zwei Symbolen,
#    die zoom.py referenziert.
CCL_PATH="$(python -c 'import PyZ3950, os; print(os.path.join(os.path.dirname(PyZ3950.__file__), "ccl.py"))')"
cat > "$CCL_PATH" << 'PYEOF'
class QuerySyntaxError(Exception):
    pass


def mk_rpn_query(query):
    raise QuerySyntaxError("CCL deaktiviert; PQF verwenden.")
PYEOF
echo "ccl.py-Stub geschrieben nach: $CCL_PATH"
