# =============================================================================
# ARQUIVO: api_governo.py
# COMO RODAR: uvicorn api_governo:app --reload --port 8001
# =============================================================================

from datetime import datetime
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DO BANCO DE DADOS ISOLADO DO GOVERNO (SQLite)
# -----------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./governo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Variável para simular queda/indisponibilidade do serviço governamental (Requisito 3.11)
ESTADO_SIMULADOR = {"indisponivel": False}

# -----------------------------------------------------------------------------
# 2. MODELOS DE TABELAS DO GOVERNO (SQLAlchemy)
# -----------------------------------------------------------------------------
class GovAnimalDB(Base):
    __tablename__ = "gov_animais"
    id = Column(Integer, primary_key=True, index=True)
    microchip_rfid = Column(String, unique=True, index=True, nullable=False)
    id_externo_animal = Column(Integer, nullable=False)
    nome = Column(String, nullable=False)
    especie = Column(String, nullable=False)
    raca = Column(String, nullable=True)
    sexo = Column(String, nullable=False)
    cpf_tutor = Column(String, nullable=False)
    crmv_veterinario = Column(String, nullable=False)
    protocolo = Column(String, unique=True, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow)

class GovVacinacaoRabicaDB(Base):
    __tablename__ = "gov_vacinacoes_antirrabicas"
    id = Column(Integer, primary_key=True, index=True)
    microchip_rfid = Column(String, index=True, nullable=False)
    id_externo_animal = Column(Integer, nullable=False)
    data_aplicacao = Column(String, nullable=False)
    identificacao_vacina = Column(String, nullable=False)
    fabricante = Column(String, nullable=False)
    numero_lote = Column(String, nullable=False)
    crmv_veterinario = Column(String, nullable=False)
    # A chave_idempotencia UNIQUE impede que reenvios dupliquem a vacina no governo!
    chave_idempotencia = Column(String, unique=True, index=True, nullable=False)
    protocolo = Column(String, unique=True, index=True, nullable=False)
    data_registro = Column(DateTime, default=datetime.utcnow)

class GovOperacaoProtocoloDB(Base):
    __tablename__ = "gov_operacoes"
    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String, unique=True, index=True, nullable=False)
    tipo_operacao = Column(String, nullable=False)
    microchip_rfid = Column(String, nullable=False)
    chave_idempotencia = Column(String, nullable=True)
    status = Column(String, default="PROCESSADO_COM_SUCESSO")
    data_hora = Column(DateTime, default=datetime.utcnow)

# Cria as tabelas automaticamente ao iniciar
Base.metadata.create_all(bind=engine)

# -----------------------------------------------------------------------------
# 3. SCHEMAS DE VALIDAÇÃO (Pydantic)
# -----------------------------------------------------------------------------
class GovAnimalSchema(BaseModel):
    microchip_rfid: str
    id_externo_animal: int
    nome: str
    especie: str
    raca: Optional[str] = "SRD"
    sexo: str
    cpf_tutor: str
    crmv_veterinario: str

class GovVacinaSchema(BaseModel):
    microchip_rfid: str
    id_externo_animal: int
    data_aplicacao: str
    identificacao_vacina: str
    fabricante: str
    numero_lote: str
    crmv_veterinario: str
    chave_idempotencia: str

class SimuladorStatusSchema(BaseModel):
    indisponivel: bool

# -----------------------------------------------------------------------------
# 4. INICIALIZAÇÃO DO FASTAPI E CORS (Como ensinado pelo Prof. Fábio)
# -----------------------------------------------------------------------------
app = FastAPI(title="API Governamental Simulada - Controle de Zoonoses e RFID", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verificar_disponibilidade():
    """Se o modo indisponível estiver ativo, simula erro 503 Service Unavailable."""
    if ESTADO_SIMULADOR["indisponivel"]:
        raise HTTPException(
            status_code=503,
            detail="Serviço Governamental temporariamente indisponível (Simulação de Falha Ativa)."
        )

def gerar_protocolo(prefixo: str = "GOV") -> str:
    return f"{prefixo}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

# -----------------------------------------------------------------------------
# 5. ENDPOINTS DA API GOVERNAMENTAL SIMULADA (Seção 3.11)
# -----------------------------------------------------------------------------
@app.post("/api/governo/simular-status")
def alterar_status_simulacao(dados: SimuladorStatusSchema):
    """Liga ou desliga a simulação de queda da API Governamental."""
    ESTADO_SIMULADOR["indisponivel"] = dados.indisponivel
    estado_txt = "INDISPONÍVEL (FORA DO AR)" if dados.indisponivel else "ONLINE (OPERACIONAL)"
    return {"mensagem": f"Status da API Governamental alterado para: {estado_txt}", "indisponivel": dados.indisponivel}

@app.get("/api/governo/simular-status")
def consultar_status_simulacao():
    return ESTADO_SIMULADOR

@app.post("/api/governo/animais")
def cadastrar_animal_governo(animal: GovAnimalSchema, db: Session = Depends(get_db)):
    verificar_disponibilidade()
    existente = db.query(GovAnimalDB).filter(GovAnimalDB.microchip_rfid == animal.microchip_rfid).first()
    if existente:
        raise HTTPException(status_code=409, detail="Animal com este microchip já está registrado no Governo.")
    
    protocolo = gerar_protocolo("CAD-ANI")
    novo = GovAnimalDB(**animal.dict(), protocolo=protocolo)
    db.add(novo)
    db.add(GovOperacaoProtocoloDB(
        protocolo=protocolo,
        tipo_operacao="CADASTRO_ANIMAL",
        microchip_rfid=animal.microchip_rfid
    ))
    db.commit()
    return {"mensagem": "Animal registrado no Governo com sucesso", "protocolo": protocolo, "microchip_rfid": animal.microchip_rfid}

@app.get("/api/governo/animais/{microchip}")
def consultar_animal_governo(microchip: str, db: Session = Depends(get_db)):
    verificar_disponibilidade()
    animal = db.query(GovAnimalDB).filter(GovAnimalDB.microchip_rfid == microchip).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Microchip não localizado na base governamental.")
    return animal

@app.put("/api/governo/animais/{microchip}")
def atualizar_animal_governo(microchip: str, dados: GovAnimalSchema, db: Session = Depends(get_db)):
    verificar_disponibilidade()
    animal = db.query(GovAnimalDB).filter(GovAnimalDB.microchip_rfid == microchip).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal não encontrado no Governo para atualização.")
    
    animal.nome = dados.nome
    animal.especie = dados.especie
    animal.raca = dados.raca
    animal.sexo = dados.sexo
    animal.cpf_tutor = dados.cpf_tutor
    animal.crmv_veterinario = dados.crmv_veterinario
    animal.atualizado_em = datetime.utcnow()
    
    protocolo = gerar_protocolo("ATU-ANI")
    db.add(GovOperacaoProtocoloDB(
        protocolo=protocolo,
        tipo_operacao="ATUALIZACAO_ANIMAL",
        microchip_rfid=microchip
    ))
    db.commit()
    return {"mensagem": "Cadastro governamental atualizado", "protocolo": protocolo}

@app.post("/api/governo/vacinacoes-antirrabicas")
def registrar_vacinacao_antirrabica(vacina: GovVacinaSchema, db: Session = Depends(get_db)):
    """
    Recebe a comunicação obrigatória de vacina antirrábica (Seção 4).
    Implementa IDEMPOTÊNCIA: se a mesma chave_idempotencia for enviada duas vezes,
    não duplica o registro e devolve o mesmo protocolo original!
    """
    verificar_disponibilidade()

    # 1. Verifica Idempotência (Teste Obrigatório nº 16)
    ja_processada = db.query(GovVacinacaoRabicaDB).filter(
        GovVacinacaoRabicaDB.chave_idempotencia == vacina.chave_idempotencia
    ).first()

    if ja_processada:
        return {
            "mensagem": "Operação idempotente: vacinação já havia sido registrada anteriormente sem duplicidade.",
            "protocolo": ja_processada.protocolo,
            "idempotente": True
        }

    # 2. Cria novo registro e protocolo único
    protocolo = gerar_protocolo("VAC-RAIVA")
    nova_vac = GovVacinacaoRabicaDB(**vacina.dict(), protocolo=protocolo)
    db.add(nova_vac)
    db.add(GovOperacaoProtocoloDB(
        protocolo=protocolo,
        tipo_operacao="VACINA_ANTIRRABICA",
        microchip_rfid=vacina.microchip_rfid,
        chave_idempotencia=vacina.chave_idempotencia
    ))
    db.commit()
    return {
        "mensagem": "Vacinação antirrábica registrada com sucesso no sistema governamental.",
        "protocolo": protocolo,
        "idempotente": False
    }

@app.get("/api/governo/operacoes/{protocolo}")
def consultar_protocolo(protocolo: str, db: Session = Depends(get_db)):
    verificar_disponibilidade()
    op = db.query(GovOperacaoProtocoloDB).filter(GovOperacaoProtocoloDB.protocolo == protocolo).first()
    if not op:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")
    return op


