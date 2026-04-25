-- =====================================================================
-- Schema MySQL - Detector de Anomalias em Transações Financeiras
-- =====================================================================

CREATE DATABASE IF NOT EXISTS anomaly_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE anomaly_db;

-- ---------------------------------------------------------------------
-- Tabela principal de transações
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS transacoes;

CREATE TABLE transacoes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cliente_id INT NOT NULL,
    valor DECIMAL(15,2) NOT NULL,
    data_transacao TIMESTAMP NOT NULL,
    tipo_transacao VARCHAR(50) NOT NULL,
    local VARCHAR(100),
    dispositivo VARCHAR(50),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

-- Índices para acelerar consultas do pipeline
INDEX idx_cliente_id (cliente_id),
    INDEX idx_data_transacao (data_transacao),
    INDEX idx_tipo_transacao (tipo_transacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Tabela de resultados de anomalias detectadas
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS anomalias;

CREATE TABLE anomalias (
    id INT PRIMARY KEY AUTO_INCREMENT,
    transacao_id INT NOT NULL,
    cliente_id INT NOT NULL,
    score_anomalia DECIMAL(10, 6) NOT NULL,
    metodo_deteccao VARCHAR(50) NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    detalhes JSON,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_transacao_id (transacao_id),
    INDEX idx_cliente_id (cliente_id),
    INDEX idx_metodo (metodo_deteccao),
    INDEX idx_is_anomaly (is_anomaly),
    CONSTRAINT fk_anomalia_transacao FOREIGN KEY (transacao_id) REFERENCES transacoes (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

-- ---------------------------------------------------------------------
-- View de anomalias com dados da transação (facilita dashboard)
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS vw_anomalias_detalhadas;

CREATE VIEW vw_anomalias_detalhadas AS
SELECT
    a.id AS anomalia_id,
    a.score_anomalia,
    a.metodo_deteccao,
    a.is_anomaly,
    a.detected_at,
    t.id AS transacao_id,
    t.cliente_id,
    t.valor,
    t.data_transacao,
    t.tipo_transacao,
    t.local,
    t.dispositivo,
    t.ip_address
FROM anomalias a
    INNER JOIN transacoes t ON a.transacao_id = t.id
WHERE
    a.is_anomaly = TRUE;