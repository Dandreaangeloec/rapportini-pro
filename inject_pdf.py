# -*- coding: utf-8 -*-
fp = r"c:/Users/dandr/OneDrive/Desktop/rapportini pro/rapportini-pro/app.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

pdf_funcs = r'''# --- FUNZIONI GENERAZIONE PDF (definite qui per evitare NameError) ---
def genera_pdf(dati, mese_sel, cliente_sel, imponibile, flag_iva, perc_iva, flag_reverse):
    pdf = FPDF()
    pdf.add_page()
    logo_path = trova_percorso_logo()
    if logo_path:
        pdf.image(logo_path, x=165, y=10, w=25)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.cell(190, 5, txt="P. IVA: 04154960985 | Cod. Univoco: N92GLON", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225); pdf.line(10, 37, 200, 37); pdf.set_y(44)
    pdf.set_font("Arial", "B", 13); pdf.set_text_color(15, 23, 42)
    titolo_report = f"REPORT ATTIVITA - {mese_sel.upper()}"
    if cliente_sel != "Tutti i clienti": titolo_report += f" ({cliente_sel.upper()})"
    pdf.cell(190, 10, txt=clean_txt(titolo_report), ln=True, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "B", 9); pdf.set_fill_color(241, 245, 249)
    headers = [("Data", 22), ("Cliente", 38), ("Cantiere", 35), ("Ore", 14), ("Tar. Ora", 18), ("Km", 12), ("Tar. Km", 18), ("Spese", 15), ("Totale", 18)]
    for h, w in headers: pdf.cell(w, 8, h, 1, 0, "C", True)
    pdf.ln(8); pdf.set_font("Arial", "", 8)
    for r in dati:
        pdf.cell(22, 8, clean_txt(r["Data"]), 1, 0, "C")
        pdf.cell(38, 8, clean_txt(r["Cliente"])[:22], 1, 0, "L")
        pdf.cell(35, 8, clean_txt(r["Cantiere"])[:20], 1, 0, "L")
        pdf.cell(14, 8, clean_txt(r["Ore"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Tariffa/h"]), 1, 0, "C")
        pdf.cell(12, 8, clean_txt(r["Km"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Tariffa/Km"]), 1, 0, "C")
        pdf.cell(15, 8, clean_txt(r["Spese Extra"]), 1, 0, "C")
        pdf.cell(18, 8, clean_txt(r["Totale Lordo"]), 1, 1, "R")
    pdf.ln(4); pdf.set_font("Arial", "", 10); pdf.cell(125, 7, "", 0, 0)
    pdf.cell(35, 7, clean_txt("Totale Imponibile:"), 0, 0, "R")
    pdf.cell(30, 7, clean_txt("\x80 " + f"{imponibile:,.2f}"), 1, 1, "R")
    calcolo_iva = 0.0
    if flag_reverse:
        pdf.cell(125, 7, "", 0, 0); pdf.set_font("Arial", "I", 9)
        pdf.cell(65, 7, clean_txt("Regime esenzione: Reverse Charge"), 0, 1, "R"); pdf.set_font("Arial", "", 10)
    elif flag_iva:
        calcolo_iva = imponibile * (perc_iva / 100)
        pdf.cell(125, 7, "", 0, 0); pdf.cell(35, 7, clean_txt(f"IVA ({perc_iva}%):"), 0, 0, "R")
        pdf.cell(30, 7, clean_txt("\x80 " + f"{calcolo_iva:,.2f}"), 1, 1, "R")
    totale_generale = imponibile + calcolo_iva
    pdf.ln(2); pdf.set_font("Arial", "B", 11); pdf.set_fill_color(224, 242, 254)
    pdf.cell(125, 9, "", 0, 0); pdf.cell(35, 9, clean_txt("TOTALE DOVUTO:"), 0, 0, "R")
    pdf.cell(30, 9, clean_txt("\x80 " + f"{totale_generale:,.2f}"), 1, 1, "C", True)
    return bytes(pdf.output())

def genera_pdf_note(rapportini_filtrati, mese_sel, cliente_sel):
    pdf = FPDF()
    pdf.add_page()
    logo_path = trova_percorso_logo()
    if logo_path:
        pdf.image(logo_path, x=165, y=10, w=25)
    pdf.set_font("Arial", "B", 14); pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, txt="D'ANDREA ANGELO E.C.", ln=True, align="L")
    pdf.set_font("Arial", "", 9); pdf.set_text_color(100, 116, 139)
    pdf.cell(190, 5, txt="Via Cesare Battisti, 9 - 25043 Breno (BS)", ln=True, align="L")
    pdf.cell(190, 5, txt="P. IVA: 04154960985 | Cod. Univoco: N92GLON", ln=True, align="L")
    pdf.set_draw_color(203, 213, 225); pdf.line(10, 37, 200, 37); pdf.set_y(44)
    pdf.set_font("Arial", "B", 13); pdf.set_text_color(15, 23, 42)
    titolo = f"REGISTRO NOTE E DESCRIZIONI INTERVENTI - {mese_sel.upper()}"
    if cliente_sel != "Tutti i clienti": titolo += " (CLIENTE: " + cliente_sel.upper() + ")"
    pdf.multi_cell(190, 6, txt=clean_txt(titolo), align="L")
    pdf.set_draw_color(148, 163, 184); pdf.line(10, pdf.get_y() + 4, 200, pdf.get_y() + 4); pdf.ln(8)
    pdf.set_font("Arial", "", 10)
    for r in rapportini_filtrati:
        pdf.set_font("Arial", "B", 10); pdf.set_text_color(30, 41, 59); pdf.set_fill_color(241, 245, 249)
        info_blocco = " DATA: " + r["data"] + "   |   CLIENTE: " + r["cliente"] + "   |   CANTIERE: " + r["cantiere"]
        pdf.cell(190, 7, txt=clean_txt(info_blocco), border=1, ln=True, fill=True)
        pdf.set_font("Arial", "", 10); pdf.set_text_color(51, 65, 85); pdf.ln(2)
        testo_nota = r["note"].strip() if "note" in r and r["note"] and str(r["note"]).strip() != "nan" else "Nessuna nota registrata."
        pdf.multi_cell(190, 5, txt=clean_txt("Note: " + testo_nota), border=0)
        pdf.ln(4); pdf.set_draw_color(226, 232, 240); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(4)
    return bytes(pdf.output())

'''

marker = "    return None\n\n# --- SIDEBAR (sempre visibile) ---"
replacement = "    return None\n\n" + pdf_funcs + "# --- SIDEBAR (sempre visibile) ---"
if marker in content:
    content = content.replace(marker, replacement, 1)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: funzioni PDF aggiunte prima della sidebar")
else:
    print("ERRORE: marker non trovato")
