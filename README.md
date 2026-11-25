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
git clone [https://github.com/IlkerSobrinho/vetcloud-distributed-api.git](https://github.com/IlkerSobrinho/vetcloud-distributed-api.git)
cd vetcloud-distributed-api
