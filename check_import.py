try:
    import sys
    sys.path.insert(0, r"c:/Users/dandr/OneDrive/Desktop/rapportini pro/rapportini-pro")
    import google_config
    print("OK modulo importato")
    print("leggi_clienti_da_gsheets:", hasattr(google_config, "leggi_clienti_da_gsheets"))
    print("scrivi_clienti_su_gsheets:", hasattr(google_config, "scrivi_clienti_su_gsheets"))
except Exception as e:
    import traceback
    traceback.print_exc()
    print("ERRORE:", e)
