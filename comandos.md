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

## 💡 Notas

- Asegúrate de tener el archivo `.env` configurado con tus credenciales de MySQL y OpenAI.
- Poppler debe estar instalado en `C:\poppler\Library\bin`.
- Si falta alguna librería, instala dependencias con:
  ```powershell
  pip install openai mysql-connector-python pandas openpyxl python-dotenv pillow pdf2image pytesseract
  ```
