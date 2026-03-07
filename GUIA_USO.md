# 📖 Guía de Uso: Sistema de Extracción Aybar Vision Premium

## 1. Objetivo
Esta guía proporciona las instrucciones necesarias para que el usuario pueda operar el sistema de extracción de datos de contratos de forma correcta, asegurando que los documentos PDF se procesen, clasifiquen y guarden en la base de datos sin errores.

---

## 2. Configuración del Entorno (.env)
Antes de ejecutar el sistema, es indispensable configurar el archivo `.env` en la raíz de la carpeta. Este archivo contiene las "llaves" del sistema:

```env
# Configuración OpenAI
OPENAI_API_KEY=tu_api_key_aqui
OPENAI_ORGANIZATION=tu_org_id
OPENAI_PROJECT=tu_project_id

# Configuración Base de Datos (Laragon/MySQL)
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=contratos
DB_USERNAME=root
DB_PASSWORD=

# Rutas de Archivos
CARPETA_PDF=C:\Ruta\Hacia\Tus\PDFs\entrenar
POPPLER_PATH=C:\poppler\Library\bin
```
*Asegúrese de que `CARPETA_PDF` apunte al lugar donde colocará los contratos nuevos.*

---

## 3. Flujo General de Operación

El proceso de uso diario sigue estos pasos sencillos:

1.  **Carga:** Coloque los archivos PDF de los contratos en la carpeta configurada (ej: `\entrenar`).
2.  **Ejecución:** Abra una terminal en la carpeta del proyecto y ejecute:
    ```bash
    python vision_aybar_premium.py
    ```
3.  **Procesamiento:** El sistema detectará automáticamente los archivos nuevos, aplicará el filtro de boletas y el radar de páginas.
4.  **Verificación:** Una vez finalizado, puede verificar los datos ingresados ejecutando:
    ```bash
    python check_db.py
    ```

---

## 4. Gestión de Resultados en la Base de Datos
El sistema está diseñado para ser "inteligente":
*   **Omitir Duplicados:** Si intenta procesar un archivo que ya está en la base de datos, el script lo saltará automáticamente para ahorrar costos.
*   **Clasificación Automática:** Si el sistema detecta que el documento es una Boleta, lo guardará con el tipo `boleta` y no extraerá datos de propietarios.

---

## 5. Recomendaciones de Uso

Para garantizar un 100% de precisión, siga estas prácticas:

*   **Calidad del PDF:** Los contratos deben estar bien escaneados. Si el PDF está muy borroso o "chueco", la precisión de la IA podría verse afectada.
*   **Documentos Multipage:** El sistema maneja contratos largos (20+ páginas) gracias al radar, pero asegúrese de que el PDF contenga las páginas de firmas y anexos.
*   **Correcciones a Mano:** Si un contrato tiene cambios escritos con lapicero, el sistema los leerá. Procure que estas anotaciones sean legibles.
*   **Nuevos Proyectos:** Si la empresa lanza un nuevo proyecto con un formato de contrato totalmente diferente, informe al administrador para añadir el nuevo patrón a la `TABLA_ENTRENAR.md`.

---

## 6. Solución de Problemas Comunes
*   **Error de Base de Datos:** Verifique que Laragon o su servidor MySQL esté encendido.
*   **Error de Poppler:** Asegúrese de que la ruta en el `.env` sea la correcta hacia la carpeta `bin` de Poppler.
*   **Falta de Datos en la Extracción:** Si un campo sale `null`, revise si la página donde debería estar la información fue detectada por el radar (verifique los logs del script).
