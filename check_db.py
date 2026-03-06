import mysql.connector
import os
import json
from dotenv import load_dotenv

load_dotenv()

def check_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            user=os.getenv('DB_USERNAME', 'root'), 
            password=os.getenv('DB_PASSWORD', ''), 
            database=os.getenv('DB_DATABASE', 'contratos'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor(dictionary=True)
        
        print("\n--- ÚLTIMOS 5 CONTRATOS EN LA DB ---")
        cursor.execute("SELECT id, proyecto, lote, manzana, area, alicuota, fecha_suscripcion_contrato, fecha_pactada_entrega, tipo_documento, tokens_entrada, tokens_salida, costo_estimado_usd FROM contratos_digitalizados ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        
        for row in rows:
            print(f"ID: {row['id']} | Tipo: {row['tipo_documento']}")
            print(f"  P: {row['proyecto']} | Mz: {row['manzana']} | Lt: {row['lote']}")
            print(f"  A: {row['area']} | Alícuota: {row['alicuota']}")
            print(f"  Sus: {row['fecha_suscripcion_contrato']} | Ent: {row['fecha_pactada_entrega']}")
            print(f"  Tokens: In:{row['tokens_entrada']} Out:{row['tokens_salida']} | Costo: ${row['costo_estimado_usd']} USD")
            print("-" * 30)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
