# API Kanban MVP

Backend em Python e Flask para um quadro Kanban simples. A API permite cadastrar, consultar, atualizar, mover e remover tarefas organizadas por colunas.

## Tecnologias

- Python
- Flask
- SQLite
- Flask-SQLAlchemy
- Flask-RESTX
- Flask-CORS

## Instalacao

Crie e ative a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

## Execucao

Inicie a API:

```bash
flask --app app run --port 5001
```

A API ficara disponivel em:

- API: `http://127.0.0.1:5001`
- Swagger: `http://127.0.0.1:5001/swagger`

O banco SQLite sera criado automaticamente em `instance/kanban.db` na primeira execucao.
