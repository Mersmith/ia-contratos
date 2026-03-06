# 📋 DOCUMENTACIÓN DEL FLUJO — Sistema Digitalizados

**Proyecto**: Automatización de extracción de contratos inmobiliarios  
**Empresa**: AYBAR CORP S.A.C.  
**Tecnologías**: Python + Tesseract OCR + Google Gemini / OpenAI + MySQL (Laragon)

---

## 🔄 Flujo General del Sistema

El sistema procesa automáticamente todos los PDFs de la carpeta `digitalizados`
y extrae los datos de los contratos para guardarlos en la base de datos.

---

## 📌 FASE 0 — Extracción de Texto por OCR

> **Archivo**: `ocr_utils.py`
> **Objetivo**: Convertir el PDF escaneado a **texto plano** antes de enviarlo a la IA.

La mayoría de los contratos llegan como PDFs escaneados (imágenes dentro de un PDF),
por lo que no tienen texto seleccionable. El OCR se encarga de "leer" visualmente cada
página y convertirla en texto, igual que haría un humano.

> 💡 **Ventaja clave**: Si primero extraemos el texto con OCR (gratis/local), la IA solo
> recibe texto en vez de imágenes. Esto reduce el costo por llamada de **$$$** a **$**.

---

### Instalación de dependencias

**1. Motor OCR (ejecutar en terminal):**

```bash
# Verificar que Tesseract está instalado
tesseract --version
```

> Si no está instalado, descargar desde: https://github.com/UB-Mannheim/tesseract/wiki
> Asegurarse de instalar el paquete de idioma **Español (spa)**.

**2. Librerías Python:**

```bash
pip install pytesseract   # Wrapper Python para Tesseract
pip install pdf2image     # Convierte páginas PDF a imágenes PIL
pip install pillow        # Procesamiento de imágenes
```

---

### Archivo: `ocr_utils.py`

```python
import pytesseract
from pdf2image import convert_from_path

def extraer_texto_pdf(ruta_pdf):
    """
    Convierte un PDF escaneado a texto usando OCR (Tesseract).

    Parámetros:
        ruta_pdf (str): Ruta al archivo PDF.

    Retorna:
        (texto_total, None)  → si el OCR fue exitoso.
        (None, mensaje_error) → si ocurrió un error.
    """
    texto_total = ""

    try:
        # Convierte cada página del PDF en una imagen PIL
        paginas = convert_from_path(ruta_pdf)

        for pagina in paginas:
            # Extrae el texto de la imagen en español
            texto = pytesseract.image_to_string(pagina, lang="spa")
            texto_total += texto + "\n"

        return texto_total, None

    except Exception as e:
        return None, str(e)
```

---

### Cómo se usa en el worker principal

```python
from ocr_utils import extraer_texto_pdf

# Por cada PDF encontrado en la carpeta:
texto, error_ocr = extraer_texto_pdf(ruta_completa)

if error_ocr:
    # Si el OCR falla, registrar en DB y pasar al siguiente archivo
    print(f"[ERROR OCR] {error_ocr}")
    guardar_en_db({"error": "ocr"}, ruta_completa, estado='error')
    continue

# Si el OCR fue exitoso, el texto se pasa a la FASE 1
# (en vez de enviar el PDF o imágenes directamente a la IA)
```

---

### ¿Cómo fluye el texto entre fases?

```
� PDF encontrado en carpeta
         ↓
[FASE 0] ocr_utils.py
   convert_from_path(pdf) → lista de imágenes PIL
   pytesseract.image_to_string(pagina, lang="spa")
         ↓
   texto_total (string con TODO el texto del contrato)
         ↓
[FASE 1] primera_fase.py → recibe texto_total
   IA lee el TEXTO (no imagen) y clasifica: ¿BOLETA o CONTRATO?
         ↓
[FASE 2] segunda_fase.py → recibe texto_total
   IA lee el TEXTO y extrae: cliente, lote, proyecto, DNI
         ↓
[FASE 3] Guardar en MySQL
```

---

### Mejora profesional — Guardar el texto OCR en la DB

Se recomienda guardar el texto extraído en la base de datos para **no volver a hacer OCR**
en caso de reprocesamiento:

```sql
-- Columna adicional en contratos_digitalizados:
ALTER TABLE contratos_digitalizados
    ADD COLUMN texto_ocr LONGTEXT NULL
        COMMENT 'Texto extraído por OCR de todas las páginas del PDF. Evita reprocesar el OCR.'
        AFTER json_completo;
```

En Python, antes de llamar a la IA, verificar si ya existe el OCR guardado:

```python
if registro_existente and registro_existente['texto_ocr']:
    texto = registro_existente['texto_ocr']  # Reutilizar OCR guardado
else:
    texto, error_ocr = extraer_texto_pdf(ruta_completa)  # Hacer OCR
    guardar_texto_ocr_en_db(id_contrato, texto)           # Guardar para la próxima
```

---

### Comparación de costo: Con OCR vs Sin OCR

| Método | Lo que recibe la IA | Costo por contrato | 1,000 contratos |
|---|---|---|---|
| Solo OpenAI Vision | Imágenes (10-17 por contrato) | ~$0.02 – $0.05 | ~$20 – $50 |
| **OCR + OpenAI** | **Texto plano** | **~$0.001 – $0.003** | **~$1 – $3** |

> 🚀 El OCR se ejecuta **localmente en tu máquina** (costo = $0).
> La IA solo recibe texto, que consume muchísimos menos tokens que imágenes.

---

## 📌 FASE 1 — Identificación del Documento (PRIMER FILTRO)

> **Archivo**: `primera_fase.py`
> **Recibe**: El `texto_total` producido por la **FASE 0** (OCR).
> **Objetivo**: Saber si el documento es un CONTRATO o una BOLETA antes de hacer cualquier otra cosa.

Este es el paso más importante. No tiene sentido extraer datos de una boleta de venta porque
no contiene la información que necesitamos (cliente, lote, proyecto en formato legal).

### ¿Cómo funciona?

```
texto_total (viene de FASE 0 — OCR)
           ↓
🐍 PYTHON — Toma solo las primeras líneas del texto
           (equivalente a la "página 1" pero en texto)
           ↓
        🤖 IA (OpenAI / Gemini)
        Recibe: fragmento de texto de la primera página
        Pregunta: "¿Es BOLETA o CONTRATO?"
                  ↓
     ┌────────────┴───────────────┐
     ↓                           ↓
  BOLETA                      CONTRATO
  es_contrato: false          es_contrato: true
     ↓                           ↓
Se registra como             Se pasa a la FASE 2
"no es contrato"             (Extracción de datos)
en la base de datos
```

### ¿Qué le pregunta Python a la IA?

La IA recibe la primera página del documento y analiza:

| Señal visual | BOLETA | CONTRATO |
|---|---|---|
| Título del documento | "BOLETA DE VENTA ELECTRÓNICA" | "CONTRATO PREPARATORIO DE COMPRAVENTA" |
| Código de documento | Serie: BB01-XXXXXXX | Serie: C20241XXXXXX |
| Tiene tabla de ítems | ✅ Sí | ❌ No |
| Tiene cláusulas legales | ❌ No | ✅ Sí (PRIMERA, SEGUNDA...) |
| Tiene QR de SUNAT | ✅ Sí | ❌ No |
| Páginas aproximadas | 3 a 5 | 7 a 20 |
| Tamaño del PDF | ~200 KB | ~1 MB o más |

### ¿Por qué solo la primera página?

- La primera página **siempre** contiene el título del documento.
- Enviar solo 1 página a la IA = **menor costo** (menos tokens).
- La clasificación (BOLETA vs CONTRATO) no requiere leer el documento completo.

### División de Responsabilidades:

| Tarea | Responsable | Costo |
|---|---|---|
| Encontrar todos los PDFs | 🐍 Python | Gratis |
| Extraer texto del PDF (OCR) | 🐍 Python + Tesseract (FASE 0) | Gratis |
| Tomar las primeras líneas del texto OCR | 🐍 Python | Gratis |
| Clasificar si es CONTRATO o BOLETA | 🤖 IA (OpenAI / Gemini) | Mínimo |
| Guardar resultado en la base de datos | 🐍 Python (MySQL) | Gratis |

> **Conclusión**: Python hace todo el trabajo pesado de forma gratuita.
> La IA solo se usa para la parte "inteligente" (leer y clasificar la imagen).

---

## 📌 FASE 2 — Extracción de Datos del Contrato

> **Archivo**: `segunda_fase.py` *(pendiente de crear)*
> **Solo se ejecuta si** la Fase 1 determinó que el documento **SÍ es un contrato**.

### ¿Por qué necesitamos Fase 2 separada?

En la Fase 1 solo enviamos **la primera página** para clasificar rápido y barato.
Pero los datos del cliente están en el **ANEXO 1 - INFORMACIÓN GENERAL**,
que siempre está en las páginas finales del contrato (no en la primera).

Por eso necesitamos una segunda llamada a la IA, esta vez con **todo el documento**.

---

### ¿Cómo funciona?

```
CONTRATO confirmado (viene de Fase 1)
           ↓
🐍 PYTHON — Convierte TODAS las páginas a imágenes
           ↓
    ¿Cuántas páginas tiene?
    ≤ 20 páginas              > 20 páginas
         ↓                          ↓
Envía todas las imágenes     Envía solo las últimas 10
a OpenAI en un solo llamado  (donde suele estar el Anexo 1)
         ↓
🤖 OpenAI Vision (gpt-4o-mini)
   Recibe: todas las imágenes del contrato
   Busca: "ANEXO 1 - INFORMACIÓN GENERAL"
   Extrae: cliente, lote, proyecto, DNI
         ↓
   JSON: {cliente, lote, proyecto, dni}
         ↓
🐍 Python recibe los datos
         ↓
   FASE 3: Guardar en MySQL
```

---

### ¿Qué busca la IA en el documento completo?

El **ANEXO 1 - INFORMACIÓN GENERAL** siempre contiene una tabla con:

| Campo a extraer | Dónde aparece en el contrato |
|---|---|
| `cliente` | "DATOS DEL CLIENTE" → Nombre y Apellidos |
| `lote` | "DATOS DEL INMUEBLE" → Manzana / Lote |
| `proyecto` | Logo superior o "DATOS DEL INMUEBLE" → Proyecto |
| `dni` | "DATOS DEL CLIENTE" → DNI/RUC |

---

### Estrategia inteligente — Páginas a enviar

Para no gastar tokens innecesarios, Python solo envía las páginas relevantes:

| Tamaño del contrato | Páginas que se envían | Motivo |
|---|---|---|
| 1 a 20 páginas | Todas | Es manejable en un llamado |
| 21 a 40 páginas | Últimas 15 | El Anexo 1 siempre está al final |
| Más de 40 páginas | Últimas 20 | Igual, Anexo 1 al final |

---

### División de Responsabilidades:

| Tarea | Responsable | Costo |
|---|---|---|
| Convertir todas las páginas a imágenes | 🐍 Python (PyMuPDF) | Gratis |
| Seleccionar qué páginas enviar | 🐍 Python | Gratis |
| Leer las imágenes y buscar el Anexo 1 | 🤖 OpenAI Vision | Bajo |
| Extraer: cliente, lote, proyecto | 🤖 OpenAI Vision | Bajo |
| Recibir el JSON y prepararlo para DB | 🐍 Python | Gratis |

---

### Comparación de costo por llamada:

| Fase | Imágenes enviadas | Costo estimado |
|---|---|---|
| Fase 1 (clasificar) | 1 imagen (página 1) | ~$0.001 |
| Fase 2 (extraer datos) | 10-17 imágenes | ~$0.01 a $0.02 |

---

## 📌 FASE 3 — Guardado en Base de Datos

> **Archivo**: integrado en el worker principal
> **Solo se ejecuta** al finalizar Fase 2 con datos extraídos.

Python toma el JSON que devolvió la IA y lo inserta (o actualiza) en MySQL:

```sql
INSERT INTO contratos_digitalizados
  (cliente, lote, proyecto, ruta_archivo, estado, json_completo)
VALUES
  ('RAMOS MERINO, ALFONSA', 'A1-17', 'ALTOS DEL PRADO', '/ruta/...', 'procesado', '{...}')
```

### Reglas de guardado:

| Situación | Acción |
|---|---|
| Archivo nuevo, es contrato | INSERT con estado `procesado` |
| Archivo nuevo, es boleta | INSERT con estado `procesado` (no_contrato) |
| Archivo ya existe con `error` | UPDATE → reintenta con nuevos datos |
| Archivo ya existe con `procesado` | Se omite completamente (no gasta IA) |

---

## 📌 RESUMEN GENERAL DEL FLUJO

```
worker.py
│
├── ocr_utils.py      → FASE 0
├── primera_fase.py   → FASE 1
├── segunda_fase.py   → FASE 2
│

📁 PDF encontrado en carpeta
      ↓
[FASE 0] ocr_utils.py
   Tesseract OCR → convierte páginas a texto_total
   Costo: $0 (local)
      ↓
   ¿Error OCR? → Guardar estado='error' → STOP
      ↓
[FASE 1] primera_fase.py
   IA recibe: texto (primeras líneas)
   ¿Es BOLETA o CONTRATO?
      ↓
    Boleta → Guardar "no_contrato" → STOP
    Contrato → Continuar
      ↓
[FASE 2] segunda_fase.py
   IA recibe: texto_total completo
   Busca ANEXO 1 → extrae {cliente, lote, proyecto, DNI}
      ↓
[FASE 3] Guardar en MySQL
   INSERT contratos_digitalizados + contrato_propietarios
   Guarda también texto_ocr para no reprocesar
   → DONE ✅
```

### Arquitectura de archivos

```
automatizacion/
├── worker.py           # Script principal — orquesta todas las fases
├── ocr_utils.py        # FASE 0 — Extracción OCR con Tesseract
├── primera_fase.py     # FASE 1 — Clasificación: ¿contrato o boleta?
├── segunda_fase.py     # FASE 2 — Extracción de datos del contrato
├── database.sql        # Estructura de la base de datos MySQL
└── digitalizados/      # Carpeta con los PDFs a procesar
```
