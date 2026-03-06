"""
=============================================================
 vision_aybar_premium.py — Extractor de Alta Fidelidad
=============================================================
 Este script utiliza OpenAI Vision para procesar contratos 
 escaneados con máxima precisión, soportando múltiples modelos
 y contratos largos (21+ páginas).
 
 Basado en:
 - database.sql (Estructura de tablas)
 - TABLA_ENTRENAR.md (Guía visual de campos)
 - modelos/ (Diferentes estructuras de contratos)
=============================================================
"""

import os
import sys
import json
import time
import base64
import mysql.connector
from io import BytesIO
from PIL import Image
from pdf2image import convert_from_path
import pytesseract  # <--- Agregado para el filtro rápido
from openai import OpenAI
from dotenv import load_dotenv

# Configuración de entorno
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Rutas
BASE_DIR = os.getenv("CARPETA_PDF", r"C:\Users\AYBAR CORP SAC\Desktop\automatizacion\analizar")
POPPLER_PATH = r"C:\poppler\Library\bin"

# ═══════════════════════════════════════════════════
# SOPORTE DE BASE DE DATOS
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
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contratos_digitalizados WHERE ruta_archivo = %s", (ruta,))
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except:
        return False

def guardar_en_db(datos, texto_crudo, ruta_archivo, tipo_documento):
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 1. Insertar en contratos_digitalizados
        sql_contrato = """
            INSERT INTO contratos_digitalizados 
            (proyecto, manzana, lote, area, alicuota, fecha_suscripcion_contrato, fecha_pactada_entrega, 
             ruta_archivo, estado, tipo_documento, json_completo, texto_ocr, tokens_entrada, tokens_salida, costo_estimado_usd)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        info = datos.get('contrato', {})
        values = (
            str(info.get('proyecto', 'N/A'))[:255],
            str(info.get('manzana', 'N/A'))[:100],
            str(info.get('lote', 'N/A'))[:100],
            str(info.get('area', 'N/A'))[:100],
            str(info.get('alicuota', 'N/A'))[:100],
            str(info.get('fecha_suscripcion', 'N/A'))[:100],
            str(info.get('fecha_entrega', 'N/A'))[:100],
            ruta_archivo, 'procesado', tipo_documento,
            json.dumps(datos, ensure_ascii=False),
            texto_crudo[:1000],
            datos.get('usage', {}).get('prompt_tokens', 0),
            datos.get('usage', {}).get('completion_tokens', 0),
            datos.get('usage', {}).get('total_cost_usd', 0)
        )
        
        cursor.execute(sql_contrato, values)
        contrato_id = cursor.lastrowid

        # 2. Insertar Propietarios
        propietarios = info.get('propietarios', [])
        if propietarios:
            sql_prop = "INSERT INTO contrato_propietarios (contrato_id, orden, nombre_completo, dni) VALUES (%s, %s, %s, %s)"
            for idx, p in enumerate(propietarios, start=1):
                cursor.execute(sql_prop, (contrato_id, idx, p.get('nombre', '').upper(), p.get('dni', '')))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  [❌ ERROR DB] {e}")
        return False

# ═══════════════════════════════════════════════════
# PROCESAMIENTO DE IMÁGENES Y VISIÓN
# ═══════════════════════════════════════════════════

def encode_image(pil_img):
    buffered = BytesIO()
    pil_img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extraer_con_vision_premium(ruta_pdf):
    # --- FILTRO DE SEGURIDAD (FASE 0) ---
    print(f"  [�] Verificando tipo de documento (Filtro rápido)...")
    try:
        # Convertimos solo la página 1 para chequear rápido
        pág1 = convert_from_path(ruta_pdf, first_page=1, last_page=1, dpi=100, poppler_path=POPPLER_PATH)[0]
        texto_pág1 = pytesseract.image_to_string(pág1, lang='spa')
        
        if "BOLETA DE VENTA" in texto_pág1.upper() or "R.U.C. 20603865813" in texto_pág1:
            print("  [ℹ️] Filtrado: Es una BOLETA. Saltando proceso premium.")
            return {"tipo": "boleta", "contrato": {}}
    except Exception as e:
        print(f"  [⚠️] No se pudo pre-clasificar, procediendo con Vision por seguridad.")

    # --- PROCESO PREMIUM (Solo si pasó el filtro) ---
    print(f"  [📄] Escaneando páginas para detectar información clave (Radar)...")
    try:
        # Convertimos todo el PDF a baja resolución (75 DPI) solo para buscar palabras clave
        paginas_baja = convert_from_path(ruta_pdf, dpi=75, poppler_path=POPPLER_PATH)
        total_pags = len(paginas_baja)
        
        indices_clave = [0, 1] # Siempre incluimos las primeras dos páginas por defecto
        # Radar detecta páginas de datos y cláusulas de entrega/formalización
        keywords = [
            "ANEXO 1", "MEMORIA DESCRIPTIVA", "INFORMACIÓN DEL CLIENTE", 
            "CALENDARIO DE PAGOS", "PRECIO Y FORMA DE PAGO",
            "DE LA FORMALIZACIÓN DEL CONTRATO", "PLAZO DE ENTREGA",
            "DE LA ENTREGA", "ENTREGA FÍSICA", "CONTRATO DEFINITIVO"
        ]
        
        for i, pag in enumerate(paginas_baja):
            if i in indices_clave: continue # Saltar si ya está
            
            # OCR rápido de la página
            texto = pytesseract.image_to_string(pag, lang='spa').upper()
            
            if any(key in texto for key in keywords):
                print(f"  [🎯] ¡Información detectada en página {i+1}!")
                indices_clave.append(i)
        
        # Siempre incluimos la última página por si acaso (firmas/fechas)
        if (total_pags - 1) not in indices_clave:
            indices_clave.append(total_pags - 1)

        indices_clave = sorted(list(set(indices_clave))) # Ordenar y quitar duplicados
        
        # Ahora convertimos SOLO las páginas detectadas a ALTA resolución (300 DPI) para la IA
        print(f"  [📸] Convirtiendo {len(indices_clave)} páginas detectadas a alta resolución...")
        payload_messages = [
            {
                "role": "system",
                "content": """Eres el analista experto de AYBAR CORP S.A.C. 
                Recibirás imágenes de páginas específicas de un contrato inmobiliario. 
                Tu misión es extraer datos con 100% de precisión.
                
                REGLAS DE EXTRACCIÓN (BASADAS EN MODELOS VISUALES DE AYBAR CORP):
                1. PROYECTO: Nombre comercial visible en logo o encabezado (ej: ALTOS DEL PRADO, LUGO, LOTES DEL PERU, VIÑA DEL MAR, ALTOS DEL VALLE, FINCA LAS LOMAS).
                2. MANZANA/LOTE: Punto V del Anexo 1 o Memoria Descriptiva.
                3. ÁREA Y ALÍCUOTA: Sección 'MEMORIA DESCRIPTIVA'.
                4. FECHA SUSCRIPCION: Donde están las firmas al final del documento (ej: "Lima, 10 de octubre de 2023") o en el encabezado.
                5. FECHA PACTADA ENTREGA — CAMPO CRÍTICO. Existen 5 patrones distintos según el modelo de contrato:
                
                   PATRÓN A — Cláusula QUINTO 5.1 (Viña del Mar / Finca Las Lomas):
                   Texto: "LAS PARTES acuerdan que la entrega física de la alícuota... se realizara en [MES] de [AÑO]."
                   → Extrae el mes y año. Ej: "diciembre de 2024"
                   
                   PATRÓN B — Cláusula QUINTO 5.1 (Altos del Prado / Grocio Prado):
                   Texto: "LAS PARTES acuerdan que la entrega física de LA ALICUOTA se realizará a partir de [MES] de [AÑO]"
                   → Extrae el mes y año. Ej: "diciembre de 2027"
                   
                   PATRÓN C — Cláusula SEXTA (Lugo / Lotes del Perú):
                   Texto: "LAS PARTES acuerdan que la entrega del ALICUOTA objeto de este contrato se realizara en [MES] del año [AÑO]"
                   → Extrae el mes y año. Ej: "diciembre del año 2021"
                   
                   PATRÓN D — Tabla Anexo 1, sección "VII. DE LA ENTREGA" (Altos del Valle):
                   Campo: "Plazo de Entrega" seguido de un valor tipo: "año 2028 mes diciembre"
                   → Extrae ese valor. Ej: "año 2028 mes diciembre"
                   
                   PATRÓN E — Tabla Anexo 1, sección "VIII. DE LA FIRMA DEL CONTRATO DEFINITIVO" (Altos del Prado):
                   Campo: "Fecha de firma de contrato definitivo" seguido de una fecha como "treinta y uno de diciembre del 2027 (31/12/2027)"
                   → Extrae esa fecha. Ej: "31/12/2027"
                   
                   ⚠️ Si una cláusula dice "se realizará en la fecha indicada en el ANEXO 1", busca el valor real en los cuadros del Anexo 1.
                   ⚠️ Si no encuentras ningún patrón, devuelve null. NUNCA inventes una fecha.
                   
                6. PROPIETARIOS: Nombre y DNI del punto II del Anexo 1 (Información del Cliente). Lista TODOS los copropietarios que aparezcan.
                
                FORMATO DE RESPUESTA JSON:
                {
                  "tipo": "contrato",
                  "contrato": {
                    "proyecto": "str", "manzana": "str", "lote": "str", "area": "str", "alicuota": "str",
                    "fecha_suscripcion": "str", "fecha_entrega": "str",
                    "propietarios": [{"nombre": "APELLIDOS, NOMBRES", "dni": "str"}]
                  }
                }"""
            },
            {
                "role": "user",
                "content": []
            }
        ]

        # Solo convertimos a alta calidad las que el radar detectó
        for i in indices_clave:
            img_alta = convert_from_path(ruta_pdf, first_page=i+1, last_page=i+1, dpi=200, poppler_path=POPPLER_PATH)[0]
            base64_img = encode_image(img_alta)
            payload_messages[1]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}", "detail": "high"}
            })

        payload_messages[1]["content"].append({
            "type": "text", "text": "Analiza estas páginas y extrae el JSON solicitado."
        })

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=payload_messages,
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        # --- CALCULO DE COSTOS (GPT-4o) ---
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        
        # Precios aprox: In $2.50/1M, Out $10.00/1M
        cost_in = (prompt_tokens / 1_000_000) * 2.50
        cost_out = (completion_tokens / 1_000_000) * 10.00
        total_cost = cost_in + cost_out

        resultado_json = json.loads(response.choices[0].message.content)
        
        # Inyectamos el costo en el resultado para guardarlo
        resultado_json['usage'] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_cost_usd": round(total_cost, 5)
        }
        
        return resultado_json

    except Exception as e:
        print(f"  [❌ ERROR VISION] {e}")
        return None

# ═══════════════════════════════════════════════════
# ORQUESTADOR
# ═══════════════════════════════════════════════════

def procesar_todo():
    print("="*60)
    print(" 🚀 AYBAR PREMIUM VISION — SISTEMA MULTI-MODELO")
    print("="*60)

    # Escanear archivos
    archivos = []
    for root, _, files in os.walk(BASE_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                archivos.append(os.path.join(root, f))

    print(f"📂 Total de archivos a procesar: {len(archivos)}")

    for i, ruta in enumerate(archivos, 1):
        nombre = os.path.basename(ruta)
        
        # --- NUEVO: Omitir si ya existe ---
        if ya_fue_procesado(ruta):
            print(f"\n[{i}/{len(archivos)}] Omitido: {nombre} (Ya en DB)")
            continue

        print(f"\n[{i}/{len(archivos)}] Procesando: {nombre}")

        # Ejecutar Visión
        resultado = extraer_con_vision_premium(ruta)
        
        if resultado:
            tipo = resultado.get('tipo', 'otro')
            if tipo == 'contrato':
                print(f"  [✅] Éxito: {resultado['contrato'].get('proyecto')} - Lote {resultado['contrato'].get('lote')}")
                # Guardar
                guardar_en_db(resultado, "Procesado vía Vision Premium", ruta, 'contrato')
            else:
                print(f"  [ℹ️] Detectado como: {tipo}. Guardando referencia.")
                guardar_en_db(resultado, "Omitido o Boleta", ruta, tipo)
        
        time.sleep(2) # Respetar límites

if __name__ == "__main__":
    procesar_todo()
