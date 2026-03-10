import mysql.connector
import os
import json
from dotenv import load_dotenv
import sys

# Windows console encoding fix
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for older python versions
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

def analyze_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            user=os.getenv('DB_USERNAME', 'root'), 
            password=os.getenv('DB_PASSWORD', ''), 
            database=os.getenv('DB_DATABASE', 'contratos'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor(dictionary=True)
        
        print("\n--- ANALIZANDO LOS 42 DOCUMENTOS ---")
        cursor.execute("SELECT id, proyecto, lote, manzana, area, alicuota, fecha_suscripcion_contrato, fecha_pactada_entrega, tipo_documento, ruta_archivo FROM contratos_digitalizados ORDER BY id ASC")
        rows = cursor.fetchall()
        
        proyectos = {}
        total = len(rows)
        correctos = 0
        fallos_totales = 0
        
        for row in rows:
            nombre_archivo = os.path.basename(row['ruta_archivo'])
            p_name = str(row['proyecto']) if row['proyecto'] else "SIN PROYECTO"
            if p_name not in proyectos:
                proyectos[p_name] = {"total": 0, "fallos": 0}
            
            proyectos[p_name]["total"] += 1
            
            # Criterio de "Fallo"
            es_fallo = False
            if row['fecha_pactada_entrega'] in [None, 'N/A', 'null', 'None', ''] or \
               row['proyecto'] in [None, 'N/A', 'null', 'None', ''] or \
               row['lote'] in [None, 'N/A', 'null', 'None', '']:
                es_fallo = True
                
            if es_fallo:
                proyectos[p_name]["fallos"] += 1
                fallos_totales += 1
                print(f"[X] ID: {row['id']} | File: {nombre_archivo} | Proyecto: {p_name} | F. Entrega: {row['fecha_pactada_entrega']} | Lote: {row['lote']}")
            else:
                correctos += 1
        
        print("\n--- RESUMEN POR PROYECTO ---")
        for p, stats in proyectos.items():
            perc = (stats['total'] - stats['fallos']) / stats['total'] * 100
            print(f"Proyecto {p}: {stats['total'] - stats['fallos']}/{stats['total']} correctos ({perc:.1f}%)")
            
        print(f"\nTOTAL: {correctos}/{total} aparentemente correctos ({ (correctos/total)*100 if total > 0 else 0 }%)")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_db()
