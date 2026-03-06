contratos_digitalizados 
    proyecto         VARCHAR(255)  NOT NULL COMMENT 'Nombre del proyecto inmobiliario (ej: "Villa del Sol")',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\proyecto

    manzana          VARCHAR(100)  NOT NULL COMMENT 'Manzana del lote dentro del proyecto (ej: "A", "B1")',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\manzana

    lote             VARCHAR(100)  NOT NULL COMMENT 'Número o código del lote (ej: "12", "23-A")',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\lote-y-manzana

    area             VARCHAR(100) NULL     COMMENT 'Área del lote en m² (puede ser NULL si aún no se extrae)',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\area

    alicuota         VARCHAR(100) NULL     COMMENT 'El porcentaje de participación del lote en el proyecto',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\lote-y-manzana

    fecha_suscripcion_contrato         VARCHAR(100) NULL     COMMENT 'La fecha de suscripción del contrato',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\fecha-suscripcion-contrato

    fecha_pactada_entrega         VARCHAR(100) NULL     COMMENT 'Fecha originalmente pactada para la entrega de la unidad inmobiliaria según el contrato',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\fecha-pactada-entrega

    ## 🗺️ Mapa de Patrones — fecha_pactada_entrega

    Este campo puede aparecer en distintas ubicaciones según el modelo de contrato.
    La IA debe revisar TODOS los patrones hasta encontrar el valor real.

    | Patrón | Modelo de Contrato          | Cláusula / Sección             | Frase Clave a Buscar                                                                 | Ejemplo de Valor Extraído      |
    |--------|-----------------------------|--------------------------------|--------------------------------------------------------------------------------------|-------------------------------|
    | **A**  | Viña del Mar                | QUINTO 5.1                     | "LAS PARTES acuerdan que la entrega física de la alícuota... **se realizara en [MES] de [AÑO]**" | `diciembre de 2024`           |
    | **B**  | Altos del Prado / Grocio    | QUINTO 5.1                     | "LAS PARTES acuerdan que la entrega física de LA ALICUOTA **se realizará a partir de [MES] de [AÑO]**" | `diciembre de 2027`      |
    | **C**  | Lugo / Lotes del Perú       | SEXTA                          | "LAS PARTES acuerdan que la entrega del ALICUOTA... **se realizara en [MES] del año [AÑO]**" | `diciembre del año 2021`  |
    | **D**  | Altos del Valle             | Anexo 1 — VII. DE LA ENTREGA   | Campo: **"Plazo de Entrega"** con valor tipo `año XXXX mes [MES]`                    | `año 2028 mes diciembre`      |
    | **E**  | Altos del Prado / Finca Las Lomas | Anexo 1 — VIII. FIRMA DEFINITIVO | Campo: **"Fecha de firma de contrato definitivo"** con fecha literal o numérica    | `30/06/2027`                  |
    | **F**  | Pontevedra / Posesión        | SÉPTIMO: ENTREGA DE LA POSESIÓN  | Frase: "...entregará la posesión de LA ALICUOTA ... el **[DIA] [MES] del [AÑO]**" | `30 diciembre del 2021`        |

    ⚠️ Si una cláusula dice "se realizará en la fecha indicada en el ANEXO 1", el valor real está en los cuadros del Anexo 1 (Patrón D o E).
    ⚠️ Ser flexible con "SÉPTIMO" o "SEPTIMO".
    ⚠️ Si no se encuentra ningún patrón, devolver null. NUNCA inventar una fecha.

contrato_propietarios 
    nombre_completo VARCHAR(255) NOT NULL COMMENT 'Nombre completo del propietario o copropietario',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\comprador

    dni             VARCHAR(20)  NOT NULL COMMENT 'Número de DNI (u otro documento de identidad) del propietario',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\comprador
