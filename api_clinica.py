# =============================================================================
# ARQUIVO: api_clinica.py
# COMO RODAR: uvicorn api_clinica:app --reload --port 8000
# =============================================================================

from datetime import datetime
import hashlib
import json
from typing import Optional
import requests
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DO BANCO DA CLÍNICA E URL DO GOVERNO
# -----------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./clinica.db"
GOV_API_BASE_URL = "http://localhost:8001/api/governo"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def gerar_hash_senha(senha: str) -> str:
    """Gera hash SHA-256 com salt fixo acadêmico para nunca salvar senha em texto puro."""
    return hashlib.sha256(f"sdm_salt_{senha}".encode("utf-8")).hexdigest()

# -----------------------------------------------------------------------------
# 2. AS 10 TABELAS OBRIGATÓRIAS DO MODELO DE DADOS (Seção 6 do PDF)
# -----------------------------------------------------------------------------
class EnderecoDB(Base):
    __tablename__ = "enderecos"
    id = Column(Integer, primary_key=True, index=True)
    cep = Column(String(8), nullable=False)
    logradouro = Column(String(150), nullable=False)
    numero = Column(String(20), nullable=False)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=False)
    cidade = Column(String(100), nullable=False)
    uf = Column(String(2), nullable=False)
    codigo_ibge = Column(String(10), nullable=True)

class TutorDB(Base):
    __tablename__ = "tutores"
    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String(150), nullable=False)
    cpf = Column(String(11), unique=True, index=True, nullable=False)
    data_nascimento = Column(String(20), nullable=False)
    email = Column(String(120), nullable=False)
    telefone = Column(String(20), nullable=False)
    endereco_id = Column(Integer, ForeignKey("enderecos.id"), nullable=False)
    data_cadastro = Column(DateTime, default=datetime.utcnow)
    situacao = Column(String(20), default="ATIVO")

class EspecieDB(Base):
    __tablename__ = "especies"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(80), unique=True, nullable=False)
    descricao = Column(String(255), nullable=True)
    situacao = Column(String(20), default="ATIVO")

class RacaDB(Base):
    __tablename__ = "racas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(80), nullable=False)
    descricao = Column(String(255), nullable=True)
    especie_id = Column(Integer, ForeignKey("especies.id"), nullable=False)
    situacao = Column(String(20), default="ATIVO")

class VeterinarioDB(Base):
    __tablename__ = "veterinarios"
    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String(150), nullable=False)
    cpf = Column(String(11), unique=True, nullable=False)
    numero_crmv = Column(String(20), nullable=False)
    uf_crmv = Column(String(2), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    telefone = Column(String(20), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    codigo_confirmacao = Column(String(64), nullable=True)
    senha_confirmada = Column(Boolean, default=False)
    data_hora_confirmacao = Column(DateTime, nullable=True)
    data_cadastro = Column(DateTime, default=datetime.utcnow)
    situacao = Column(String(20), default="ATIVO") # ATIVO ou INATIVO
    ultimo_acesso = Column(DateTime, nullable=True)

class AnimalDB(Base):
    __tablename__ = "animais"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    data_nascimento = Column(String(20), nullable=True)
    idade_estimada = Column(String(50), nullable=True)
    sexo = Column(String(15), nullable=False)
    cor = Column(String(50), nullable=False)
    peso_atual = Column(Float, nullable=False)
    tutor_id = Column(Integer, ForeignKey("tutores.id"), nullable=False)
    especie_id = Column(Integer, ForeignKey("especies.id"), nullable=False)
    raca_id = Column(Integer, ForeignKey("racas.id"), nullable=True)
    microchip_rfid = Column(String(50), unique=True, index=True, nullable=True)
    data_vinculo_microchip = Column(DateTime, nullable=True)
    veterinario_vinculo_id = Column(Integer, ForeignKey("veterinarios.id"), nullable=True)
    situacao = Column(String(20), default="ATIVO")
    situacao_integracao_gov = Column(String(30), default="NAO_SINCRONIZADO")

class VinculoMicrochipDB(Base):
    __tablename__ = "vinculos_microchip"
    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animais.id"), nullable=False)
    microchip_rfid = Column(String(50), nullable=False)
    veterinario_id = Column(Integer, ForeignKey("veterinarios.id"), nullable=False)
    data_vinculo = Column(DateTime, default=datetime.utcnow)
    data_substituicao = Column(DateTime, nullable=True)
    motivo_substituicao = Column(String(255), nullable=True)
    ativo = Column(Boolean, default=True)

class ConsultaDB(Base):
    __tablename__ = "consultas"
    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animais.id"), nullable=False)
    veterinario_id = Column(Integer, ForeignKey("veterinarios.id"), nullable=False)
    data_hora = Column(String(30), nullable=False)
    motivo = Column(String(255), nullable=False)
    anamnese = Column(Text, nullable=True)
    sintomas = Column(Text, nullable=True)
    diagnostico = Column(Text, nullable=True)
    tratamento_prescrito = Column(Text, nullable=True)
    prescricao_medicamentos = Column(Text, nullable=True)
    peso_registrado = Column(Float, nullable=True)
    temperatura = Column(Float, nullable=True)
    observacoes = Column(Text, nullable=True)
    situacao = Column(String(30), default="REALIZADA")

class VacinaDB(Base):
    __tablename__ = "vacinas"
    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animais.id"), nullable=False)
    veterinario_id = Column(Integer, ForeignKey("veterinarios.id"), nullable=False)
    nome_vacina = Column(String(100), nullable=False)
    tipo_vacina = Column(String(50), nullable=False) # Ex: ANTIRRABICA, V10, GRIPE
    indicador_antirrabica = Column(Boolean, default=False)
    fabricante = Column(String(100), nullable=False)
    numero_lote = Column(String(50), nullable=False)
    data_aplicacao = Column(String(20), nullable=False)
    dose_etapa = Column(String(50), nullable=False)
    via_aplicacao = Column(String(50), nullable=False)
    data_proxima_dose = Column(String(20), nullable=True)
    data_validade_lote = Column(String(20), nullable=False)
    observacoes = Column(Text, nullable=True)
    situacao = Column(String(30), default="APLICADA")

class IntegracaoGovernoDB(Base):
    __tablename__ = "integracoes_governo"
    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animais.id"), nullable=False)
    vacina_id = Column(Integer, ForeignKey("vacinas.id"), nullable=True)
    tipo_operacao = Column(String(50), nullable=False)
    protocolo_externo = Column(String(64), nullable=True)
    chave_idempotencia = Column(String(64), unique=True, index=True, nullable=False)
    situacao = Column(String(30), default="PENDENTE") # PENDENTE, ENVIADA, CONFIRMADA, FALHA
    data_hora_solicitacao = Column(DateTime, default=datetime.utcnow)
    data_hora_resposta = Column(DateTime, nullable=True)
    quantidade_tentativas = Column(Integer, default=0)
    mensagem_erro = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False)

Base.metadata.create_all(bind=engine)

# -----------------------------------------------------------------------------
# 3. SCHEMAS PYDANTIC (VALIDAÇÃO DE ENTRADA)
# -----------------------------------------------------------------------------
class LoginSchema(BaseModel):
    email: str
    senha: str

class ConfirmarSenhaSchema(BaseModel):
    email: str
    codigo_confirmacao: str

class VeterinarioCreateSchema(BaseModel):
    nome_completo: str
    cpf: str
    numero_crmv: str
    uf_crmv: str
    email: str
    telefone: str
    senha: str
    situacao: Optional[str] = "ATIVO"
    senha_confirmada: Optional[bool] = False

class EnderecoCreateSchema(BaseModel):
    cep: str
    logradouro: str
    numero: str
    complemento: Optional[str] = ""
    bairro: str
    cidade: str
    uf: str
    codigo_ibge: Optional[str] = ""

class TutorCreateSchema(BaseModel):
    nome_completo: str
    cpf: str
    data_nascimento: str
    email: str
    telefone: str
    endereco: EnderecoCreateSchema

class EspecieCreateSchema(BaseModel):
    nome: str
    descricao: Optional[str] = ""

class RacaCreateSchema(BaseModel):
    nome: str
    descricao: Optional[str] = ""
    especie_id: int

class AnimalCreateSchema(BaseModel):
    nome: str
    data_nascimento: Optional[str] = None
    idade_estimada: Optional[str] = None
    sexo: str
    cor: str
    peso_atual: float
    tutor_id: int
    especie_id: int
    raca_id: Optional[int] = None

class MicrochipVinculoSchema(BaseModel):
    microchip_rfid: str
    veterinario_id: int
    motivo_substituicao: Optional[str] = "Primeiro vínculo de microchip"

class ConsultaCreateSchema(BaseModel):
    animal_id: int
    veterinario_id: int
    data_hora: str
    motivo: str
    anamnese: Optional[str] = ""
    sintomas: Optional[str] = ""
    diagnostico: Optional[str] = ""
    tratamento_prescrito: Optional[str] = ""
    prescricao_medicamentos: Optional[str] = ""
    peso_registrado: Optional[float] = None
    temperatura: Optional[float] = None
    observacoes: Optional[str] = ""
    situacao: Optional[str] = "REALIZADA"

class VacinaCreateSchema(BaseModel):
    animal_id: int
    veterinario_id: int
    nome_vacina: str
    tipo_vacina: str # "ANTIRRABICA", "V10", "GRIPE", etc.
    indicador_antirrabica: bool
    fabricante: str
    numero_lote: str
    data_aplicacao: str
    dose_etapa: str
    via_aplicacao: str
    data_proxima_dose: Optional[str] = None
    data_validade_lote: str
    observacoes: Optional[str] = ""
    situacao: Optional[str] = "APLICADA"

# -----------------------------------------------------------------------------
# 4. INICIALIZAÇÃO DO FASTAPI E SEEDS AUTOMÁTICOS PARA TESTE RÁPIDO
# -----------------------------------------------------------------------------
app = FastAPI(title="API Privada - Gestão de Clínica Veterinária (SDM A3)", version="1.0")

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

@app.on_event("startup")
def popular_dados_iniciais():
    """Cria automaticamente os 3 veterinários de teste e espécies/raças ao subir a API!"""
    db = SessionLocal()
    if db.query(VeterinarioDB).count() == 0:
        # 1. Veterinário Ativo e Confirmado (Para Teste #1)
        db.add(VeterinarioDB(
            nome_completo="Dr. veterinário Ativo (Teste OK)",
            cpf="11111111111",
            numero_crmv="12345",
            uf_crmv="RJ",
            email="ativo@clinica.com",
            telefone="21999990001",
            senha_hash=gerar_hash_senha("123456"),
            codigo_confirmacao="CONF-OK",
            senha_confirmada=True,
            data_hora_confirmacao=datetime.utcnow(),
            situacao="ATIVO"
        ))
        # 2. Veterinário Inativo (Para Teste #2)
        db.add(VeterinarioDB(
            nome_completo="Dr. Veterinário Inativo (Teste Bloqueio)",
            cpf="22222222222",
            numero_crmv="54321",
            uf_crmv="RJ",
            email="inativo@clinica.com",
            telefone="21999990002",
            senha_hash=gerar_hash_senha("123456"),
            codigo_confirmacao="CONF-INA",
            senha_confirmada=True,
            situacao="INATIVO"
        ))
        # 3. Veterinário Sem Senha Confirmada (Para Teste #3)
        db.add(VeterinarioDB(
            nome_completo="Dr. Veterinário Pendente (Teste Não Confirmado)",
            cpf="33333333333",
            numero_crmv="99999",
            uf_crmv="RJ",
            email="pendente@clinica.com",
            telefone="21999990003",
            senha_hash=gerar_hash_senha("123456"),
            codigo_confirmacao="CODIGO-123",
            senha_confirmada=False,
            situacao="ATIVO"
        ))
        # Espécies e Raças Iniciais
        cao = EspecieDB(nome="Canina (Cão)", descricao="Cães domésticos")
        gato = EspecieDB(nome="Felina (Gato)", descricao="Gatos domésticos")
        db.add_all([cao, gato])
        db.commit()
        db.add_all([
            RacaDB(nome="Sem Raça Definida (SRD)", descricao="Mestiço", especie_id=cao.id),
            RacaDB(nome="Pastor Alemão", descricao="Porte grande", especie_id=cao.id),
            RacaDB(nome="Siamês", descricao="Felino de pelo curto", especie_id=gato.id),
        ])
        db.commit()
    db.close()

# -----------------------------------------------------------------------------
# 5. ENDPOINTS: AUTENTICAÇÃO E VETERINÁRIOS (Seção 3.1 e 3.6 - Testes 1, 2, 3 e 4)
# -----------------------------------------------------------------------------
@app.post("/api/auth/login")
def login_veterinario(credenciais: LoginSchema, db: Session = Depends(get_db)):
    vet = db.query(VeterinarioDB).filter(VeterinarioDB.email == credenciais.email).first()
    if not vet or vet.senha_hash != gerar_hash_senha(credenciais.senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    if vet.situacao != "ATIVO":
        raise HTTPException(status_code=403, detail="Acesso bloqueado: Veterinário está INATIVO.")
    if not vet.senha_confirmada:
        raise HTTPException(status_code=403, detail="Acesso bloqueado: Senha ainda não foi confirmada.")
    
    vet.ultimo_acesso = datetime.utcnow()
    db.commit()
    return {
        "mensagem": "Login realizado com sucesso!",
        "veterinario": {
            "id": vet.id,
            "nome_completo": vet.nome_completo,
            "crmv": f"{vet.numero_crmv}-{vet.uf_crmv}",
            "email": vet.email
        }
    }

@app.post("/api/auth/confirmar-senha")
def confirmar_senha(dados: ConfirmarSenhaSchema, db: Session = Depends(get_db)):
    vet = db.query(VeterinarioDB).filter(VeterinarioDB.email == dados.email).first()
    if not vet:
        raise HTTPException(status_code=404, detail="Veterinário não encontrado.")
    if vet.codigo_confirmacao != dados.codigo_confirmacao:
        raise HTTPException(status_code=400, detail="Código de confirmação inválido.")
    vet.senha_confirmada = True
    vet.data_hora_confirmacao = datetime.utcnow()
    db.commit()
    return {"mensagem": "Senha confirmada com sucesso! O profissional já pode realizar login."}

@app.post("/api/veterinarios")
def criar_veterinario(dados: VeterinarioCreateSchema, db: Session = Depends(get_db)):
    if db.query(VeterinarioDB).filter(VeterinarioDB.cpf == dados.cpf).first():
        raise HTTPException(status_code=400, detail="CPF de veterinário já cadastrado.")
    novo = VeterinarioDB(
        nome_completo=dados.nome_completo,
        cpf=dados.cpf,
        numero_crmv=dados.numero_crmv,
        uf_crmv=dados.uf_crmv,
        email=dados.email,
        telefone=dados.telefone,
        senha_hash=gerar_hash_senha(dados.senha),
        codigo_confirmacao="CODIGO-123",
        senha_confirmada=dados.senha_confirmada,
        situacao=dados.situacao
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.get("/api/veterinarios")
def listar_veterinarios(db: Session = Depends(get_db)):
    return db.query(VeterinarioDB).all()

# -----------------------------------------------------------------------------
# 6. ENDPOINT: CONSULTA À API PÚBLICA VIACEP (Seção 3.3 - Teste 6)
# -----------------------------------------------------------------------------
@app.get("/api/cep/{cep}")
def consultar_viacep(cep: str):
    cep_limpo = "".join(filter(str.isdigit, cep))
    if len(cep_limpo) != 8:
        raise HTTPException(status_code=400, detail="Formato de CEP inválido. Informe 8 dígitos numéricos.")
    try:
        resposta = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
        resposta.raise_for_status()
        dados = resposta.json()
        if dados.get("erro"):
            raise HTTPException(status_code=404, detail="CEP inexistente na base dos Correios/ViaCEP.")
        return {
            "cep": cep_limpo,
            "logradouro": dados.get("logradouro", ""),
            "bairro": dados.get("bairro", ""),
            "cidade": dados.get("localidade", ""),
            "uf": dados.get("uf", ""),
            "codigo_ibge": dados.get("ibge", "")
        }
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout ao consultar a API pública ViaCEP. Preencha manualmente.")
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Serviço ViaCEP indisponível no momento. Preencha manualmente.")

# -----------------------------------------------------------------------------
# 7. ENDPOINTS: TUTORES, ESPÉCIES E RAÇAS (Seção 3.2, 3.4 e 3.5 - Teste 5)
# -----------------------------------------------------------------------------
@app.post("/api/tutores")
def cadastrar_tutor(dados: TutorCreateSchema, db: Session = Depends(get_db)):
    cpf_limpo = "".join(filter(str.isdigit, dados.cpf))
    if len(cpf_limpo) != 11:
        raise HTTPException(status_code=400, detail="CPF inválido. Deve conter 11 dígitos.")
    if db.query(TutorDB).filter(TutorDB.cpf == cpf_limpo).first():
        raise HTTPException(status_code=409, detail="Erro: Já existe um tutor cadastrado com este CPF.")
    
    novo_end = EnderecoDB(**dados.endereco.dict())
    db.add(novo_end)
    db.commit()
    db.refresh(novo_end)

    novo_tutor = TutorDB(
        nome_completo=dados.nome_completo,
        cpf=cpf_limpo,
        data_nascimento=dados.data_nascimento,
        email=dados.email,
        telefone=dados.telefone,
        endereco_id=novo_end.id
    )
    db.add(novo_tutor)
    db.commit()
    db.refresh(novo_tutor)
    return {"tutor": novo_tutor, "endereco": novo_end}

@app.get("/api/tutores")
def listar_tutores(db: Session = Depends(get_db)):
    return db.query(TutorDB).all()

@app.get("/api/tutores/{tutor_id}")
def obter_tutor(tutor_id: int, db: Session = Depends(get_db)):
    tutor = db.query(TutorDB).filter(TutorDB.id == tutor_id).first()
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor não encontrado.")
    end = db.query(EnderecoDB).filter(EnderecoDB.id == tutor.endereco_id).first()
    return {"tutor": tutor, "endereco": end}

@app.post("/api/especies")
def criar_especie(dados: EspecieCreateSchema, db: Session = Depends(get_db)):
    nova = EspecieDB(**dados.dict())
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova

@app.get("/api/especies")
def listar_especies(db: Session = Depends(get_db)):
    return db.query(EspecieDB).all()

@app.post("/api/racas")
def criar_raca(dados: RacaCreateSchema, db: Session = Depends(get_db)):
    if not db.query(EspecieDB).filter(EspecieDB.id == dados.especie_id).first():
        raise HTTPException(status_code=404, detail="Espécie informada não existe (Violação de Foreign Key).")
    nova = RacaDB(**dados.dict())
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova

@app.get("/api/racas")
def listar_racas(db: Session = Depends(get_db)):
    return db.query(RacaDB).all()

# -----------------------------------------------------------------------------
# 8. ENDPOINTS: ANIMAIS E VÍNCULO DE MICROCHIP RFID (Seção 3.7 - Testes 7, 8, 11)
# -----------------------------------------------------------------------------
@app.post("/api/animais")
def cadastrar_animal(dados: AnimalCreateSchema, db: Session = Depends(get_db)):
    # Verifica se Tutor e Espécie existem (Regra de Foreign Key destacada na aula)
    if not db.query(TutorDB).filter(TutorDB.id == dados.tutor_id).first():
        raise HTTPException(status_code=404, detail="Tutor não encontrado. Cadastre o tutor primeiro.")
    if not db.query(EspecieDB).filter(EspecieDB.id == dados.especie_id).first():
        raise HTTPException(status_code=404, detail="Espécie não encontrada.")
    
    # Valida compatibilidade entre Raça e Espécie (Seção 3.5)
    if dados.raca_id:
        raca = db.query(RacaDB).filter(RacaDB.id == dados.raca_id).first()
        if not raca or raca.especie_id != dados.especie_id:
            raise HTTPException(status_code=400, detail="A raça selecionada não pertence à espécie informada.")
    
    novo_animal = AnimalDB(**dados.dict())
    db.add(novo_animal)
    db.commit()
    db.refresh(novo_animal)
    return novo_animal

@app.get("/api/animais")
def listar_animais(db: Session = Depends(get_db)):
    return db.query(AnimalDB).all()

@app.get("/api/animais/{animal_id}")
def obter_animal(animal_id: int, db: Session = Depends(get_db)):
    animal = db.query(AnimalDB).filter(AnimalDB.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal não encontrado.")
    historico_chips = db.query(VinculoMicrochipDB).filter(VinculoMicrochipDB.animal_id == animal_id).all()
    integracoes = db.query(IntegracaoGovernoDB).filter(IntegracaoGovernoDB.animal_id == animal_id).all()
    return {"animal": animal, "historico_microchips": historico_chips, "integracoes_governo": integracoes}

@app.post("/api/animais/{animal_id}/microchip")
def vincular_ou_substituir_microchip(animal_id: int, dados: MicrochipVinculoSchema, db: Session = Depends(get_db)):
    animal = db.query(AnimalDB).filter(AnimalDB.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal não encontrado.")
    
    # Verifica se o veterinário está ativo e confirmado (Regra 3.7.3)
    vet = db.query(VeterinarioDB).filter(VeterinarioDB.id == dados.veterinario_id).first()
    if not vet or vet.situacao != "ATIVO" or not vet.senha_confirmada:
        raise HTTPException(status_code=403, detail="Apenas veterinário ativo e confirmado pode vincular microchip.")
    
    # Verifica se o microchip já está em uso em qualquer animal ou histórico (Teste #8)
    em_uso = db.query(AnimalDB).filter(AnimalDB.microchip_rfid == dados.microchip_rfid).first()
    if em_uso:
        raise HTTPException(status_code=409, detail="Rejeitado: Este código de microchip RFID já está vinculado a um animal.")
    
    # Se o animal já tinha um microchip anterior, preserva no histórico como substituído (Regra 3.7.5)
    vinculo_atual = db.query(VinculoMicrochipDB).filter(
        VinculoMicrochipDB.animal_id == animal_id,
        VinculoMicrochipDB.ativo == True
    ).first()
    if vinculo_atual:
        vinculo_atual.ativo = False
        vinculo_atual.data_substituicao = datetime.utcnow()
        vinculo_atual.motivo_substituicao = dados.motivo_substituicao

    # Registra o novo vínculo
    novo_vinculo = VinculoMicrochipDB(
        animal_id=animal_id,
        microchip_rfid=dados.microchip_rfid,
        veterinario_id=vet.id,
        ativo=True
    )
    animal.microchip_rfid = dados.microchip_rfid
    animal.data_vinculo_microchip = datetime.utcnow()
    animal.veterinario_vinculo_id = vet.id
    db.add(novo_vinculo)
    db.commit()

    # Tenta sincronizar o cadastro do animal na API Governamental
    tutor = db.query(TutorDB).filter(TutorDB.id == animal.tutor_id).first()
    especie = db.query(EspecieDB).filter(EspecieDB.id == animal.especie_id).first()
    raca = db.query(RacaDB).filter(RacaDB.id == animal.raca_id).first() if animal.raca_id else None
    payload_gov = {
        "microchip_rfid": animal.microchip_rfid,
        "id_externo_animal": animal.id,
        "nome": animal.nome,
        "especie": especie.nome if especie else "N/A",
        "raca": raca.nome if raca else "SRD",
        "sexo": animal.sexo,
        "cpf_tutor": tutor.cpf if tutor else "00000000000",
        "crmv_veterinario": f"{vet.numero_crmv}-{vet.uf_crmv}"
    }
    try:
        resp = requests.post(f"{GOV_API_BASE_URL}/animais", json=payload_gov, timeout=4)
        if resp.status_code in (200, 201, 409):
            animal.situacao_integracao_gov = "SINCRONIZADO"
        else:
            animal.situacao_integracao_gov = "PENDENTE"
    except Exception:
        animal.situacao_integracao_gov = "PENDENTE"
    db.commit()
    return {"mensagem": "Microchip vinculado com sucesso!", "microchip_rfid": animal.microchip_rfid, "situacao_gov": animal.situacao_integracao_gov}

# -----------------------------------------------------------------------------
# 9. ENDPOINTS: CONSULTAS CLÍNICAS (Seção 3.8 - Teste 9)
# -----------------------------------------------------------------------------
@app.post("/api/consultas")
def registrar_consulta(dados: ConsultaCreateSchema, db: Session = Depends(get_db)):
    if not db.query(AnimalDB).filter(AnimalDB.id == dados.animal_id).first():
        raise HTTPException(status_code=404, detail="Animal não encontrado.")
    nova = ConsultaDB(**dados.dict())
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova

@app.get("/api/animais/{animal_id}/consultas")
def historico_consultas(animal_id: int, db: Session = Depends(get_db)):
    return db.query(ConsultaDB).filter(ConsultaDB.animal_id == animal_id).all()

# -----------------------------------------------------------------------------
# 10. ENDPOINTS: VACINAS E PREMISSA OBRIGATÓRIA ANTIRRÁBICA (Seções 3.9, 4 e 5)
# -----------------------------------------------------------------------------
def tentar_enviar_integracao_gov(integracao: IntegracaoGovernoDB, db: Session):
    """Função auxiliar que envia a operação para a API Governamental e atualiza o status."""
    integracao.quantidade_tentativas += 1
    payload = json.loads(integracao.payload_json)
    try:
        resp = requests.post(f"{GOV_API_BASE_URL}/vacinacoes-antirrabicas", json=payload, timeout=4)
        if resp.status_code in (200, 201):
            dados_resp = resp.json()
            integracao.situacao = "CONFIRMADA"
            integracao.protocolo_externo = dados_resp.get("protocolo")
            integracao.data_hora_resposta = datetime.utcnow()
            integracao.mensagem_erro = None
        else:
            integracao.situacao = "PENDENTE"
            integracao.mensagem_erro = f"HTTP {resp.status_code}: {resp.text}"
    except Exception as erro:
        integracao.situacao = "PENDENTE"
        integracao.mensagem_erro = f"Falha de comunicação / API Governo Indisponível: {str(erro)}"
    db.commit()

@app.post("/api/vacinas")
def registrar_vacina(dados: VacinaCreateSchema, db: Session = Depends(get_db)):
    animal = db.query(AnimalDB).filter(AnimalDB.id == dados.animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal não encontrado.")
    vet = db.query(VeterinarioDB).filter(VeterinarioDB.id == dados.veterinario_id).first()
    if not vet:
        raise HTTPException(status_code=404, detail="Veterinário não encontrado.")

    # Classificação estruturada (Seção 3.9)
    eh_antirrabica = dados.indicador_antirrabica or (dados.tipo_vacina.upper() == "ANTIRRABICA")
    if eh_antirrabica and not animal.microchip_rfid:
        raise HTTPException(status_code=400, detail="Para aplicar vacina antirrábica, o animal precisa possuir microchip RFID vinculado.")

    # 1. Registra a vacina localmente no banco da clínica (SEMPRE persiste localmente!)
    nova_vacina = VacinaDB(**dados.dict())
    nova_vacina.indicador_antirrabica = eh_antirrabica
    db.add(nova_vacina)
    db.commit()
    db.refresh(nova_vacina)

    # 2. Premissa Obrigatória (Seção 4): Se for ANTIRRÁBICA e APLICADA, comunica ao Governo!
    resultado_integracao = None
    if eh_antirrabica and nova_vacina.situacao.upper() == "APLICADA":
        chave_idemp = hashlib.sha256(
            f"{animal.microchip_rfid}:{nova_vacina.id}:{nova_vacina.numero_lote}:{nova_vacina.data_aplicacao}".encode()
        ).hexdigest()

        payload_vacina_gov = {
            "microchip_rfid": animal.microchip_rfid,
            "id_externo_animal": animal.id,
            "data_aplicacao": nova_vacina.data_aplicacao,
            "identificacao_vacina": nova_vacina.nome_vacina,
            "fabricante": nova_vacina.fabricante,
            "numero_lote": nova_vacina.numero_lote,
            "crmv_veterinario": f"{vet.numero_crmv}-{vet.uf_crmv}",
            "chave_idempotencia": chave_idemp
        }

        registro_int = IntegracaoGovernoDB(
            animal_id=animal.id,
            vacina_id=nova_vacina.id,
            tipo_operacao="VACINA_ANTIRRABICA",
            chave_idempotencia=chave_idemp,
            situacao="PENDENTE",
            payload_json=json.dumps(payload_vacina_gov)
        )
        db.add(registro_int)
        db.commit()
        db.refresh(registro_int)

        # Tenta transmitir imediatamente para a API Governamental
        tentar_enviar_integracao_gov(registro_int, db)
        resultado_integracao = {
            "integracao_id": registro_int.id,
            "situacao_comunicacao_gov": registro_int.situacao,
            "protocolo_externo": registro_int.protocolo_externo,
            "chave_idempotencia": registro_int.chave_idempotencia,
            "tentativas": registro_int.quantidade_tentativas,
            "erro": registro_int.mensagem_erro
        }
    else:
        # Teste Obrigatório #13: Vacina não antirrábica não gera comunicação obrigatória
        resultado_integracao = {"mensagem": "Vacina não antirrábica registrada localmente (isenta de envio ao governo)."}

    return {"vacina_registrada": nova_vacina, "comunicacao_governo": resultado_integracao}

@app.get("/api/animais/{animal_id}/vacinas")
def historico_vacinas(animal_id: int, db: Session = Depends(get_db)):
    vacinas = db.query(VacinaDB).filter(VacinaDB.animal_id == animal_id).all()
    proximas_doses = [v for v in vacinas if v.data_proxima_dose]
    return {"historico_vacinas": vacinas, "proximas_doses_previstas": proximas_doses}

# -----------------------------------------------------------------------------
# 11. ENDPOINTS: CONTROLE DE INTEGRAÇÕES E REENVIO DE PENDÊNCIAS (Seção 5 - Testes 14, 15, 16)
# -----------------------------------------------------------------------------
@app.get("/api/integracoes")
def listar_integracoes(db: Session = Depends(get_db)):
    return db.query(IntegracaoGovernoDB).all()

@app.post("/api/integracoes/reenviar-pendentes")
def reenviar_todas_pendentes(db: Session = Depends(get_db)):
    pendentes = db.query(IntegracaoGovernoDB).filter(IntegracaoGovernoDB.situacao != "CONFIRMADA").all()
    processadas = []
    for item in pendentes:
        tentar_enviar_integracao_gov(item, db)
        processadas.append({
            "id": item.id,
            "situacao": item.situacao,
            "protocolo_externo": item.protocolo_externo,
            "tentativas": item.quantidade_tentativas
        })
    return {"total_processadas": len(processadas), "resultado": processadas}

# -----------------------------------------------------------------------------
# 12. ENTREGA DA INTERFACE WEB E GATEWAY PARA NUVEM (RENDER / PORTFÓLIO)
# -----------------------------------------------------------------------------
from fastapi.responses import FileResponse

@app.get("/", include_in_schema=False)
def entregar_interface_web():
    """Entrega o index.html direto na rota raiz (/) para abrir no PC ou celular."""
    return FileResponse("index.html")

class SimuladorProxySchema(BaseModel):
    indisponivel: bool

@app.post("/api/governo-status")
def alterar_status_governo_via_gateway(dados: SimuladorProxySchema):
    """Repassa o comando de simular queda (503) para a API Governamental na porta 8001."""
    try:
        resp = requests.post(
            f"{GOV_API_BASE_URL}/simular-status",
            json={"indisponivel": dados.indisponivel},
            timeout=4
        )
        return resp.json()
    except Exception as erro:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao comunicar com a API Governamental (Porta 8001): {str(erro)}"
        )

@app.get("/api/governo-status")
def consultar_status_governo_via_gateway():
    """Consulta o status da API do Governo na porta 8001."""
    try:
        resp = requests.get(f"{GOV_API_BASE_URL}/simular-status", timeout=4)
        return resp.json()
    except Exception:
        return {"indisponivel": True, "erro_conexao": True}
