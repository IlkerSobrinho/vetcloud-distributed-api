# VetCloud — Sistema de Gestão de Clínica Veterinária (A3 - SDM)

Sistema web distribuído desenvolvido para a Avaliação A3 da disciplina de **Sistemas Distribuídos e Mobile (SDM)** do Centro Universitário IBMR.

- **Aplicação em Produção (Render):** https://nzk-vetcloud.onrender.com
- **Documentação Swagger (API Clínica):** https://nzk-vetcloud.onrender.com/docs

> **Nota sobre a nuvem gratuita:** O ambiente hospedado no Render entra em modo de hibernação após períodos de inatividade; o primeiro acesso pode levar cerca de 50 segundos para inicializar os dois serviços.

---

## Arquitetura do Sistema

O projeto aplica fundamentos de **Sistemas Distribuídos**, operando com microsserviços independentes, bancos SQLite fisicamente isolados e comunicação via HTTP/REST (JSON):

1. **API Privada da Clínica (`api_clinica.py` — Porta 8000)**
   - Persistência relacional via SQLite (`clinica.db`) com SQLAlchemy (10 entidades obrigatórias).
   - Autenticação de veterinários com hash **SHA-256 + salt** e trava tripla (cadastro ativo, senha confirmada e credenciais válidas).
   - Integração com a API pública **ViaCEP** com tratamento de formato inválido (`400`), CEP inexistente (`404`), indisponibilidade (`503`) e timeout (`504`).
   - Vínculo e substituição de microchip RFID com histórico e gestão de fila de pendências/retentativas.
   - Entrega da interface web (`GET /`) e gateway de status governamental (`/api/governo-status`).

2. **API Governamental Simulada (`api_governo.py` — Porta 8001)**
   - Persistência independente em banco próprio (`governo.db` — 3 tabelas).
   - Registro e atualização de animais microchipados e recebimento obrigatório de vacinações antirrábicas com emissão de protocolos únicos.
   - Garantia de **idempotência** via `chave_idempotencia` (`UNIQUE`), impedindo duplicidade em retentativas.
   - Simulador de indisponibilidade (`HTTP 503`) para validação de tolerância a falhas.

3. **Frontend Web (`index.html`)**
   - Interface responsiva construída em **HTML5, CSS3 customizado e JavaScript Vanilla (`fetch`)**, sem dependência de frameworks externos.
   - Detecção automática de ambiente (execução local ou nuvem), 5 módulos operacionais, painel de simulação de queda do governo e console integrado de respostas HTTP/JSON.

4. **Orquestrador de Execução (`start.py`)**
   - Inicializa a API Governamental em segundo plano na porta `8001` e sobe a API Privada na porta pública configurada (`PORT` no ambiente em nuvem ou `8000` localmente), mantendo os dois processos e bancos desacoplados.

---

## Como Executar Localmente

### 1. Clonar o Repositório

```bash
git clone https://github.com/IlkerSobrinho/vetcloud-distributed-api.git
cd vetcloud-distributed-api
```

### 2. Criar e Ativar o Ambiente Virtual

**Windows (PowerShell):**

```powershell
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar as Dependências

```bash
pip install -r requirements.txt
```

### 4. Iniciar os Serviços

**Opção A — Dois terminais separados** (recomendado para rodar os testes do Postman):

Terminal 1 — API Governamental (Porta 8001):

```bash
uvicorn api_governo:app --reload --port 8001
```

Terminal 2 — API Privada da Clínica (Porta 8000):

```bash
uvicorn api_clinica:app --reload --port 8000
```

**Opção B — Inicialização unificada** (mesmo modo usado no Render):

```bash
python start.py
```

> **Nota:** Na primeira inicialização, os arquivos `clinica.db` e `governo.db` são criados automaticamente com os veterinários de teste, espécies e raças iniciais.

---

## Acessos e Documentação

| Recurso | URL |
|---|---|
| Interface Web (Nuvem) | https://nzk-vetcloud.onrender.com |
| Swagger OpenAPI — Clínica (Nuvem) | https://nzk-vetcloud.onrender.com/docs |
| Interface Web (Local) | http://localhost:8000 |
| Swagger OpenAPI — Clínica (Local) | http://localhost:8000/docs |
| Swagger OpenAPI — Governo (Local) | http://localhost:8001/docs |

## Contas Pré-configuradas para Teste de Login

| E-mail | Senha | Comportamento Esperado |
|---|---|---|
| `ativo@clinica.com` | `123456` | HTTP 200 OK — Veterinário ativo e com senha confirmada |
| `inativo@clinica.com` | `123456` | HTTP 403 Forbidden — Bloqueio de acesso para profissional inativo |
| `pendente@clinica.com` | `123456` | HTTP 403 Forbidden — Bloqueio por senha não confirmada (Código: `CODIGO-123`) |

---

## Testes Automatizados (Postman)

Os 16 cenários obrigatórios de homologação (autenticação, CPF duplicado, ViaCEP, microchip RFID, prontuário, vacinas, indisponibilidade 503, reenvio de pendências e idempotência) podem ser executados em sequência pelo Postman Collection Runner:

1. Suba os dois serviços localmente nas portas 8000 e 8001.
2. Importe o arquivo `VetDistribuido_Testes_A3.postman_collection.json` no Postman.
3. Clique em **Run collection** para validar automaticamente todas as asserções (T01 a T16).

---

## Estrutura do Projeto

```text
vetcloud-distributed-api/
├── api_clinica.py          # API Privada da Clínica (Porta 8000 + Gateway + Frontend)
├── api_governo.py          # API Governamental Simulada (Porta 8001 + Idempotência)
├── start.py                # Orquestrador para execução dos dois serviços em nuvem
├── index.html              # Interface Web responsiva (HTML5, CSS3, Fetch API)
├── requirements.txt        # Dependências Python
├── schema.sql              # Esquema SQL das tabelas relacionais
├── clinica.db              # Banco SQLite da clínica (gerado automaticamente)
├── governo.db              # Banco SQLite do governo (gerado automaticamente)
├── .gitignore
└── README.md
```
