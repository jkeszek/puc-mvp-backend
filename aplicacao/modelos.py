from datetime import datetime, timezone

from .banco import db


def agora_utc():
    return datetime.now(timezone.utc)


class Coluna(db.Model):
    __tablename__ = "colunas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    criada_em = db.Column(db.DateTime(timezone=True), nullable=False, default=agora_utc)

    tarefas = db.relationship(
        "Tarefa",
        back_populates="coluna",
        cascade="all, delete-orphan",
        lazy=True,
    )


class Tarefa(db.Model):
    __tablename__ = "tarefas"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    prioridade = db.Column(db.String(20), nullable=False, default="media")
    prazo = db.Column(db.Date, nullable=True)
    concluida = db.Column(db.Boolean, nullable=False, default=False)
    criada_em = db.Column(db.DateTime(timezone=True), nullable=False, default=agora_utc)
    atualizada_em = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=agora_utc,
        onupdate=agora_utc,
    )

    coluna_id = db.Column(db.Integer, db.ForeignKey("colunas.id"), nullable=False)
    coluna = db.relationship("Coluna", back_populates="tarefas")


def criar_colunas_padrao():
    if Coluna.query.count() > 0:
        return

    colunas = [
        Coluna(nome="A fazer", ordem=1),
        Coluna(nome="Em andamento", ordem=2),
        Coluna(nome="Concluido", ordem=3),
    ]
    db.session.add_all(colunas)
    db.session.commit()
