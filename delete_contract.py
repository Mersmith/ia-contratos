import mysql.connector; import os; from dotenv import load_dotenv; load_dotenv(); conn = mysql.connector.connect(host='127.0.0.1', user='root', password='', database='contratos'); cursor = conn.cursor(); cursor.execute(\
DELETE
FROM
contratos_digitalizados
WHERE
lote
=
06
AND
manzana
=
B
AND
proyecto
LIKE
%FINCA LAS LOMAS%
\); conn.commit(); print(f'Filas eliminadas: {cursor.rowcount}'); conn.close()
