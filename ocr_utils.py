"""
=============================================================
 FASE 0 — Extracción de Texto por OCR
=============================================================
 Objetivo: Convertir un PDF escaneado a texto plano usando
           Tesseract OCR, página por página.

 Dependencias:
   pip install pytesseract pdf2image pillow

 Tesseract (motor OCR) debe estar instalado:
   https://github.com/UB-Mannheim/tesseract/wiki
   (marcar "Spanish" durante la instalación)

 Uso desde otro módulo:
   from ocr_utils import extraer_texto_pdf
   texto, error = extraer_texto_pdf("ruta/al/archivo.pdf")

 Prueba directa:
   python ocr_utils.py
=============================================================
"""

import sys
import os

import pytesseract
from pdf2image import convert_from_path
from dotenv import load_dotenv

# Cargar configuración del archivo .env
load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────
# CONFIGURACIÓN PARA WINDOWS
# ─────────────────────────────────────────────────────────
# 1. Tesseract: Si no está en el PATH, descomenta la siguiente línea:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 2. Poppler: Necesario para pdf2image. 
POPPLER_PATH = r"C:\poppler\Library\bin" 
# ─────────────────────────────────────────────────────────


def extraer_texto_pdf(ruta_pdf, lang="spa", dpi=300, verbose=True):
    """
    Convierte un PDF a texto usando OCR (Tesseract), página por página.
    """
    if not os.path.isfile(ruta_pdf):
        return None, f"Archivo no encontrado: {ruta_pdf}"

    texto_total = ""

    try:
        if verbose:
            print(f"  [📄] Convirtiendo PDF a imágenes (DPI={dpi})...")

        if POPPLER_PATH and os.path.exists(POPPLER_PATH):
            paginas = convert_from_path(ruta_pdf, dpi=dpi, poppler_path=POPPLER_PATH)
        else:
            paginas = convert_from_path(ruta_pdf, dpi=dpi)

        if verbose:
            print(f"  [📑] Total de páginas: {len(paginas)}")

        for i, pagina in enumerate(paginas, start=1):
            if verbose:
                print(f"  [🔍] OCR página {i}/{len(paginas)}...", end=" ", flush=True)

            texto_pagina = pytesseract.image_to_string(pagina, lang=lang)
            texto_total += texto_pagina + "\n"

            if verbose:
                chars = len(texto_pagina.strip())
                print(f"({chars} caracteres)")

        return texto_total, None

    except Exception as e:
        return None, str(e)


# ═════════════════════════════════════════════════════════
# PRUEBA DIRECTA — ejecuta: python ocr_utils.py
# ═════════════════════════════════════════════════════════
if __name__ == "__main__":

    print("=" * 60)
    print(" FASE 0 — Prueba de OCR con Tesseract")
    print("=" * 60)

    # ── 1. Cargar ruta desde el .env o usar la de por defecto ──
    # Si CARPETA_PDF está en el .env, la usamos.
    BASE_DIR = os.getenv("CARPETA_PDF", r"C:\Users\AYBAR CORP SAC\Desktop\automatizacion\analizar")

    PDF_PRUEBA = BASE_DIR

    # Si se pasa una ruta por argumento, usarla
    if len(sys.argv) > 1:
        PDF_PRUEBA = sys.argv[1]

    # ── 2. Buscar primer PDF ──
    if os.path.isdir(PDF_PRUEBA):
        pdfs_encontrados = []
        for root, _, files in os.walk(PDF_PRUEBA):
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdfs_encontrados.append(os.path.join(root, f))

        if not pdfs_encontrados:
            print(f"[ERROR] No se encontró ningún PDF en: {PDF_PRUEBA}")
            sys.exit(1)

        print(f"\n📂 Buscando en: {PDF_PRUEBA}")
        print(f"👉 Procesando el primero: {os.path.basename(pdfs_encontrados[0])}")
        PDF_PRUEBA = pdfs_encontrados[0]

    # ── 3. Ejecutar OCR ──
    print(f"\n[INICIO OCR] {os.path.basename(PDF_PRUEBA)}\n")
    texto, error = extraer_texto_pdf(PDF_PRUEBA, verbose=True)

    if error:
        print(f"\n[❌ ERROR] {error}")
        sys.exit(1)

    # ── 4. GUARDAR EN ARCHIVO EDITABLE (.txt) ──
    # Creamos una carpeta 'preview' si no existe
    output_folder = "preview"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    nombre_txt = os.path.basename(PDF_PRUEBA).replace(".pdf", ".txt")
    ruta_txt = os.path.join(output_folder, nombre_txt)

    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(texto)

    print(f"\n{'=' * 60}")
    print(f" ✅ PROCESO COMPLETADO")
    print(f"{'=' * 60}")
    print(f"  📄 Texto guardado en : {ruta_txt}")
    print(f"  🔍 Caracteres totales: {len(texto)}")
    print(f"\n  [!] Ya puedes abrir el archivo .txt para editarlo.")
    print(f"{'=' * 60}")
