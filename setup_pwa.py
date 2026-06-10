# -*- coding: utf-8 -*-
import os
import shutil

base = r"c:/Users/dandr/OneDrive/Desktop/rapportini pro"
static_dir = os.path.join(base, "rapportini-pro", "static")
os.makedirs(static_dir, exist_ok=True)

# 1) Copia LOGO.jpg come logo-192.png e logo-512.png
logo_candidates = [
    os.path.join(base, "rapportini-pro", "LOGO.jpg"),
    os.path.join(base, "rapportini-pro", "logo.jpeg"),
    os.path.join(base, "rapportini-pro", "LOGO.JPEG"),
    os.path.join(base, "LOGO.jpg"),
    os.path.join(base, "logo.jpeg"),
]
src = None
for c in logo_candidates:
    if os.path.exists(c):
        src = c
        break

if src:
    for dst_name in ("logo-192.png", "logo-512.png"):
        dst = os.path.join(static_dir, dst_name)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"OK: copiato {src} -> {dst}")
        else:
            print(f"SKIP: {dst} gia esiste")
else:
    print("ERRORE: nessun LOGO.jpg trovato")

# 2) Modifica app.py: aggiungi meta tag PWA dopo st.set_page_config
fp = os.path.join(base, "rapportini-pro", "app.py")
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

pwa_markers = [
    "st.set_page_config(page_title=\"Rapportini Pro - D'Andrea Angelo E.C.\", page_icon=\"\U0001f4cb\", layout=\"centered\")",
]
# Purtroppo potrebbe esserci encoding diverso. Cerco con un marker semplice.
simple_marker = 'st.set_page_config(page_title="Rapportini Pro - D\'Andrea Angelo E.C.", page_icon="📋", layout="centered")'

if simple_marker in content and "apple-mobile-web-app" not in content:
    pwa_block = simple_marker + """

# --- META TAG PWA (per installazione come app su smartphone) ---
st.markdown('''
<link rel="manifest" href="./static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Rapportini Pro">
<meta name="theme-color" content="#4f8bf9">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="apple-touch-icon" href="./static/logo-192.png">
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('./static/sw.js').then(function(reg) {
      console.log('SW OK:', reg.scope);
    }).catch(function(err) {
      console.warn('SW err:', err);
    });
  });
}
</script>
''', unsafe_allow_html=True)
"""
    content = content.replace(simple_marker, pwa_block, 1)
    print("OK: meta tag PWA aggiunti")
elif "apple-mobile-web-app" in content:
    print("SKIP: meta tag PWA gia presenti")
else:
    print("ERRORE: marker non trovato in app.py")

# 3) Aggiungi banner "Installa App" in cima alla sidebar
sidebar_marker = 'st.sidebar.title("📋 Rapportini")'
if sidebar_marker in content and "pwa-install-banner" not in content:
    banner = '# --- BANNER INSTALLA APP (PWA) ---\n' + sidebar_marker
    content = content.replace(sidebar_marker, banner, 1)
    print("OK: marker banner aggiunto (banner visibile verra aggiunto dopo)")
else:
    print("SKIP: banner marker gia presente")

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)

print("Fatto!")
