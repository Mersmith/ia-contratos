# 🧠 Manual de Entrenamiento — Visión Premium (AYBAR CORP)

Este documento detalla la lógica de "entrenamiento" (Prompt Engineering) aplicada en el script `vision_aybar_premium.py` para garantizar una extracción del 100% de fidelidad.

---

## 🚀 Flujo Logístico del Script

El "entrenamiento" no es solo texto, es un flujo de 3 fases diseñado para ahorrar costos y maximizar precisión:

1.  **Fase 0: Filtro de Seguridad (OCR Local):**
    *   Se escanea la página 1 con Tesseract.
    *   Si detecta "BOLETA DE VENTA", el sistema la marca como `boleta` y detiene el proceso premium (Ahorro de tokens).

2.  **Fase 1: El Radar (Detección de Páginas):**
    *   El script recorre todo el PDF buscando palabras clave: `ANEXO`, `MEMORIA`, `FECHA DE FIRMA`, `VIII`, `VII`.
    *   Solo envía a la IA las páginas que contienen datos críticos.

3.  **Fase 2: Visión GPT-4o (300 DPI):**
    *   Envía imágenes de alta resolución solo de las páginas detectadas por el radar.

---

## 📋 Mapeo de Campos Técnicos (SQL)

| Campo SQL | Ubicación en Contrato | Regla de Extracción |
| :--- | :--- | :--- |
| `proyecto` | Logo / Encabezado | Identificar nombre comercial (ej: Finca Las Lomas, Lugo). |
| `manzana` / `lote` | Anexo 1 - Punto V | Buscar tabla de "IDENTIFICACIÓN DEL INMUEBLE". |
| `area` / `alicuota` | Memoria Descriptiva | Extraer valor numérico y unidad (m² / %). |
| `fecha_suscripcion_contrato` | Final del documento | Ubicar la frase: "Lima, [DIA] de [MES] de [AÑO]" cerca de las firmas. |
| `fecha_pactada_entrega` | Anexos / Cláusulas | **CAMPO CRÍTICO.** Seguir el Mapa de Patrones (ver abajo). |

---

## 🗺️ Mapa de Patrones — fecha_pactada_entrega

| Patrón | Modelo de Contrato          | Cláusula / Sección             | Frase Clave a Buscar                                                                 | Ejemplo de Valor Extraído      |
|--------|-----------------------------|--------------------------------|--------------------------------------------------------------------------------------|-------------------------------|
| **A**  | Viña del Mar                | QUINTO 5.1                     | "...se realizara en [MES] de [AÑO]" | `diciembre de 2024`           |
| **B**  | Altos del Prado / Grocio    | QUINTO 5.1                     | "...se realizará a partir de [MES] de [AÑO]" | `diciembre de 2027`      |
| **C**  | Lugo / Lotes del Perú       | SEXTA                          | "...se realizara en [MES] del año [AÑO]" | `diciembre del año 2021`  |
| **D**  | Altos del Valle             | Anexo 1 — VII                  | Campo: **"Plazo de Entrega"** (año XXXX mes [MES]) | `año 2028 mes diciembre`      |
| **E**  | Finca Las Lomas / Prado | Anexo 1 — VIII                 | Campo: **"Fecha de firma de contrato definitivo"** | `30/06/2027`                  |
| **F**  | Pontevedra / Posesión        | SÉPTIMO                        | "...entregará la posesión... el [DIA] [MES] del [AÑO]" | `30 diciembre del 2021`        |

---

## ⚠️ Reglas de Oro para la IA

1.  **Prioridad Manuscrita:** Si existe una corrección con lapicero sobre un texto impreso, el valor del lapicero tiene **prioridad total**.
2.  **Inducción por Anexo:** Si la cláusula de entrega dice "según Anexo 1", la IA debe ignorar el texto actual y buscar estrictamente los cuadros de los patrones D o E.
3.  **Propietarios:** Extraer siempre la lista completa del Punto II del Anexo 1 (Información del Cliente). No omitir copropietarios.
4.  **No Inventar:** Si el radar falla y no hay página de firmas, devolver `null` en fecha de suscripción. Jamás inventar fechas.
