import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime

# Cargar configuración desde .env
load_dotenv()

def exportar_contratos_excel():
    print("🚀 Iniciando exportación de contratos a Excel...")
    
    try:
        # 1. Conexión a la base de datos
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USERNAME", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_DATABASE", "contratos"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        
        # 2. Consulta SQL estructurada para visualización horizontal
        query = """
        SELECT 
            c.id AS 'ID Contrato',
            c.proyecto AS 'Proyecto',
            c.manzana AS 'Mz',
            c.lote AS 'Lote',
            c.area AS 'Área',
            c.alicuota AS 'Alícuota',
            c.fecha_suscripcion_contrato AS 'Fecha Suscripción',
            c.fecha_pactada_entrega AS 'Fecha Entrega Pactada',
            c.estado AS 'Estado Proceso',
            c.costo_estimado_usd AS 'Costo IA ($)',
            
            -- Propietario 1
            p1.nombre_completo AS 'Nombre Propietario 1',
            p1.dni AS 'DNI 1',
            
            -- Propietario 2
            p2.nombre_completo AS 'Nombre Propietario 2',
            p2.dni AS 'DNI 2',
            
            -- Propietario 3
            p3.nombre_completo AS 'Nombre Propietario 3',
            p3.dni AS 'DNI 3',
            
            -- Propietario 4
            p4.nombre_completo AS 'Nombre Propietario 4',
            p4.dni AS 'DNI 4',
            
            c.ruta_archivo AS 'Ruta de Archivo'

        FROM contratos_digitalizados c
        LEFT JOIN contrato_propietarios p1 ON c.id = p1.contrato_id AND p1.orden = 1
        LEFT JOIN contrato_propietarios p2 ON c.id = p2.contrato_id AND p2.orden = 2
        LEFT JOIN contrato_propietarios p3 ON c.id = p3.contrato_id AND p3.orden = 3
        LEFT JOIN contrato_propietarios p4 ON c.id = p4.contrato_id AND p4.orden = 4
        
        WHERE c.tipo_documento = 'contrato'
        ORDER BY c.id DESC;
        """
        
        # 3. Leer datos con Pandas
        df = pd.read_sql(query, conn)
        
        # 4. Generar nombre de archivo con fecha
        fecha_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        nombre_excel = f"Reporte_Contratos_Aybar_{fecha_str}.xlsx"
        
        # 5. Carpeta de destino: reportes/ junto al script
        carpeta_reportes = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
        os.makedirs(carpeta_reportes, exist_ok=True)
        ruta_excel = os.path.join(carpeta_reportes, nombre_excel)
        
        # 6. Exportar a Excel
        df.to_excel(ruta_excel, index=False, engine='openpyxl')
        
        print(f"✅ ¡Éxito! Reporte generado: {ruta_excel}")
        print(f"📊 Total de contratos exportados: {len(df)}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error durante la exportación: {e}")

if __name__ == "__main__":
    exportar_contratos_excel()
