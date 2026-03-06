-- =============================================================
-- Script de creación de base de datos
-- Motor: MySQL / MariaDB
-- Descripción: Digitalización de contratos de lotes por proyecto.
--              Un contrato puede tener 1 propietario principal
--              o N copropietarios (relación uno-a-muchos).
-- =============================================================

CREATE DATABASE IF NOT EXISTS contratos
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE contratos;

-- -------------------------------------------------------------
-- TABLA PRINCIPAL: contratos_digitalizados
-- Almacena la información general del contrato:
--   proyecto, lote, manzana, archivo fuente y estado del proceso.
-- NO almacena propietarios aquí; eso va en la tabla hija.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contratos_digitalizados (
    id               INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Identificador único del contrato',

    -- Datos de ubicación del inmueble
    proyecto         VARCHAR(255)  NOT NULL COMMENT 'Nombre del proyecto inmobiliario (ej: "Villa del Sol")',
    manzana          VARCHAR(100)  NOT NULL COMMENT 'Manzana del lote dentro del proyecto (ej: "A", "B1")',
    lote             VARCHAR(100)  NOT NULL COMMENT 'Número o código del lote (ej: "12", "23-A")',
    area             VARCHAR(100) NULL     COMMENT 'Área del lote en m² (puede ser NULL si aún no se extrae)',
    alicuota         VARCHAR(100) NULL     COMMENT 'El porcentaje de participación del lote en el proyecto',
    fecha_suscripcion_contrato         VARCHAR(100) NULL     COMMENT 'La fecha de suscripción del contrato',
    fecha_pactada_entrega         VARCHAR(100) NULL     COMMENT 'Fecha originalmente pactada para la entrega de la unidad inmobiliaria según el contrato',

    -- Datos del archivo fuente
    ruta_archivo     TEXT          NOT NULL COMMENT 'Ruta o URL al archivo PDF/imagen del contrato original',

    -- Estado del proceso de digitalización
    estado           ENUM('pendiente', 'procesado', 'error')
                                   NOT NULL DEFAULT 'pendiente'
                                   COMMENT 'Estado actual del procesamiento: pendiente | procesado | error',

    -- Tipo de documento detectado por la IA
    tipo_documento   ENUM('contrato', 'boleta', 'otro')
                                   NOT NULL DEFAULT 'otro'
                                   COMMENT 'Clasificación del documento: contrato | boleta | otro',

    -- Datos crudos retornados por la IA (para auditoría o reproceso)
    json_completo    JSON          NULL
                                   COMMENT 'JSON completo devuelto por la IA; útil para depuración y reproceso',

    -- Mejor profesional: Guardar el texto extraído por OCR
    texto_ocr        LONGTEXT      NULL
                                   COMMENT 'Texto extraído por OCR de todas las páginas del PDF. Evita reprocesar el OCR.',

    -- Auditoría de tiempo
    fecha_extraccion TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   COMMENT 'Fecha y hora en que se procesó/digitalizó el contrato',

    -- Índices para búsquedas frecuentes
    INDEX idx_proyecto  (proyecto),
    INDEX idx_manzana_lote (manzana, lote),
    INDEX idx_estado    (estado),
    INDEX idx_tipo      (tipo_documento)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Contratos de lotes digitalizados. Cada fila es un contrato único por proyecto/manzana/lote.';


-- -------------------------------------------------------------
-- TABLA HIJA: contrato_propietarios
-- Almacena los propietarios (o copropietarios) de cada contrato.
-- Relación: 1 contrato → N propietarios (mínimo 1).
--
-- El campo "orden" distingue al propietario principal (orden=1)
-- de los copropietarios (orden=2, 3, …).
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contrato_propietarios (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Identificador único del registro de propietario',

    -- Relación con el contrato padre
    contrato_id     INT          NOT NULL
                                 COMMENT 'FK al contrato al que pertenece este propietario',

    -- Orden dentro del contrato (1 = propietario principal, 2+ = copropietario)
    orden           TINYINT      NOT NULL DEFAULT 1
                                 COMMENT 'Posición del propietario: 1=principal, 2=copropietario 1, 3=copropietario 2…',

    -- Datos personales del propietario / copropietario
    nombre_completo VARCHAR(255) NOT NULL COMMENT 'Nombre completo del propietario o copropietario',
    dni             VARCHAR(20)  NOT NULL COMMENT 'Número de DNI (u otro documento de identidad) del propietario',

    -- Índices
    INDEX idx_contrato  (contrato_id),
    INDEX idx_dni       (dni),

    -- Restricción de integridad referencial
    CONSTRAINT fk_propietario_contrato
        FOREIGN KEY (contrato_id)
        REFERENCES contratos_digitalizados (id)
        ON DELETE CASCADE   -- Si se borra el contrato, se borran sus propietarios
        ON UPDATE CASCADE

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Propietarios y copropietarios de cada contrato. Un contrato puede tener 1 o más filas aquí.';
