-- =========================================================================
-- 1. ESQUEMA DO BANCO DA CLÍNICA (10 ENTIDADES OBRIGATÓRIAS - SEÇÃO 6)
-- =========================================================================

CREATE TABLE enderecos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cep VARCHAR(8) NOT NULL,
    logradouro VARCHAR(150) NOT NULL,
    numero VARCHAR(20) NOT NULL,
    complemento VARCHAR(100),
    bairro VARCHAR(100) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    uf CHAR(2) NOT NULL,
    codigo_ibge VARCHAR(10)
);

CREATE TABLE tutores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo VARCHAR(150) NOT NULL,
    cpf VARCHAR(11) NOT NULL UNIQUE,
    data_nascimento DATE NOT NULL,
    email VARCHAR(120) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    endereco_id INTEGER NOT NULL,
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    situacao VARCHAR(20) DEFAULT 'ATIVO',
    FOREIGN KEY (endereco_id) REFERENCES enderecos(id)
);

CREATE TABLE especies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(80) NOT NULL UNIQUE,
    descricao VARCHAR(255),
    situacao VARCHAR(20) DEFAULT 'ATIVO'
);

CREATE TABLE racas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(80) NOT NULL,
    descricao VARCHAR(255),
    especie_id INTEGER NOT NULL,
    situacao VARCHAR(20) DEFAULT 'ATIVO',
    FOREIGN KEY (especie_id) REFERENCES especies(id)
);

CREATE TABLE veterinarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo VARCHAR(150) NOT NULL,
    cpf VARCHAR(11) NOT NULL UNIQUE,
    numero_crmv VARCHAR(20) NOT NULL,
    uf_crmv CHAR(2) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    telefone VARCHAR(20) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    codigo_confirmacao VARCHAR(64),
    senha_confirmada BOOLEAN DEFAULT 0,
    data_hora_confirmacao DATETIME,
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    situacao VARCHAR(20) DEFAULT 'ATIVO',
    ultimo_acesso DATETIME
);

CREATE TABLE animais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL,
    data_nascimento VARCHAR(20),
    idade_estimada VARCHAR(50),
    sexo VARCHAR(15) NOT NULL,
    cor VARCHAR(50) NOT NULL,
    peso_atual REAL NOT NULL,
    tutor_id INTEGER NOT NULL,
    especie_id INTEGER NOT NULL,
    raca_id INTEGER,
    microchip_rfid VARCHAR(50) UNIQUE,
    data_vinculo_microchip DATETIME,
    veterinario_vinculo_id INTEGER,
    situacao VARCHAR(20) DEFAULT 'ATIVO',
    situacao_integracao_gov VARCHAR(30) DEFAULT 'NAO_SINCRONIZADO',
    FOREIGN KEY (tutor_id) REFERENCES tutores(id),
    FOREIGN KEY (especie_id) REFERENCES especies(id),
    FOREIGN KEY (raca_id) REFERENCES racas(id),
    FOREIGN KEY (veterinario_vinculo_id) REFERENCES veterinarios(id)
);

CREATE TABLE vinculos_microchip (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    microchip_rfid VARCHAR(50) NOT NULL,
    veterinario_id INTEGER NOT NULL,
    data_vinculo DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_substituicao DATETIME,
    motivo_substituicao VARCHAR(255),
    ativo BOOLEAN DEFAULT 1,
    FOREIGN KEY (animal_id) REFERENCES animais(id),
    FOREIGN KEY (veterinario_id) REFERENCES veterinarios(id)
);

CREATE TABLE consultas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    veterinario_id INTEGER NOT NULL,
    data_hora DATETIME NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    anamnese TEXT,
    sintomas TEXT,
    diagnostico TEXT,
    tratamento_prescrito TEXT,
    prescricao_medicamentos TEXT,
    peso_registrado REAL,
    temperatura REAL,
    observacoes TEXT,
    situacao VARCHAR(30) DEFAULT 'REALIZADA',
    FOREIGN KEY (animal_id) REFERENCES animais(id),
    FOREIGN KEY (veterinario_id) REFERENCES veterinarios(id)
);

CREATE TABLE vacinas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    veterinario_id INTEGER NOT NULL,
    nome_vacina VARCHAR(100) NOT NULL,
    tipo_vacina VARCHAR(50) NOT NULL, -- ANTIRRABICA, POLIVALENTE_V10, GRIPE, OUTRA
    indicador_antirrabica BOOLEAN NOT NULL DEFAULT 0,
    fabricante VARCHAR(100) NOT NULL,
    numero_lote VARCHAR(50) NOT NULL,
    data_aplicacao VARCHAR(20) NOT NULL,
    dose_etapa VARCHAR(50) NOT NULL,
    via_aplicacao VARCHAR(50) NOT NULL,
    data_proxima_dose VARCHAR(20),
    data_validade_lote VARCHAR(20) NOT NULL,
    observacoes TEXT,
    situacao VARCHAR(30) DEFAULT 'APLICADA',
    FOREIGN KEY (animal_id) REFERENCES animais(id),
    FOREIGN KEY (veterinario_id) REFERENCES veterinarios(id)
);

CREATE TABLE integracoes_governo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    vacina_id INTEGER,
    tipo_operacao VARCHAR(50) NOT NULL,
    protocolo_externo VARCHAR(64),
    chave_idempotencia VARCHAR(64) NOT NULL UNIQUE,
    situacao VARCHAR(30) DEFAULT 'PENDENTE', -- PENDENTE, ENVIADA, CONFIRMADA, FALHA
    data_hora_solicitacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_hora_resposta DATETIME,
    quantidade_tentativas INTEGER DEFAULT 0,
    mensagem_erro TEXT,
    payload_json TEXT,
    FOREIGN KEY (animal_id) REFERENCES animais(id),
    FOREIGN KEY (vacina_id) REFERENCES vacinas(id)
);


