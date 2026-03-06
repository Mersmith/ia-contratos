"""
=============================================================
 FASE 1 — Identificación del Documento
=============================================================
 Objetivo: Determinar si un PDF es un CONTRATO o una BOLETA.
 
 Flujo:
  1. Python lee el PDF con PyMuPDF
  2. Intenta extraer texto directamente (gratis)
     - Si hay texto  → lo envía como texto a la IA
     - Si no hay     → convierte página 1 a imagen y la envía
  3. La IA clasifica: ¿es CONTRATO o BOLETA?
  4. Retorna: True (contrato) / False (no es contrato)
=============================================================
"""

import os
import sys
import json
import base64
import fitz  # PyMuPDF
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# Cliente OpenAI
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization=os.getenv("OPENAI_ORGANIZATION"),
    project=os.getenv("OPENAI_PROJECT"),
)

# ─────────────────────────────────────────────
# PASO 1: Leer el PDF con Python
# ─────────────────────────────────────────────
def leer_pdf(pdf_path):
    """
    Intenta extraer texto del PDF.
    Si no tiene texto (escaneado), convierte la página 1 a imagen en base64.
    Retorna: (texto, imagen_base64) — uno de los dos tendrá valor.
    """
    doc = fitz.open(pdf_path)
    
    # Intentar extraer texto de las primeras 2 páginas
    texto_total = ""
    for i in range(min(2, len(doc))):
        texto_total += doc.load_page(i).get_text().strip()
    
    doc.close()

    if len(texto_total) > 50:  # Si tiene suficiente texto real
        print(f"  [📝] PDF con texto seleccionable ({len(texto_total)} caracteres)")
        return texto_total, None
    else:
        print(f"  [🖼️] PDF escaneado. Convirtiendo página 1 a imagen...")
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Alta resolución
        img_bytes = pix.tobytes("png")
        doc.close()
        imagen_b64 = base64.b64encode(img_bytes).decode('utf-8')
        return None, imagen_b64


# ─────────────────────────────────────────────
# PASO 2: Preguntar a la IA si es contrato
# ─────────────────────────────────────────────
PROMPT_CLASIFICACION = """
Analiza este documento de una empresa inmobiliaria peruana (AYBAR CORP S.A.C.).

Determina si es:
A) BOLETA DE VENTA ELECTRÓNICA — comprobante tributario con QR de SUNAT, serie BB01 o B001, tabla de ítems y precios.
B) CONTRATO PREPARATORIO DE COMPRAVENTA — documento legal con cláusulas (PRIMERA, SEGUNDA...), código serie C20241..., logos del proyecto.

Si es tipo B (contrato), extrae:
- cliente: nombre completo del comprador (formato: APELLIDO, NOMBRE)
- lote: identificación del lote (ej: A1-17 o Mz A1 Lt 17)
- proyecto: nombre del proyecto inmobiliario (ej: ALTOS DEL PRADO, ALTOS DEL VALLE)

Responde SOLO en JSON:
{"es_contrato": bool, "cliente": "str", "lote": "str", "proyecto": "str"}
"""

def clasificar_con_ia(texto=None, imagen_b64=None):
    """
    Envía el texto o imagen a OpenAI para clasificar el documento.
    Retorna el JSON con la clasificación.
    """
    if texto:
        # Caso 1: PDF con texto → enviar como texto plano
        print("  [🤖] Enviando texto a OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"{PROMPT_CLASIFICACION}\n\nTEXTO DEL DOCUMENTO:\n{texto[:3000]}"}
            ],
            response_format={"type": "json_object"},
            max_tokens=200
        )
    else:
        # Caso 2: PDF escaneado → enviar imagen
        print("  [🤖] Enviando imagen a OpenAI Vision...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT_CLASIFICACION},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{imagen_b64}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=200
        )

    resultado = json.loads(response.choices[0].message.content)
    return resultado


# ─────────────────────────────────────────────
# FASE 1 COMPLETA: identificar_documento()
# ─────────────────────────────────────────────
def identificar_documento(pdf_path):
    """
    FASE 1 COMPLETA:
    Lee el PDF → Detecta tipo → Pregunta a la IA → Retorna clasificación.
    
    Retorna: (dict con {es_contrato, cliente, lote, proyecto}, error_msg)
    """
    try:
        print(f"\n[FASE 1] Identificando: {os.path.basename(pdf_path)}")
        
        # Paso 1: Leer el PDF
        texto, imagen_b64 = leer_pdf(pdf_path)
        
        # Paso 2: Preguntar a la IA
        resultado = clasificar_con_ia(texto=texto, imagen_b64=imagen_b64)
        
        # Resultado
        es_contrato = resultado.get("es_contrato", False)
        if es_contrato:
            print(f"  [✅] CONTRATO detectado")
            print(f"       Cliente : {resultado.get('cliente', 'N/A')}")
            print(f"       Lote    : {resultado.get('lote', 'N/A')}")
            print(f"       Proyecto: {resultado.get('proyecto', 'N/A')}")
        else:
            print(f"  [ℹ️] BOLETA / No es contrato")

        return resultado, None

    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────
# PRUEBA DIRECTA (solo para testing)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    BASE = r"c:\Users\AYBAR CORP SAC\Desktop\digitalizados\ALTOS DEL PRADO\A1-17"
    
    print("=" * 55)
    print("PRUEBA FASE 1 — Clasificar documentos")
    print("=" * 55)

    archivos = [
        f"{BASE}\\ALTOS DEL PRADO BOLETA  A1-17.pdf",
        f"{BASE}\\ALTOS DEL PRADO CONTRATO A1-17.pdf",
    ]

    for pdf in archivos:
        resultado, error = identificar_documento(pdf)
        if error:
            print(f"  [ERROR] {error[:80]}")
        print()
