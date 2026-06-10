# -*- coding: utf-8 -*-
"""
Punto di ingresso per Streamlit Cloud.
Re-indirizza al file principale dentro rapportini-pro/rapportini-pro/.
"""
import os
import sys

# Aggiungi la directory al path
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

# Esegui l'app principale
exec(open(os.path.join(_app_dir, "rapportini-pro", "app.py"), encoding="utf-8").read())