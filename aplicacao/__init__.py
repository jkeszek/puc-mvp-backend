import os

from flask import Flask
from flask_cors import CORS
from flask_restx import Api

from .banco import db
from .modelos import criar_colunas_padrao
from .rotas import registrar_rotas


def criar_app(configuracao=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'kanban.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        RESTX_VALIDATE=True,
        RESTX_MASK_SWAGGER=False,
    )

    if configuracao:
        app.config.update(configuracao)

    os.makedirs(app.instance_path, exist_ok=True)
    CORS(app, resources={r"/*": {"origins": "*"}})
    db.init_app(app)

    api = Api(
        app,
        version="1.0",
        title="API Kanban MVP",
        description="Backend em Flask para organizar tarefas em um quadro Kanban.",
        doc="/swagger",
    )
    registrar_rotas(api)

    with app.app_context():
        db.create_all()
        criar_colunas_padrao()

    return app
