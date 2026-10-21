-- Criação do banco da GameHub API (PostgreSQL).
-- O container do Postgres executa este script automaticamente na primeira inicialização
-- (pasta /docker-entrypoint-initdb.d). Para recriar o banco: docker compose down -v && docker compose up -d

CREATE TYPE genero AS ENUM (
    'acao', 'aventura', 'rpg', 'estrategia', 'esportes',
    'corrida', 'simulacao', 'puzzle', 'terror', 'luta'
);

CREATE TABLE usuario (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(100) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    data_nascimento DATE,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE carteira (
    id            SERIAL PRIMARY KEY,
    usuario_id    INTEGER NOT NULL UNIQUE REFERENCES usuario (id) ON DELETE CASCADE,
    saldo         NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (saldo >= 0),
    atualizada_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE jogo (
    id                   SERIAL PRIMARY KEY,
    titulo               VARCHAR(150) NOT NULL,
    descricao            VARCHAR(2000),
    genero               genero NOT NULL,
    preco                NUMERIC(10, 2) NOT NULL CHECK (preco >= 0),
    data_lancamento      DATE NOT NULL,
    classificacao_etaria INTEGER NOT NULL CHECK (classificacao_etaria BETWEEN 0 AND 18),
    vendedor_id          INTEGER NOT NULL REFERENCES usuario (id),
    disponivel           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Jogos que cada carteira possui (N:N)
CREATE TABLE carteira_jogo (
    carteira_id  INTEGER NOT NULL REFERENCES carteira (id) ON DELETE CASCADE,
    jogo_id      INTEGER NOT NULL REFERENCES jogo (id),
    adquirido_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (carteira_id, jogo_id)
);

CREATE TABLE grupo (
    id        SERIAL PRIMARY KEY,
    nome      VARCHAR(60) NOT NULL,
    descricao VARCHAR(500),
    dono_id   INTEGER NOT NULL REFERENCES usuario (id),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Membros de cada grupo (N:N). O limite de 5 membros é garantido pela API.
CREATE TABLE grupo_membro (
    grupo_id   INTEGER NOT NULL REFERENCES grupo (id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    entrou_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (grupo_id, usuario_id)
);

-- Log de compras: guarda o preço pago no momento da compra
CREATE TABLE compra (
    id           SERIAL PRIMARY KEY,
    comprador_id INTEGER NOT NULL REFERENCES usuario (id),
    vendedor_id  INTEGER NOT NULL REFERENCES usuario (id),
    jogo_id      INTEGER NOT NULL REFERENCES jogo (id),
    valor_pago   NUMERIC(10, 2) NOT NULL,
    realizada_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
