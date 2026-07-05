from datetime import date, datetime

from flask import request
from flask_restx import Namespace, Resource, fields
from sqlalchemy import func

from .banco import db
from .modelos import Coluna, Tarefa


PRIORIDADES = {"baixa", "media", "alta"}

colunas_ns = Namespace("colunas", path="/colunas", description="Consulta das colunas do Kanban.")
tarefas_ns = Namespace("tarefas", path="/tarefas", description="Cadastro e manutencao das tarefas.")
relatorios_ns = Namespace("relatorios", path="/relatorios", description="Indicadores simples do quadro.")

coluna_resposta = colunas_ns.model(
    "ColunaResposta",
    {
        "id": fields.Integer(description="Identificador da coluna."),
        "nome": fields.String(description="Nome exibido no quadro."),
        "ordem": fields.Integer(description="Ordem da coluna no Kanban."),
        "total_tarefas": fields.Integer(description="Quantidade de tarefas vinculadas."),
    },
)

coluna_resumida = tarefas_ns.model(
    "ColunaResumida",
    {
        "id": fields.Integer(description="Identificador da coluna."),
        "nome": fields.String(description="Nome exibido no quadro."),
    },
)

tarefa_criacao = tarefas_ns.model(
    "TarefaCriacao",
    {
        "titulo": fields.String(required=True, description="Titulo curto da tarefa.", example="Preparar video do MVP"),
        "descricao": fields.String(description="Detalhes da tarefa.", example="Gravar demonstracao da API e do front-end."),
        "prioridade": fields.String(description="baixa, media ou alta.", example="alta"),
        "prazo": fields.String(description="Data limite no formato AAAA-MM-DD.", example="2026-07-12"),
        "coluna_id": fields.Integer(description="Coluna inicial. Se omitida, usa 'A fazer'.", example=1),
    },
)

tarefa_atualizacao = tarefas_ns.model(
    "TarefaAtualizacao",
    {
        "titulo": fields.String(description="Novo titulo da tarefa.", example="Atualizar README"),
        "descricao": fields.String(description="Nova descricao da tarefa.", example="Incluir passos de instalacao."),
        "prioridade": fields.String(description="baixa, media ou alta.", example="media"),
        "prazo": fields.String(description="Data limite no formato AAAA-MM-DD ou null.", example="2026-07-15"),
        "concluida": fields.Boolean(description="Marca a tarefa como concluida ou aberta.", example=False),
        "coluna_id": fields.Integer(description="Nova coluna da tarefa.", example=2),
    },
)

tarefa_movimento = tarefas_ns.model(
    "TarefaMovimento",
    {
        "coluna_id": fields.Integer(required=True, description="Coluna para onde a tarefa sera movida.", example=2),
    },
)

tarefa_resposta = tarefas_ns.model(
    "TarefaResposta",
    {
        "id": fields.Integer(description="Identificador da tarefa."),
        "titulo": fields.String(description="Titulo da tarefa."),
        "descricao": fields.String(description="Detalhes da tarefa."),
        "prioridade": fields.String(description="Prioridade atual."),
        "prazo": fields.String(description="Data limite no formato AAAA-MM-DD."),
        "concluida": fields.Boolean(description="Indica se a tarefa foi finalizada."),
        "criada_em": fields.String(description="Data e hora de criacao."),
        "atualizada_em": fields.String(description="Data e hora da ultima atualizacao."),
        "coluna": fields.Nested(coluna_resumida, description="Coluna atual da tarefa."),
    },
)

contagem_coluna = relatorios_ns.model(
    "ContagemColuna",
    {
        "coluna_id": fields.Integer(description="Identificador da coluna."),
        "nome": fields.String(description="Nome da coluna."),
        "total": fields.Integer(description="Quantidade de tarefas."),
    },
)

resumo_resposta = relatorios_ns.model(
    "ResumoResposta",
    {
        "total_tarefas": fields.Integer(description="Total de tarefas cadastradas."),
        "tarefas_abertas": fields.Integer(description="Tarefas ainda nao concluidas."),
        "tarefas_concluidas": fields.Integer(description="Tarefas concluidas."),
        "tarefas_atrasadas": fields.Integer(description="Tarefas abertas com prazo vencido."),
        "por_coluna": fields.List(fields.Nested(contagem_coluna), description="Distribuicao por coluna."),
        "por_prioridade": fields.Raw(description="Distribuicao por prioridade."),
    },
)


def registrar_rotas(api):
    api.add_namespace(colunas_ns)
    api.add_namespace(tarefas_ns)
    api.add_namespace(relatorios_ns)


def coluna_para_dict(coluna):
    return {
        "id": coluna.id,
        "nome": coluna.nome,
        "ordem": coluna.ordem,
        "total_tarefas": len(coluna.tarefas),
    }


def tarefa_para_dict(tarefa):
    return {
        "id": tarefa.id,
        "titulo": tarefa.titulo,
        "descricao": tarefa.descricao,
        "prioridade": tarefa.prioridade,
        "prazo": tarefa.prazo.isoformat() if tarefa.prazo else None,
        "concluida": tarefa.concluida,
        "criada_em": tarefa.criada_em.isoformat() if tarefa.criada_em else None,
        "atualizada_em": tarefa.atualizada_em.isoformat() if tarefa.atualizada_em else None,
        "coluna": {
            "id": tarefa.coluna.id,
            "nome": tarefa.coluna.nome,
        },
    }


def obter_json():
    dados = request.get_json(silent=True)
    if dados is None:
        tarefas_ns.abort(400, "Envie um corpo JSON valido.")
    return dados


def obter_tarefa_ou_404(tarefa_id):
    tarefa = db.session.get(Tarefa, tarefa_id)
    if tarefa is None:
        tarefas_ns.abort(404, "Tarefa nao encontrada.")
    return tarefa


def obter_coluna_ou_404(coluna_id):
    coluna = db.session.get(Coluna, coluna_id)
    if coluna is None:
        tarefas_ns.abort(404, "Coluna nao encontrada.")
    return coluna


def primeira_coluna():
    return Coluna.query.order_by(Coluna.ordem.asc()).first()


def limpar_texto(valor):
    if valor is None:
        return None
    return str(valor).strip()


def validar_titulo(valor):
    titulo = limpar_texto(valor)
    if not titulo:
        tarefas_ns.abort(400, "O campo titulo e obrigatorio.")
    if len(titulo) > 120:
        tarefas_ns.abort(400, "O titulo deve ter no maximo 120 caracteres.")
    return titulo


def validar_prioridade(valor):
    prioridade = limpar_texto(valor or "media").lower()
    if prioridade not in PRIORIDADES:
        tarefas_ns.abort(400, "A prioridade deve ser baixa, media ou alta.")
    return prioridade


def validar_prazo(valor):
    if valor in (None, ""):
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        tarefas_ns.abort(400, "O prazo deve estar no formato AAAA-MM-DD.")


@colunas_ns.route("")
class ListaColunas(Resource):
    @colunas_ns.marshal_list_with(coluna_resposta)
    @colunas_ns.response(200, "Colunas retornadas com sucesso.")
    def get(self):
        """Lista as colunas disponiveis no quadro Kanban."""
        colunas = Coluna.query.order_by(Coluna.ordem.asc()).all()
        return [coluna_para_dict(coluna) for coluna in colunas]


@tarefas_ns.route("")
class ListaTarefas(Resource):
    @tarefas_ns.doc(
        params={
            "coluna_id": "Filtra tarefas por coluna.",
            "prioridade": "Filtra por baixa, media ou alta.",
            "concluida": "Filtra por true ou false.",
        }
    )
    @tarefas_ns.marshal_list_with(tarefa_resposta)
    @tarefas_ns.response(200, "Tarefas retornadas com sucesso.")
    def get(self):
        """Lista tarefas com filtros opcionais."""
        consulta = Tarefa.query.join(Coluna)

        coluna_id = request.args.get("coluna_id", type=int)
        prioridade = request.args.get("prioridade")
        concluida = request.args.get("concluida")

        if coluna_id is not None:
            consulta = consulta.filter(Tarefa.coluna_id == coluna_id)
        if prioridade:
            consulta = consulta.filter(Tarefa.prioridade == validar_prioridade(prioridade))
        if concluida is not None:
            consulta = consulta.filter(Tarefa.concluida == (concluida.lower() == "true"))

        tarefas = consulta.order_by(Coluna.ordem.asc(), Tarefa.criada_em.desc()).all()
        return [tarefa_para_dict(tarefa) for tarefa in tarefas]

    @tarefas_ns.expect(tarefa_criacao, validate=True)
    @tarefas_ns.marshal_with(tarefa_resposta, code=201)
    @tarefas_ns.response(400, "Dados invalidos.")
    @tarefas_ns.response(404, "Coluna nao encontrada.")
    def post(self):
        """Cria uma nova tarefa no quadro."""
        dados = obter_json()
        coluna = obter_coluna_ou_404(dados["coluna_id"]) if dados.get("coluna_id") else primeira_coluna()

        tarefa = Tarefa(
            titulo=validar_titulo(dados.get("titulo")),
            descricao=limpar_texto(dados.get("descricao")),
            prioridade=validar_prioridade(dados.get("prioridade")),
            prazo=validar_prazo(dados.get("prazo")),
            coluna=coluna,
        )
        db.session.add(tarefa)
        db.session.commit()
        return tarefa_para_dict(tarefa), 201


@tarefas_ns.route("/<int:tarefa_id>")
@tarefas_ns.param("tarefa_id", "Identificador da tarefa.")
class DetalheTarefa(Resource):
    @tarefas_ns.marshal_with(tarefa_resposta)
    @tarefas_ns.response(200, "Tarefa encontrada.")
    @tarefas_ns.response(404, "Tarefa nao encontrada.")
    def get(self, tarefa_id):
        """Busca uma tarefa pelo identificador."""
        return tarefa_para_dict(obter_tarefa_ou_404(tarefa_id))

    @tarefas_ns.expect(tarefa_atualizacao, validate=True)
    @tarefas_ns.marshal_with(tarefa_resposta)
    @tarefas_ns.response(200, "Tarefa atualizada com sucesso.")
    @tarefas_ns.response(400, "Dados invalidos.")
    @tarefas_ns.response(404, "Tarefa ou coluna nao encontrada.")
    def put(self, tarefa_id):
        """Atualiza os dados principais de uma tarefa."""
        tarefa = obter_tarefa_ou_404(tarefa_id)
        dados = obter_json()

        if "titulo" in dados:
            tarefa.titulo = validar_titulo(dados.get("titulo"))
        if "descricao" in dados:
            tarefa.descricao = limpar_texto(dados.get("descricao"))
        if "prioridade" in dados:
            tarefa.prioridade = validar_prioridade(dados.get("prioridade"))
        if "prazo" in dados:
            tarefa.prazo = validar_prazo(dados.get("prazo"))
        if "concluida" in dados:
            tarefa.concluida = bool(dados.get("concluida"))
        if "coluna_id" in dados:
            tarefa.coluna = obter_coluna_ou_404(dados.get("coluna_id"))

        db.session.commit()
        return tarefa_para_dict(tarefa)

    @tarefas_ns.response(204, "Tarefa removida com sucesso.")
    @tarefas_ns.response(404, "Tarefa nao encontrada.")
    def delete(self, tarefa_id):
        """Remove uma tarefa do quadro."""
        tarefa = obter_tarefa_ou_404(tarefa_id)
        db.session.delete(tarefa)
        db.session.commit()
        return "", 204


@tarefas_ns.route("/<int:tarefa_id>/mover")
@tarefas_ns.param("tarefa_id", "Identificador da tarefa.")
class MovimentoTarefa(Resource):
    @tarefas_ns.expect(tarefa_movimento, validate=True)
    @tarefas_ns.marshal_with(tarefa_resposta)
    @tarefas_ns.response(200, "Tarefa movida com sucesso.")
    @tarefas_ns.response(400, "Dados invalidos.")
    @tarefas_ns.response(404, "Tarefa ou coluna nao encontrada.")
    def patch(self, tarefa_id):
        """Move uma tarefa para outra coluna do Kanban."""
        tarefa = obter_tarefa_ou_404(tarefa_id)
        dados = obter_json()
        coluna = obter_coluna_ou_404(dados.get("coluna_id"))

        tarefa.coluna = coluna
        tarefa.concluida = coluna.nome.lower() == "concluido"
        db.session.commit()
        return tarefa_para_dict(tarefa)


@relatorios_ns.route("/resumo")
class Resumo(Resource):
    @relatorios_ns.marshal_with(resumo_resposta)
    @relatorios_ns.response(200, "Resumo retornado com sucesso.")
    def get(self):
        """Mostra indicadores simples para um painel do front-end."""
        tarefas = Tarefa.query.all()
        hoje = date.today()
        por_coluna = (
            db.session.query(Coluna.id, Coluna.nome, func.count(Tarefa.id))
            .outerjoin(Tarefa)
            .group_by(Coluna.id)
            .order_by(Coluna.ordem.asc())
            .all()
        )

        por_prioridade = {prioridade: 0 for prioridade in sorted(PRIORIDADES)}
        for tarefa in tarefas:
            por_prioridade[tarefa.prioridade] = por_prioridade.get(tarefa.prioridade, 0) + 1

        concluidas = sum(1 for tarefa in tarefas if tarefa.concluida)
        atrasadas = sum(1 for tarefa in tarefas if tarefa.prazo and tarefa.prazo < hoje and not tarefa.concluida)

        return {
            "total_tarefas": len(tarefas),
            "tarefas_abertas": len(tarefas) - concluidas,
            "tarefas_concluidas": concluidas,
            "tarefas_atrasadas": atrasadas,
            "por_coluna": [
                {"coluna_id": coluna_id, "nome": nome, "total": total}
                for coluna_id, nome, total in por_coluna
            ],
            "por_prioridade": por_prioridade,
        }
