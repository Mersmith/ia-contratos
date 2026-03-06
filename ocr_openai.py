"""
=============================================================
 ocr_openai.py — Sistema de Extracción con IA (Nuevo Flujo)
=============================================================
 Este script implementa el flujo profesional completo:
 
 FASE 0: OCR Local (Tesseract) → Extrae texto gratis
 FASE 1: Clasificación IA → ¿Es Contrato o Boleta?
 FASE 2: Extracción IA → Solo si es contrato, extrae datos
 FASE 3: Guardado MySQL → Inserta contrato y propietarios
=============================================================
"""

import os
import sys
import json
import time
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

# Reutilizamos la Fase 0 que ya creamos y probamos
from ocr_utils import extraer_texto_pdf

# Configuración de salida para consola (evitar errores de caracteres)
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# Cliente OpenAI
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Configuración de rutas desde .env
BASE_DIR = os.getenv("CARPETA_PDF", r"C:\Users\AYBAR CORP SAC\Desktop\automatizacion\analizar")

# ═══════════════════════════════════════════════════
# FASE 3 — Base de Datos (Funciones de Soporte)
# ═══════════════════════════════════════════════════

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USERNAME", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_DATABASE", "contratos"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def ya_fue_procesado(ruta):
    """Verifica si el archivo ya existe con estado 'procesado'."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT estado FROM contratos_digitalizados WHERE ruta_archivo = %s", (ruta,))
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == 'procesado'
    except:
        return False

def guardar_resultado_final(datos_ia, texto_ocr, ruta_archivo, tipo_documento):
    """
    Guarda el contrato y sus propietarios en la base de datos.
    Soporta N copropietarios.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        sql_contrato = """
            INSERT INTO contratos_digitalizados 
            (proyecto, manzana, lote, area, alicuota, fecha_suscripcion_contrato, fecha_pactada_entrega, ruta_archivo, estado, tipo_documento, json_completo, texto_ocr)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Datos del contrato
        proyecto = datos_ia.get('proyecto') or 'N/A'
        manzana = datos_ia.get('manzana') or 'N/A'
        lote = datos_ia.get('lote') or 'N/A'
        area = datos_ia.get('area') or 'N/A'
        alicuota = datos_ia.get('alicuota') or 'N/A'
        fecha_sus = datos_ia.get('fecha_suscripcion_contrato') or 'N/A'
        fecha_ent = datos_ia.get('fecha_pactada_entrega') or 'N/A'
        
        values_contrato = (
            str(proyecto)[:255], 
            str(manzana)[:100], 
            str(lote)[:100], 
            str(area)[:100],
            str(alicuota)[:100],
            str(fecha_sus)[:100],
            str(fecha_ent)[:100],
            ruta_archivo, 'procesado', tipo_documento,
            json.dumps(datos_ia, ensure_ascii=False),
            texto_ocr
        )
        
        cursor.execute(sql_contrato, values_contrato)
        contrato_id = cursor.lastrowid

        # 2. Insertar Propietarios (Solo si es contrato y hay una lista de propietarios)
        propietarios = datos_ia.get('propietarios', [])
        if tipo_documento == 'contrato' and propietarios:
            sql_prop = """
                INSERT INTO contrato_propietarios (contrato_id, orden, nombre_completo, dni)
                VALUES (%s, %s, %s, %s)
            """
            for idx, p in enumerate(propietarios, start=1):
                params_prop = (
                    contrato_id,
                    idx,
                    p.get('nombre', 'N/A').upper(),
                    p.get('dni', 'N/A')
                )
                cursor.execute(sql_prop, params_prop)

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  [❌ ERROR DB] {e}")
        return False

# ═══════════════════════════════════════════════════
# FASE 1 & 2 — Lógica de Inteligencia Artificial
# ═══════════════════════════════════════════════════

def procesar_con_ia(texto_ocr):
    """
    Realiza la Fase 1 (Clasificar) y Fase 2 (Extraer) en un solo llamado inteligente.
    """
    prompt = """
    Eres un analista experto en contratos de AYBAR CORP S.A.C.
    Tu objetivo es extraer información de un texto OCR siguiendo estas reglas visuales:

    1. PROYECTO: Busca logotipos o en el punto IV del ANEXO 1. (Ej: ALTOS DEL PRADO).
    2. MANZANA Y LOTE: Busca en el punto V del ANEXO 1 o en la sección MEMORIA DESCRIPTIVA.
       - manzana: Identificado como 'Manzana' o 'Mz' (ej: A1).
       - lote: Identificado como 'Lote' o 'Lt' (ej: 17).
    3. ÁREA: Busca en el punto V del ANEXO 1 o en el punto 3 de MEMORIA DESCRIPTIVA. (ej: 120.54 m2).
    4. ALÍCUOTA: Busca específicamente en el punto 3 de MEMORIA DESCRIPTIVA, al final del contrato. (ej: 0.0803 %).
    5. FECHA SUSCRIPCION: Busca cerca de la parte final donde dice 'Lima, [FECHA]' o en el encabezado.
    6. FECHA PACTADA ENTREGA: Busca en el punto VII del ANEXO 1 (ej: año 2028 mes diciembre).
    7. COMPRADORES: Busca en el punto II del ANEXO 1 'INFORMACIÓN DEL CLIENTE'.
       - Extrae una lista de propietarios con 'nombre' y 'dni'.

    REGLAS DE FORMATO:
    - nombres: APELLIDOS, NOMBRES (Mayúsculas).
    - fechas: DD/MM/AAAA o descripción textual si es difusa.
    - tipo_documento: Solo 'contrato' o 'boleta'.

    RESPONDE EN JSON:
    {
      "tipo_documento": "contrato",
      "datos": {
        "proyecto": "str",
        "manzana": "str",
        "lote": "str",
        "area": "str",
        "alicuota": "str",
        "fecha_suscripcion_contrato": "str",
        "fecha_pactada_entrega": "str",
        "propietarios": [{"nombre": "str", "dni": "str"}]
      }
    }
    """

    try:
        # Enviamos solo los primeros 10k caracteres para ahorrar y porque ahí está todo lo relevante
        fragmento = texto_ocr[:10000]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"TEXTO DEL DOCUMENTO:\n{fragmento}"}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  [❌ ERROR IA] {e}")
        return None

# ═══════════════════════════════════════════════════
# ORQUESTADOR — Proceso Principal
# ═══════════════════════════════════════════════════

def ejecutar_flujo_completo():
    print("=" * 60)
    print(" INICIANDO PROCESAMIENTO: OCR + OPENAI")
    print("=" * 60)

    archivos_pdf = []
    for root, _, files in os.walk(BASE_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                archivos_pdf.append(os.path.join(root, f))

    print(f"📂 Encontrados {len(archivos_pdf)} archivos en {BASE_DIR}")

    total = 0
    exitos = 0
    saltados = 0

    for ruta in archivos_pdf:
        total += 1
        nombre = os.path.basename(ruta)
        
        print(f"\n[{total}/{len(archivos_pdf)}] 👉 {nombre}")

        # --- 1. Verificar si ya existe ---
        if ya_fue_procesado(ruta):
            print("  [⏭️] Ya procesado. Saltando...")
            saltados += 1
            continue

        # --- 2. FASE 0: OCR Local ---
        print("  [🔍] Ejecutando OCR (Fase 0)...")
        texto_ocr, error_ocr = extraer_texto_pdf(ruta, verbose=False)
        
        if error_ocr:
            print(f"  [❌] Error OCR: {error_ocr}")
            continue

        # --- 3. FASE 1 y 2: IA ---
        print("  [🤖] Clasificando y extrayendo con IA...")
        resultado = procesar_con_ia(texto_ocr)

        if not resultado:
            continue

        tipo = resultado.get('tipo_documento', 'otro')
        datos = resultado.get('datos', {})

        if tipo == 'boleta':
            print("  [ℹ️] Es una BOLETA. Se registra tipo pero no datos.")
        elif tipo == 'contrato':
            p_nombres = [p.get('nombre') for p in datos.get('propietarios', [])]
            print(f"  [✅] CONTRATO: {datos.get('proyecto')} | {datos.get('lote')}")
            print(f"       Propietarios: {', '.join(p_nombres)}")
        else:
            print("  [?] Documento no reconocido.")

        # --- 4. FASE 3: Guardar ---
        if guardar_resultado_final(datos, texto_ocr, ruta, tipo):
            print("  [💾] Guardado en Base de Datos correctamente.")
            exitos += 1
        
        # Pausa pequeña para no saturar la CPU/API
        time.sleep(1)

    print("\n" + "=" * 60)
    print(" RESUMEN FINAL")
    print("=" * 60)
    print(f"  Procesados con éxito: {exitos}")
    print(f"  Saltados (ya OK)    : {saltados}")
    print(f"  Total de archivos   : {total}")
    print("=" * 60)

if __name__ == "__main__":
    ejecutar_flujo_completo()
