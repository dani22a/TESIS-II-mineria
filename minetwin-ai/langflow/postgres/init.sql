-- Base de conocimiento operativo del copiloto MineTwin (Langflow).
-- Se ejecuta solo la primera vez que se crea el volumen de Postgres.

CREATE TABLE IF NOT EXISTS procedimientos (
    codigo TEXT PRIMARY KEY,
    dominio TEXT NOT NULL,
    titulo TEXT NOT NULL,
    regla TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bitacora_turno (
    id SERIAL PRIMARY KEY,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    categoria TEXT NOT NULL DEFAULT 'OBSERVACION',
    activo TEXT,
    descripcion TEXT NOT NULL,
    autor TEXT NOT NULL DEFAULT 'copiloto-langflow'
);

INSERT INTO procedimientos (codigo, dominio, titulo, regla) VALUES
('SOP-DSP-01', 'DESPACHO', 'Umbral de cola en pala', 'Si una pala acumula 3 o más camiones en cola durante más de 10 minutos, evaluar reasignar hasta 2 camiones a la pala con menor cola. Requiere aprobación del jefe de turno.'),
('SOP-DSP-02', 'DESPACHO', 'Reasignación segura', 'Nunca reasignar un camión que esté en estado LOADING o DUMPING. Solo camiones en tránsito vacío o en cola.'),
('SOP-DSP-03', 'DESPACHO', 'Política DRL', 'La política MAPPO es la referencia de despacho. Toda desviación manual debe quedar registrada en la bitácora con su justificación.'),
('SOP-DB-01', 'TRONADURA', 'Ajuste de factor de carga', 'Los cambios de factor de carga mayores a 10% requieren validación del especialista de perforación y tronadura y revisión de vibraciones del banco.'),
('SOP-DB-02', 'TRONADURA', 'Objetivo de fragmentación', 'El P80 objetivo para alimentar al chancador primario es menor a 200 mm. Sobre 250 mm se considera riesgo de atollo en chancador.'),
('SOP-PLT-01', 'PLANTA', 'Nivel de tolva', 'Mantener la tolva del chancador CR-01 entre 40% y 85%. Bajo 40% priorizar camiones con mineral hacia chancador; sobre 85% desviar a acopio.'),
('SOP-PLT-02', 'PLANTA', 'Energía específica SAG', 'Si la energía específica del SAG supera 11 kWh/t, revisar fragmentación (P80) antes de tocar parámetros del molino.'),
('SOP-SEG-01', 'SEGURIDAD', 'Clima adverso', 'Con lluvia o barro en rampas reducir la velocidad máxima de acarreo en 20% y reportar el evento en la bitácora.'),
('SOP-SEG-02', 'SEGURIDAD', 'Aprobación humana', 'Ninguna acción que modifique despacho, tronadura o alimentación a planta se ejecuta sin aprobación humana explícita (HITL).'),
('SOP-REP-01', 'REPORTE', 'Informe de turno', 'El informe de turno incluye: KPIs de producción (t/h), estado de palas y colas, chancador y SAG, eventos de bitácora y acciones aprobadas o rechazadas.')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO bitacora_turno (categoria, activo, descripcion, autor) VALUES
('INICIO_TURNO', NULL, 'Inicio de turno A. Flota completa operativa, clima despejado.', 'jefe-de-turno'),
('OBSERVACION', 'EX-02', 'Se observa cola creciente en pala EX-02 tras cambio de frente.', 'operador-despacho'),
('MANTENCION', 'CR-01', 'Inspección visual del chancador primario sin novedades.', 'mantenedor');
