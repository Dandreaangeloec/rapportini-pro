# -*- coding: utf-8 -*-
"""
Punto di ingresso per Streamlit Cloud.
Re-indirizza al file principale dentro rapportini-pro/rapportini-pro/.
"""
import os
import sys

# Aggiungi la directory al path (per google_config.py e altri moduli)
_app_dir = os.path.dirname(os.path.abspath(__file__))
_app_sub = os.path.join(_app_dir, "rapportini-pro")
for p in [_app_dir, _app_sub]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Esegui l'app principale
exec(open(os.path.join(_app_sub, "app.py"), encoding="utf-8").read())
