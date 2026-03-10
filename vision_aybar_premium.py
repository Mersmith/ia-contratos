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
        # Convertimos todo el PDF a resolución media (130 DPI) para buscar palabras clave (Radar)
        paginas_baja = convert_from_path(ruta_pdf, dpi=130, poppler_path=POPPLER_PATH)
        total_pags = len(paginas_baja)
        
        indices_clave = [0, 1] # Siempre incluimos las primeras dos páginas por defecto
        # Radar detecta páginas de datos y cláusulas de entrega/formalización
        keywords = [
            "ANEXO", "MEMORIA", "INFORMACIÓN DEL CLIENTE", 
            "CALENDARIO", "PRECIO", "FORMA DE PAGO",
            "FORMALIZACIÓN", "PLAZO DE ENTREGA",
            "DE LA ENTREGA", "ENTREGA FÍSICA", "CONTRATO DEFINITIVO",
            "SÉPTIMO", "SEPTIMO", "POSESION", "POSESIÓN", "PLAZO",
            "VIGENCIA", "FIRMA DEL CONTRATO", "VIII", "VII", "VIVA NORTE",
            "INFORMACIÓN GENERAL", "FECHA DE FIRMA", "DEFINITIVO",
            "DENOMINACIÓN", "DENOMINACION", "ALICUOTA", "ALÍCUOTA",
            "EL COMPRADOR", "EL VENDEDOR", "PREPARATORIO",
            "COMPROMISO", "ADQUIRIENTE", "TRANSFIRIENTE", "CUARTA",
            "PLAZO DE EJECUCIÓN", "PLAZO DE EJECUCION", "EJECUCIÓN DEL SERVICIO",
            "SEXTA", "SÉPTIMA"
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
        
        # Ahora convertimos SOLO las páginas detectadas a ALTA resolución (200-300 DPI) para la IA
        print(f"  [📸] Convirtiendo {len(indices_clave)} páginas detectadas a alta resolución...")
        payload_messages = [
            {
                "role": "system",
                "content": """Eres el analista experto de AYBAR CORP S.A.C. 
                Recibirás imágenes de páginas específicas de un contrato inmobiliario (Anexos, Cláusulas y Firmas).
                Tu misión es extraer datos con 100% de precisión.
                
                REGLAS DE EXTRACCIÓN (BASADAS EN MODELOS VISUALES DE AYBAR CORP):
                 1. PROYECTO: 
                    - Prioridad 1: Nombre del Condominio que aparece en la cláusula "OBJETO". Ej: "...del Condominio CAMTABRIA LAGOONS" -> Proyecto: "CAMTABRIA LAGOONS".
                    - Prioridad 2: Nombre comercial en logo o encabezado (ej: ALTOS DEL PRADO, LUGO, LOTES DEL PERU, VIÑA DEL MAR, ALTOS DEL VALLE, FINCA LAS LOMAS).
                    - ⚠️ IMPORTANTE: No confundir el nombre de la empresa "AYBAR CORP" con el nombre del proyecto.
                 2. MANZANA/LOTE: 
                    - Prioridad 1: Título o encabezado que diga "SUB-LOTE [MZ]-[LOTE]" o similar. Ej: "SUB-LOTE A-04" -> Manzana: "A", Lote: "04".
                    - Prioridad 2: Cuadro bajo el título "DENOMINACIÓN" u "OBJETO". Si dice 'DEL LOTE "26" MANZANA "A1"', Manzana es "A1" y Lote es "26". Debe ser literal.
                    - 🚫 REGLA CRÍTICA DE EXCLUSIÓN: JAMÁS uses datos que aparezcan en la sección "DATOS DEL CLIENTE" o "DIRECCIÓN COMÚN". Esos datos (ej: "MZ-K LT 23") corresponden a la casa actual del cliente, NO al lote que está comprando.
                 3. ÁREA Y ALÍCUOTA: Sección 'MEMORIA DESCRIPTIVA' o Punto V del Anexo 1.
                 4. FECHA SUSCRIPCION (fecha_suscripcion):
                    - ⚠️ PRIORIDAD MÁXIMA: La fecha que acompaña a las firmas conjuntas de "EL COMPRADOR/CLIENTE" y "EL VENDEDOR/INMOBILIARIA" en el **Contrato Preparatorio original** (suele estar al final de las cláusulas, cerca de 'DÉCIMA CUARTA' o similares).
                    - 🚫 REGLA DE EXCLUSIÓN CRÍTICA: Ignora TOTALMENTE las fechas de una "ADENDA AL CONTRATO".
                    - 🚫 EXCLUSIÓN 2: Ignora títulos como "HOJA DE NEGOCIACIÓN", "ACUERDO DE COMPRA", "SEPARACIÓN" o "MEMORIA DESCRIPTIVA". Estas son fechas preliminares, NO la fecha legal del contrato.
                 5. FECHA ENTREGA (fecha_entrega) — CAMPO CRÍTICO:
                    - PATRÓN CLAUSULAR 1: Busca frases como "la entrega ... se realizará en [MES] del [AÑO]" o "entrega ... se realizará en [MES] de [AÑO]". Común en cláusula SEXTA o SÉPTIMA.
                    - PATRÓN CLAUSULAR 2: Mención de "plazo máximo de [X] meses" bajo títulos como "PLAZO DE EJECUCIÓN". Muy común en modelos de "FORMALIZACION DE VIVIENDA".
                    - PATRÓN SAN ANDRÉS/GENERAL: Cuadro VIII del Anexo 1 o fecha de formalización final.
                    - PRIORIDAD: Prefiere un mes/año específico (ej: "diciembre de 2021") o un plazo (ej: "24 meses"). Evita usar la fecha de suscripción del contrato como fecha de entrega salvo que el contrato lo indique explícitamente.
                    Esta es la fecha pactada originalmente para la entrega. Existem múltiples patrones:
                 
                     PATRÓN PREFERENTE — Cuadro Anexo 1 - Sección VIII (Altos del Prado, Altos del Valle, Finca Las Lomas):
                     Busca la tabla: "VIII. DE LA FIRMA DEL CONTRATO DEFINITIVO".
                     A su derecha verás una fecha como: "treinta y uno de diciembre del 2027 (31/12/2027)".
                     → ✅ ¡ESTE VALOR ES LA PRIORIDAD ABSOLUTA PARA fecha_entrega! Debe anular cualquier fecha de la sección VII.
                     
                     PATRÓN SECUNDARIO — Cuadro Anexo 1 - Sección VII:
                     Solo si la sección VIII está vacía o no existe, busca en "VII. DE LA ENTREGA" -> "Plazo de Entrega".
                     → Ej: "año 2028 mes diciembre".
                    
                    PATRÓN — Cláusula SÉPTIMO (Pontevedra / Posesión):
                    Texto: "entregará la posesión de LA ALICUOTA ... el [DIA] [MES] del [AÑO]"
                    → Ej: "30 diciembre del 2021"
                    
                 ⚠️ IMPORTANTE: En el modelo de FINCA LAS LOMAS, ignora las menciones de "Anexo 1" en la página 2 y busca directamente el CUADRO VIII al final.
                 ⚠️ "Fecha de firma de contrato definitivo" en el Anexo 1 NO es la suscripción de hoy, es la FECHA DE ENTREGA PACTADA.
                 ⚠️ Si no encuentras ningún patrón real, devuelve null.
                
                  6. PROPIETARIOS: Extrae el nombre completo tal cual aparece en el contrato, capturando AMBOS APELLIDOS y todos los nombres. Es CRÍTICO capturar la identidad legal íntegra y no omitir ninguna parte. No reordenes los apellidos a menos que el documento use explícitamente el formato 'Apellidos, Nombres'.
                
                FORMATO DE RESPUESTA JSON:
                {
                  "tipo": "contrato",
                  "contrato": {
                    "proyecto": "str", "manzana": "str", "lote": "str", "area": "str", "alicuota": "str",
                    "fecha_suscripcion": "str", "fecha_entrega": "str",
                    "propietarios": [{"nombre": "TAL CUAL APARECE EN EL DOCUMENTO", "dni": "str"}]
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
        
        # Depuración: Ver respuesta de la IA
        print("-" * 30)
        print(f"  [DEBUG IA JSON] {json.dumps(resultado_json, indent=2)}")
        print("-" * 30)
        
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
