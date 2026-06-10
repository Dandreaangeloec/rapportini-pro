# -*- coding: utf-8 -*-
fp = r"c:/Users/dandr/OneDrive/Desktop/rapportini pro/rapportini-pro/app.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Inserisci meta tag PWA + link al manifest + registrazione SW subito dopo st.set_page_config
old_config = 'st.set_page_config(page_title="Rapportini Pro - D\'Andrea Angelo E.C.", page_icon="\U0001f4cb", layout="centered")'
# Cerca direttamente la stringa effettiva presente nel file
real_config = 'st.set_page_config(page_title="Rapportini Pro - D\'Andrea Angelo E.C.", page_icon="\U0001f4cb", layout="centered")'
pwa_block = (
    real_config + "\n\n"
    "# --- META TAG PWA (per installazione come app su smartphone) ---\n"
    "st.markdown(\n"
    "    '<link rel=\"manifest\" href=\"./static/manifest.json\">',\\n"
    "    '<meta name=\"mobile-web-app-capable\" content=\"yes\">',\\n"
    "    '<meta name=\"apple-mobile-web-app-capable\" content=\"yes\">',\\n"
    "    '<meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\">',\\n"
    "    '<meta name=\"apple-mobile-web-app-title\" content=\"Rapportini Pro\">',\\n"
    "    '<meta name=\"theme-color\" content=\"#4f8bf9\">',\\n"
    "    '<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">',\\n"
    "    '<link rel=\"apple-touch-icon\" href=\"./static/logo-192.png\">',\\n"
    "    unsafe_allow_html=True\\n"
    ")"
)

if real_config in content and "serviceWorker" not in content and "apple-mobile-web-app" not in content:
    content = content.replace(real_config, pwa_block, 1)
    print("OK: meta tag PWA aggiunti")
else:
    print("SKIP: meta tag PWA gia presenti")

# 2) Aggiungi banner installa app nella sidebar
real_sidebar = 'st.sidebar.title("\U0001f4cb Rapportini")'
banner_block = (
    "# --- BANNER INSTALLA APP (PWA) ---\n"
    "st.sidebar.markdown(\n"
    "    '<div id=\"pwa-install-banner\" style=\"display:none; background:linear-gradient(135deg, #4f8bf9, #2563eb); color:white; padding:10px; border-radius:8px; margin-bottom:10px; text-align:center;\">',\\n"
    "    '<div style=\"font-size:15px;\">\U0001f4f2 <strong>Installa Rapportini Pro</strong></div>',\\n"
    "    '<div style=\"font-size:11px; opacity:0.9;\">Aggiungi l\\'app alla schermata Home del telefono</div>',\\n"
    "    '<div style=\"margin-top:8px;\">',\\n"
    "    \"<a href='javascript:void(0)' id='pwa-install-btn' style='background:white; color:#4f8bf9; padding:6px 14px; border-radius:6px; font-weight:bold; text-decoration:none; display:inline-block;' onclick=\\\"var s=document.createElement('script');s.textContent='\\\\'\\\\'+''\\\\'\\\\';document.body.appendChild(s);\\\">Apri menu del browser \u2192 Aggiungi a Home</a>\",\\n"
    "    '</div>',\\n"
    "    '</div>',\\n"
    "    unsafe_allow_html=True\\n"
    ")"
)
if real_sidebar in content and "pwa-install-banner" not in content:
    content = content.replace(real_sidebar, banner_block + "\\n\\n" + real_sidebar, 1)
    print("OK: banner PWA aggiunto")
else:
    print("SKIP: banner gia presente")

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("File salvato")
