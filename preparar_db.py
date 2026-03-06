import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def update_database():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            user=os.getenv('DB_USERNAME', 'root'), 
            password=os.getenv('DB_PASSWORD', ''), 
            database=os.getenv('DB_DATABASE', 'contratos'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("DESCRIBE contratos_digitalizados")
        columns = [row[0] for row in cursor.fetchall()]
        
        if 'tokens_entrada' not in columns:
            print("Agregando columnas de tokens y costos...")
            alter_query = """
            ALTER TABLE contratos_digitalizados 
            ADD COLUMN tokens_entrada INT DEFAULT 0 AFTER texto_ocr,
            ADD COLUMN tokens_salida INT DEFAULT 0 AFTER tokens_entrada,
            ADD COLUMN costo_estimado_usd DECIMAL(10, 5) DEFAULT 0 AFTER tokens_salida;
            """
            cursor.execute(alter_query)
            conn.commit()
            print("Base de datos actualizada con éxito.")
        else:
            print("Las columnas ya existen en la base de datos.")
            
        conn.close()
    except Exception as e:
        print(f"Error actualizando la base de datos: {e}")

if __name__ == "__main__":
    update_database()
