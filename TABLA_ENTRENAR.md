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
    
contrato_propietarios 
    nombre_completo VARCHAR(255) NOT NULL COMMENT 'Nombre completo del propietario o copropietario',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\comprador

    dni             VARCHAR(20)  NOT NULL COMMENT 'Número de DNI (u otro documento de identidad) del propietario',
    C:\Users\AYBAR CORP SAC\Desktop\automatizacion\campos\comprador
