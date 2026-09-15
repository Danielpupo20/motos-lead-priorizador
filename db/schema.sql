-- Esquema del priorizador de leads
-- Aislamiento por empresa_id en cada tabla relevante (multi-tenant simple)

CREATE TABLE empresas (
    empresa_id      TEXT PRIMARY KEY,
    nombre          TEXT
);

CREATE TABLE puntos_venta (
    punto_venta_id  TEXT PRIMARY KEY,
    empresa_id      TEXT NOT NULL REFERENCES empresas(empresa_id)
);

CREATE TABLE asesores (
    asesor_id             TEXT PRIMARY KEY,
    nombre                TEXT,
    punto_venta_id        TEXT REFERENCES puntos_venta(punto_venta_id),
    empresa_id            TEXT NOT NULL REFERENCES empresas(empresa_id),
    capacidad_diaria_leads INTEGER,
    activo                TEXT,
    fecha_ingreso         TEXT
);

CREATE TABLE catalogo_motos (
    sku                       TEXT PRIMARY KEY,
    marca                     TEXT,
    linea                     TEXT,
    cilindraje                INTEGER,
    segmento                  TEXT,
    precio_lista              INTEGER,
    puntos_venta_disponibles  TEXT,
    unidades_disponibles      INTEGER
);

-- Leads ya normalizados y deduplicados (una fila = una persona real)
CREATE TABLE leads (
    lead_id               TEXT PRIMARY KEY,
    lead_ids_origen       TEXT,        -- ids originales fusionados en la dedup, separados por |
    empresa_id            TEXT NOT NULL REFERENCES empresas(empresa_id),
    punto_venta_id        TEXT REFERENCES puntos_venta(punto_venta_id),
    nombre_cliente        TEXT,
    telefono_normalizado  TEXT,
    email                 TEXT,
    ciudad                TEXT,
    modelo_interes_texto  TEXT,
    canal_origen          TEXT,        -- si vino de varios canales, el primero cronológicamente
    canales               TEXT,        -- todos los canales por los que escribió, separados por |
    fecha_registro        TEXT,
    estado_gestion        TEXT,
    fecha_primer_contacto TEXT,
    campania              TEXT
);

CREATE TABLE conversaciones (
    conversacion_id  TEXT PRIMARY KEY,
    lead_id          TEXT REFERENCES leads(lead_id),
    canal            TEXT,
    fecha_inicio     TEXT
);

CREATE TABLE mensajes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    conversacion_id   TEXT REFERENCES conversaciones(conversacion_id),
    emisor            TEXT,
    hora              TEXT,
    texto             TEXT
);

-- Lo que extrae el LLM de cada conversación
CREATE TABLE extracciones_ia (
    lead_id            TEXT PRIMARY KEY REFERENCES leads(lead_id),
    modelo_interes_ia  TEXT,
    presupuesto_cuota  TEXT,
    forma_pago         TEXT,
    intencion          TEXT,
    objecion_principal TEXT,
    pidio_cita         INTEGER,   -- 0/1
    confianza_extraccion REAL,
    fecha_extraccion   TEXT
);

CREATE TABLE scores (
    lead_id         TEXT PRIMARY KEY REFERENCES leads(lead_id),
    score           REAL,
    temperatura     TEXT,     -- Frío / Tibio / Caliente
    detalle_calculo TEXT,     -- JSON con el desglose de señales que explica el score
    fecha_calculo   TEXT
);

CREATE TABLE asignaciones (
    lead_id       TEXT PRIMARY KEY REFERENCES leads(lead_id),
    asesor_id     TEXT REFERENCES asesores(asesor_id),
    fecha_asignacion TEXT
);
