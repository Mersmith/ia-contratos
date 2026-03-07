import os
import pytesseract
from pdf2image import convert_from_path
from dotenv import load_dotenv

load_dotenv()
POPPLER_PATH = r'C:\poppler\Library\bin'
MAX_PAGES = 30 # Por seguridad

def buscar_pagina_contrato_definitivo(ruta_pdf):
    print(f"Analizando: {ruta_pdf}")
    paginas = convert_from_path(ruta_pdf, dpi=75, poppler_path=POPPLER_PATH)
    for i, pag in enumerate(paginas):
        texto = pytesseract.image_to_string(pag, lang='spa').upper()
        if "VIII." in texto and "FIRMA" in texto:
            print(f"✅ ¡ENCONTRADO! Página {i+1}")
            # print(texto)

pdf = r'C:\Users\AYBAR CORP SAC\Desktop\automatizacion\modelos\FINCA LAS LOMAS CONTRATO B-06.pdf'
buscar_pagina_contrato_definitivo(pdf)
