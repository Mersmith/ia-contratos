# 📋 Comandos de Ejecución — Automatización AYBAR CORP

## 📂 Directorio de trabajo

Abre PowerShell o CMD y navega a la carpeta:

```powershell
cd "C:\Users\AYBAR CORP SAC\Desktop\automatizacion"
```

---

## 🤖 1. Extractor de contratos con IA (Vision Premium)

Procesa los PDFs de la carpeta `analizar\` y guarda los datos en la base de datos MySQL.

```powershell
python vision_aybar_premium.py
```

---

## 📊 2. Exportar contratos a Excel

Genera un reporte `.xlsx` con todos los contratos procesados.
El archivo se guarda automáticamente en:
`C:\Users\AYBAR CORP SAC\Desktop\automatizacion\reportes\`

```powershell
python exportar_excel.py
```

---

## ⚡ Ejecutar ambos en secuencia (uno tras otro)

```powershell
python vision_aybar_premium.py ; python exportar_excel.py
```

---

## 💡 Notas rápidas

- Asegúrate de tener el archivo `.env` configurado con tus credenciales de MySQL y OpenAI.
- Poppler debe estar instalado en `C:\poppler\Library\bin`.
- Si falta alguna librería, instala dependencias con:
  ```powershell
  pip install openai mysql-connector-python pandas openpyxl python-dotenv pillow pdf2image pytesseract
  ```

---

---

# 🖥️ GUÍA DE INSTALACIÓN EN PC NUEVA (desde cero)

> Sigue este orden exacto. Todo es gratuito.

---

## PASO 1 — Instalar Python

1. Descarga Python desde: https://www.python.org/downloads/
2. Durante la instalación: ✅ marcar **"Add Python to PATH"**
3. Verifica que quedó bien:
   ```powershell
   python --version
   ```
   Debe mostrar algo como: `Python 3.11.x`

---

## PASO 2 — Instalar Laragon (MySQL + PHP)

> Laragon incluye MySQL, que es la base de datos que usa el sistema.

1. Descarga desde: https://laragon.net/download
   - Elige **"Laragon Full"** (incluye MySQL)
   - Si no puedes instalar, elige **"Laragon Portable"** (solo descomprimes el .zip)
2. Instala o descomprime en `C:\laragon`
3. Ejecuta `laragon.exe` como **Administrador**
4. Presiona **"Start All"** para iniciar MySQL

---

## PASO 3 — Instalar Poppler (para leer PDFs)

> El script usa Poppler para convertir páginas del PDF en imágenes.

1. Descarga desde: https://github.com/oschwartz10612/poppler-windows/releases
   - Descarga el `.zip` más reciente (ej: `Release-24.xx.x-0.zip`)
2. Descomprime y copia la carpeta a:
   ```
   C:\poppler\
   ```
3. La ruta final debe quedar así:
   ```
   C:\poppler\Library\bin\pdftoppm.exe   ← debe existir este archivo
   ```

---

## PASO 4 — Instalar Tesseract OCR (para leer texto de PDFs)

> Tesseract es el motor de lectura de texto en imágenes.

1. Descarga desde: https://github.com/UB-Mannheim/tesseract/wiki
   - Descarga el instalador para Windows (`.exe`)
2. Durante la instalación, selecciona el idioma **Spanish (spa)**
3. La ruta de instalación por defecto es:
   ```
   C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
4. Agrega Tesseract al PATH de Windows:
   - Busca "Variables de entorno" en el menú inicio
   - En "Variables del sistema" → `Path` → "Editar" → "Nuevo"
   - Agrega: `C:\Program Files\Tesseract-OCR`

---

## PASO 5 — Instalar librerías de Python

Abre PowerShell y ejecuta:

```powershell
pip install openai mysql-connector-python pandas openpyxl python-dotenv pillow pdf2image pytesseract
```

---

## PASO 6 — Crear la base de datos

1. Abre el navegador y entra a: http://localhost/phpmyadmin
   - Usuario: `root`
   - Contraseña: *(vacía por defecto en Laragon)*
2. Crea una base de datos llamada: `contratos`
3. Importa el archivo de estructura:
   - En phpMyAdmin → pestaña **Importar**
   - Selecciona el archivo `database.sql` de la carpeta del proyecto

---

## PASO 7 — Configurar el archivo `.env`

En la carpeta `C:\...\automatizacion\` crea un archivo llamado `.env` con este contenido:

```env
# Base de datos
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=contratos
DB_USERNAME=root
DB_PASSWORD=

# OpenAI
OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Carpeta de PDFs a procesar
CARPETA_PDF=C:\Users\TU_USUARIO\Desktop\automatizacion\analizar
```

> ⚠️ Reemplaza `sk-XXXX...` con tu clave real de OpenAI (https://platform.openai.com/api-keys)
> ⚠️ Reemplaza `TU_USUARIO` con el nombre de tu usuario de Windows

---

## PASO 8 — Verificar que todo funciona

```powershell
cd "C:\...\automatizacion"
python vision_aybar_premium.py
```

Si ves `🚀 AYBAR PREMIUM VISION — SISTEMA MULTI-MODELO`, ¡todo está listo! ✅

---

## 📦 Checklist final

- [ ] Python instalado y en PATH
- [ ] Laragon corriendo (MySQL activo)
- [ ] Poppler en `C:\poppler\Library\bin`
- [ ] Tesseract instalado y en PATH
- [ ] Librerías de Python instaladas (`pip install ...`)
- [ ] Base de datos `contratos` creada e importada
- [ ] Archivo `.env` configurado con API Key de OpenAI
- [ ] Carpeta `analizar\` con los PDFs a procesar
