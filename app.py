from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from models import db, User, Task, UserTask
import random

app = Flask(__name__)

# Configuração do CORS
CORS(app, origins=["http://localhost:4200"])

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
bcrypt = Bcrypt(app)
db.init_app(app)

# Inicializa o banco de dados
with app.app_context():
    db.create_all()
    
    # Adiciona algumas tasks iniciais
    if not Task.query.first():
        tasks_data = [
            {"nome": "Aprender C", "descricao": "Estudo básico de C", "pontuacao": 5},
            {"nome": "Aprender POO", "descricao": "Conceitos de Programação Orientada a Objetos", "pontuacao": 15},
            {"nome": "Estudo de Algoritmos", "descricao": "Análise e implementação de algoritmos", "pontuacao": 10},
            {"nome": "Introdução a Python", "descricao": "Aprender Python básico", "pontuacao": 8},
            {"nome": "Banco de Dados SQL", "descricao": "Fundamentos de bancos de dados SQL", "pontuacao": 12},
        ]
        for task in tasks_data:
            db.session.add(Task(**task))
        db.session.commit()

# Função para selecionar duas tarefas aleatórias
def get_random_tasks():
    return random.sample(Task.query.all(), 2)

# Post de registro
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    nome = data.get('username')
    email = data.get('email')
    senha = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email já cadastrado'}), 409

    hashed_senha = bcrypt.generate_password_hash(senha).decode('utf-8')
    novo_usuario = User(nome=nome, email=email, senha=hashed_senha)

    db.session.add(novo_usuario)
    db.session.commit()
    return jsonify({'message': 'Usuário registrado com sucesso'}), 201

# Post de Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    senha = data.get('password')

    usuario = User.query.filter_by(email=email).first()
    if usuario and bcrypt.check_password_hash(usuario.senha, senha):
        return jsonify({
            'message': 'Login bem-sucedido',
            'user_id': usuario.id,
            'nome': usuario.nome,
            'email': usuario.email,
            'pontos': usuario.pontos,
        }), 200
    else:
        return jsonify({'message': 'Credenciais inválidas'}), 401

# Get de tarefas
@app.route('/random_tasks', methods=['GET'])
def random_tasks():
    tasks = get_random_tasks()
    tasks_data = [{'task_id': task.id, 'nome': task.nome, 'descricao': task.descricao, 'pontuacao': task.pontuacao} for task in tasks]
    return jsonify({'tasks': tasks_data}), 200

# Get do histórico do usuário
@app.route('/task_history/<int:user_id>', methods=['GET'])
def task_history(user_id):
    user_tasks = UserTask.query.filter_by(user_id=user_id).order_by(desc(UserTask.id)).all()
    history = [{'task_id': ut.task_id, 'nome': ut.task.nome, 'descricao': ut.task.descricao, 'status': ut.status, 'pontuacao': ut.task.pontuacao} for ut in user_tasks]
    return jsonify({'history': history}), 200

# Post para marcar tarefa como concluída
@app.route('/complete_task/<int:user_id>/<int:task_id>', methods=['POST'])
def complete_task(user_id, task_id):
    # Verifica se a tarefa está pendente para o usuário
    user_task = UserTask.query.filter_by(user_id=user_id, task_id=task_id, status="pendente").first()
    if not user_task:
        return jsonify({'message': 'Tarefa pendente não encontrada ou já concluída'}), 404
    
    # Atualiza o status da tarefa para "concluída"
    user_task.status = "concluída"
    db.session.commit()

    # Retorna a lista de tarefas após concluir
    tasks = get_random_tasks()
    tasks_data = [{'task_id': task.id, 'nome': task.nome, 'descricao': task.descricao, 'pontuacao': task.pontuacao} for task in tasks]
    return jsonify({'message': 'Tarefa concluída com sucesso!', 'tasks': tasks_data}), 200

# Post para atribuir tarefa a um usuário
@app.route('/assign_task/<int:user_id>/<int:task_id>', methods=['POST'])
def assign_task(user_id, task_id):
    usuario = User.query.get(user_id)
    tarefa = Task.query.get(task_id)
    if not usuario:
        return jsonify({'message': 'Usuário não encontrado'}), 404
    if not tarefa:
        return jsonify({'message': 'Tarefa não encontrada'}), 404

    # Cria um registro de tarefa para o usuário com status "pendente"
    user_task = UserTask(user_id=user_id, task_id=task_id, status="pendente")
    db.session.add(user_task)
    db.session.commit()

    return jsonify({'message': f'Tarefa "{tarefa.nome}" atribuída ao usuário "{usuario.nome}" com sucesso!'}), 201

# Get de tarefas pendentes de um usuário
@app.route('/pending_task/<int:user_id>', methods=['GET'])
def pending_task(user_id):
    user_task = UserTask.query.filter_by(user_id=user_id, status="pendente").first()

    if not user_task:
        return jsonify({'message': 'Nenhuma tarefa pendente encontrada para este usuário'}), 404

    task = user_task.task
    task_data = {
        'task_id': task.id,
        'nome': task.nome,
        'descricao': task.descricao,
        'pontuacao': task.pontuacao
    }

    return jsonify({'task': task_data}), 200

# Get de informações do usuário
@app.route('/user_profile/<int:user_id>', methods=['GET'])
def user_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'Usuário não encontrado'}), 404
    user_data = {
        'id': user.id,
        'nome': user.nome,
        'email': user.email,
        'pontos': sum(ut.task.pontuacao for ut in UserTask.query.filter_by(user_id=user_id).all()),
    }
    return jsonify({'user': user_data}), 200

if __name__ == '__main__':
    app.run(debug=True)
