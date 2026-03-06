"""
=============================================================
 WORKER FINAL — Sistema Digitalizados
 AYBAR CORP S.A.C.
=============================================================
 Une las 3 fases en un proceso automático completo:

 FASE 1: ¿Es CONTRATO o BOLETA? (primera_fase.py)
         → Analiza solo la página 1 (rápido y barato)

 FASE 2: Extraer datos del contrato (segunda_fase.py)
         → Lee todo el documento y busca el ANEXO 1
         → Extrae: cliente, lote, proyecto, dni

 FASE 3: Guardar en MySQL (Laragon)
         → INSERT o UPDATE en contratos_digitalizados

 Características:
  - Omite archivos ya procesados (no gasta IA de nuevo)
  - Reintenta automáticamente si OpenAI está saturado (429)
  - Registra errores en la DB para no perder trazabilidad
  - Pausa entre archivos para respetar límites de la API
=============================================================
"""

import os
import sys
import json
import time
import mysql.connector
from dotenv import load_dotenv

# Importar las fases como módulos
from primera_fase import identificar_documento
from segunda_fase import extraer_datos_contrato

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# Carpeta raíz a escanear (configurada en .env → CARPETA_PDF)
BASE_DIR = os.getenv("CARPETA_PDF", r"C:\Users\AYBAR CORP SAC\Desktop\automatizacion\analizar")

# Carpetas y archivos a ignorar
IGNORAR = ["worker", ".git", "vendor", "node_modules", "__pycache__", ".env"]

# Pausa entre archivos (segundos) — para respetar límite gratuito de OpenAI
PAUSA_ENTRE_ARCHIVOS = 5  # segundos


# ═══════════════════════════════════════════════════
# FASE 3 — Base de Datos
# ═══════════════════════════════════════════════════

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USERNAME", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_DATABASE", "contratos"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def validar_db():
    """Valida que la tabla exista antes de arrancar."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES LIKE 'contratos_digitalizados'")
        existe = cursor.fetchone()
        conn.close()
        if not existe:
            print("[ERROR] La tabla 'contratos_digitalizados' no existe. Creala en phpMyAdmin.")
            return False
        return True
    except Exception as e:
        print(f"[ERROR DB] {e}")
        return False

def ya_fue_procesado(ruta):
    """Retorna True si el archivo ya tiene estado 'procesado' en la DB."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT estado FROM contratos_digitalizados WHERE ruta_archivo = %s", (ruta,))
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == 'procesado'
    except:
        return False

def guardar_en_db(datos, ruta, estado='procesado'):
    """
    FASE 3: Guarda o actualiza el registro en MySQL.
    - Si la ruta ya existe → UPDATE
    - Si es nuevo → INSERT
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM contratos_digitalizados WHERE ruta_archivo = %s", (ruta,))
        existing = cursor.fetchone()

        json_str = json.dumps(datos, ensure_ascii=False)

        if existing:
            sql = """UPDATE contratos_digitalizados 
                     SET cliente=%s, lote=%s, proyecto=%s, estado=%s, json_completo=%s 
                     WHERE id=%s"""
            values = (
                datos.get('cliente', 'N/A'),
                datos.get('lote', 'N/A'),
                datos.get('proyecto', 'N/A'),
                estado,
                json_str,
                existing[0]
            )
        else:
            sql = """INSERT INTO contratos_digitalizados 
                     (cliente, lote, proyecto, ruta_archivo, estado, json_completo) 
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            values = (
                datos.get('cliente', 'N/A'),
                datos.get('lote', 'N/A'),
                datos.get('proyecto', 'N/A'),
                ruta,
                estado,
                json_str
            )

        cursor.execute(sql, values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  [ERROR DB] {e}")
        return False


# ═══════════════════════════════════════════════════
# Función auxiliar: Reintentos para errores 429
# ═══════════════════════════════════════════════════

def ejecutar_con_reintentos(funcion, *args, max_reintentos=3):
    """
    Ejecuta una función y reintenta si hay error de cuota (429).
    Espera progresivamente: 30s → 60s → 90s
    """
    for intento in range(1, max_reintentos + 1):
        resultado, error = funcion(*args)
        if error and ("429" in error or "quota" in error.lower()):
            espera = 30 * intento
            print(f"  [⏳] Cuota agotada. Reintento {intento}/{max_reintentos} en {espera}s...")
            time.sleep(espera)
        else:
            return resultado, error
    return None, "Maximo de reintentos alcanzado."


# ═══════════════════════════════════════════════════
# PROCESO PRINCIPAL
# ═══════════════════════════════════════════════════

def procesar_directorio(base_path):
    """
    Escanea toda la carpeta y procesa cada PDF encontrado.
    """
    total = 0
    contratos = 0
    boletas = 0
    errores = 0
    omitidos = 0

    for root, dirs, files in os.walk(base_path):
        # Ignorar carpetas del sistema
        if any(x in root.lower() for x in IGNORAR):
            continue

        for file in files:
            if not file.lower().endswith(".pdf"):
                continue

            ruta_completa = os.path.normpath(os.path.join(root, file))
            total += 1

            print(f"\n{'='*55}")
            print(f"[{total}] {file}")
            print(f"{'='*55}")

            # ─── Verificar si ya fue procesado ───
            if ya_fue_procesado(ruta_completa):
                print(f"  [⏭️] Omitido: ya está procesado en la DB.")
                omitidos += 1
                continue

            # ─── FASE 1: ¿Boleta o Contrato? ───
            clasificacion, error1 = ejecutar_con_reintentos(identificar_documento, ruta_completa)

            if error1:
                print(f"  [ERROR Fase 1] {error1[:80]}")
                guardar_en_db({"ruta_archivo": ruta_completa}, ruta_completa, estado='error')
                errores += 1
                time.sleep(PAUSA_ENTRE_ARCHIVOS)
                continue

            if not clasificacion.get("es_contrato"):
                # Es boleta → registrar y continuar
                print(f"  [ℹ️] BOLETA detectada. Se registra y omite a futuro.")
                guardar_en_db({
                    "es_contrato": False,
                    "tipo": "boleta"
                }, ruta_completa, estado='procesado')
                boletas += 1
                time.sleep(PAUSA_ENTRE_ARCHIVOS)
                continue

            # ─── FASE 2: Extraer datos del contrato ───
            print(f"  [✅] CONTRATO confirmado. Iniciando Fase 2...")
            datos, error2 = ejecutar_con_reintentos(extraer_datos_contrato, ruta_completa)

            if error2:
                print(f"  [ERROR Fase 2] {error2[:80]}")
                guardar_en_db({
                    "es_contrato": True,
                    "error": error2
                }, ruta_completa, estado='error')
                errores += 1
                time.sleep(PAUSA_ENTRE_ARCHIVOS)
                continue

            # ─── FASE 3: Guardar en MySQL ───
            datos_finales = {
                "es_contrato": True,
                "cliente": datos.get("cliente"),
                "lote": datos.get("lote"),
                "proyecto": datos.get("proyecto"),
                "dni": datos.get("dni"),
            }

            if guardar_en_db(datos_finales, ruta_completa, estado='procesado'):
                print(f"  [💾] Guardado en MySQL:")
                print(f"       Cliente : {datos.get('cliente', 'N/A')}")
                print(f"       Lote    : {datos.get('lote', 'N/A')}")
                print(f"       Proyecto: {datos.get('proyecto', 'N/A')}")
                contratos += 1
            else:
                errores += 1

            time.sleep(PAUSA_ENTRE_ARCHIVOS)

    # ─── Resumen final ───
    print(f"\n{'='*55}")
    print(f" RESUMEN FINAL")
    print(f"{'='*55}")
    print(f"  PDFs encontrados  : {total}")
    print(f"  Contratos extraidos: {contratos}")
    print(f"  Boletas omitidas  : {boletas}")
    print(f"  Errores           : {errores}")
    print(f"  Omitidos (ya OK)  : {omitidos}")
    print(f"{'='*55}")


# ═══════════════════════════════════════════════════
# INICIO
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print(" WORKER FINAL — AYBAR CORP S.A.C.")
    print(" Sistema de Digitalización de Contratos")
    print("=" * 55)

    if validar_db():
        procesar_directorio(BASE_DIR)

    print("\n[PROCESO COMPLETADO]")
