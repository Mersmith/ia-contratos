"""
=============================================================
 FASE 2 — Extracción de Datos del Contrato
=============================================================
 Objetivo: Leer todo el contrato y extraer:
   - cliente  (nombre completo del comprador)
   - lote     (número de manzana/lote)
   - proyecto (nombre del proyecto inmobiliario)
   - dni      (documento de identidad del comprador)
 
 Flujo:
  1. Python convierte TODAS las páginas del PDF a imágenes
  2. Si el PDF tiene > 20 páginas, envía solo las últimas 15
     (el ANEXO 1 con los datos del cliente siempre está al final)
  3. OpenAI Vision recibe todas las imágenes y busca el ANEXO 1
  4. Retorna un JSON con los datos encontrados
=============================================================
"""

import os
import sys
import json
import base64
import fitz  # PyMuPDF
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

# Límite máximo de imágenes a enviar por llamada a OpenAI
MAX_IMAGENES = 20

# Carpeta de previews (configurable desde .env)
PREVIEW_DIR = os.getenv("PREVIEW_DIR", r"C:\Users\AYBAR CORP SAC\Desktop\automatizacion\preview")


# ─────────────────────────────────────────────
# PASO 1: Convertir páginas del PDF a imágenes
# ─────────────────────────────────────────────
def pdf_a_imagenes(pdf_path, paginas=None):
    """
    Convierte páginas del PDF a imágenes PNG guardadas en disco (preview/)
    y retorna su contenido en base64 para enviarlo a OpenAI.

    - paginas: lista de índices a convertir (ej: [0,1,2...])
               Si es None, convierte TODAS las páginas.
    Retorna: lista de strings base64
    """
    doc = fitz.open(pdf_path)
    total_paginas = len(doc)

    if paginas is None:
        paginas = list(range(total_paginas))

    # Crear subcarpeta en preview/ con el nombre del PDF (sin extensión)
    nombre_pdf = os.path.splitext(os.path.basename(pdf_path))[0]
    carpeta_preview = os.path.join(PREVIEW_DIR, nombre_pdf)
    os.makedirs(carpeta_preview, exist_ok=True)
    print(f"  [📁] Guardando previews en: {carpeta_preview}")

    imagenes = []
    for i in paginas:
        if i < total_paginas:
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Buena resolución

            # Guardar imagen en disco
            ruta_img = os.path.join(carpeta_preview, f"pagina_{i+1:02d}.png")
            pix.save(ruta_img)

            # Leer desde disco y encodear a base64 (libera el pixmap de RAM)
            with open(ruta_img, "rb") as f:
                imagenes.append(base64.b64encode(f.read()).decode('utf-8'))

            print(f"  [🖼️] Guardada: pagina_{i+1:02d}.png")

    doc.close()
    return imagenes, total_paginas


def seleccionar_paginas(total_paginas):
    """
    Decide qué páginas enviar según el total de páginas del contrato.
    El ANEXO 1 siempre está en las páginas finales.
    
    Retorna: lista de índices de página a procesar
    """
    if total_paginas <= MAX_IMAGENES:
        # Enviar todas las páginas
        return list(range(total_paginas))
    elif total_paginas <= 40:
        # Enviar solo las últimas 15
        return list(range(total_paginas - 15, total_paginas))
    else:
        # Enviar solo las últimas 20
        return list(range(total_paginas - MAX_IMAGENES, total_paginas))


# ─────────────────────────────────────────────
# PASO 2: Extraer datos con OpenAI Vision
# ─────────────────────────────────────────────
PROMPT_EXTRACCION = """
Eres un asistente especializado en documentos inmobiliarios peruanos de AYBAR CORP S.A.C.

Estás viendo las páginas de un CONTRATO PREPARATORIO DE COMPRAVENTA.
Busca específicamente la sección llamada "ANEXO 1 - INFORMACIÓN GENERAL" o "DATOS DEL CLIENTE".

Extrae los siguientes datos:
1. cliente: Nombre completo del COMPRADOR (puede estar como "Nombres y Apellidos", "Cliente", "Comprador")
   - Formato esperado: APELLIDO APELLIDO, NOMBRE NOMBRE (en mayúsculas)
2. lote: Identificación del lote o manzana comprado
   - Formato esperado: A1-17 o similar (Manzana + número de lote)
3. proyecto: Nombre del proyecto inmobiliario
   - Ejemplos: ALTOS DEL PRADO, ALTOS DEL VALLE
4. dni: Número de DNI o documento del comprador (solo números)

Si un campo no se encuentra claramente, usa null.

Responde SOLO en JSON:
{
  "cliente": "APELLIDO APELLIDO, NOMBRE NOMBRE",
  "lote": "A1-17",
  "proyecto": "ALTOS DEL PRADO",
  "dni": "12345678"
}
"""

def extraer_datos_con_ia(imagenes_b64):
    """
    Envía las imágenes del contrato a OpenAI Vision.
    Busca el ANEXO 1 y extrae: cliente, lote, proyecto, dni.
    """
    print(f"  [🤖] Enviando {len(imagenes_b64)} páginas a OpenAI Vision...")

    # Construir el contenido del mensaje con todas las imágenes
    contenido = [{"type": "text", "text": PROMPT_EXTRACCION}]
    
    for i, img_b64 in enumerate(imagenes_b64):
        contenido.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": contenido}
        ],
        response_format={"type": "json_object"},
        max_tokens=300
    )

    resultado = json.loads(response.choices[0].message.content)
    return resultado


# ─────────────────────────────────────────────
# FASE 2 COMPLETA: extraer_datos_contrato()
# ─────────────────────────────────────────────
def extraer_datos_contrato(pdf_path):
    """
    FASE 2 COMPLETA:
    Convierte el PDF → selecciona páginas → envía a OpenAI → retorna datos extraídos.
    
    Retorna: (dict con {cliente, lote, proyecto, dni}, error_msg)
    """
    try:
        print(f"\n[FASE 2] Extrayendo datos de: {os.path.basename(pdf_path)}")

        # Paso 1: Determinar qué páginas enviar
        doc_info = fitz.open(pdf_path)
        total = len(doc_info)
        doc_info.close()

        paginas_a_enviar = seleccionar_paginas(total)
        print(f"  [📄] Total páginas: {total} | Enviando páginas: {[p+1 for p in paginas_a_enviar]}")

        # Paso 2: Convertir páginas seleccionadas a imágenes
        imagenes, _ = pdf_a_imagenes(pdf_path, paginas=paginas_a_enviar)
        print(f"  [🖼️] {len(imagenes)} imágenes generadas")

        # Paso 3: Extraer datos con OpenAI
        datos = extraer_datos_con_ia(imagenes)

        # Mostrar resultado
        print(f"  [✅] Datos extraídos:")
        print(f"       Cliente : {datos.get('cliente', 'No encontrado')}")
        print(f"       Lote    : {datos.get('lote', 'No encontrado')}")
        print(f"       Proyecto: {datos.get('proyecto', 'No encontrado')}")
        print(f"       DNI     : {datos.get('dni', 'No encontrado')}")

        return datos, None

    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────
# PRUEBA DIRECTA (solo para testing)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    BASE = r"c:\Users\AYBAR CORP SAC\Desktop\digitalizados\ALTOS DEL PRADO\A1-17"
    CONTRATO = f"{BASE}\\ALTOS DEL PRADO CONTRATO A1-17.pdf"
    
    print("=" * 55)
    print("PRUEBA FASE 2 — Extraer datos del contrato")
    print("=" * 55)

    datos, error = extraer_datos_contrato(CONTRATO)

    if error:
        print(f"  [ERROR] {error[:100]}")
    elif datos:
        print(f"\n  JSON completo recibido:")
        print(json.dumps(datos, indent=2, ensure_ascii=False))
