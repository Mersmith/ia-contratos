"""
Script temporal: Contar cuántos PDFs son CONTRATOS vs BOLETAS
usando la Fase 1 (IA de OpenAI) sobre toda la carpeta digitalizados.
"""

import os
import sys
import time
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

from primera_fase import identificar_documento

BASE_DIR = os.getenv("CARPETA_PDF", r"c:\Users\AYBAR CORP SAC\Desktop\digitalizados")
IGNORAR  = ["worker", ".git", "vendor", "node_modules", "__pycache__", ".env"]
PAUSA    = 3  # segundos entre llamadas a la IA

def main():
    print("=" * 60)
    print(f" CONTEO DE CONTRATOS vs BOLETAS")
    print(f" Carpeta: {BASE_DIR}")
    print("=" * 60)

    total     = 0
    contratos = 0
    boletas   = 0
    errores   = 0
    lista_contratos = []

    for root, dirs, files in os.walk(BASE_DIR):
        if any(x in root.lower() for x in IGNORAR):
            continue

        for file in files:
            if not file.lower().endswith(".pdf"):
                continue

            ruta = os.path.normpath(os.path.join(root, file))
            total += 1
            print(f"\n[{total}] {file}")

            resultado, error = identificar_documento(ruta)

            if error:
                print(f"  [ERROR] {error[:80]}")
                errores += 1
            elif resultado and resultado.get("es_contrato"):
                contratos += 1
                lista_contratos.append(file)
            else:
                boletas += 1

            time.sleep(PAUSA)

    # Resumen
    print("\n" + "=" * 60)
    print(" RESUMEN FINAL")
    print("=" * 60)
    print(f"  Total PDFs encontrados : {total}")
    print(f"  ✅ CONTRATOS           : {contratos}")
    print(f"  🧾 BOLETAS             : {boletas}")
    print(f"  ❌ Errores             : {errores}")
    print("=" * 60)

    if lista_contratos:
        print("\n  Archivos clasificados como CONTRATO:")
        for c in lista_contratos:
            print(f"    - {c}")

if __name__ == "__main__":
    main()
