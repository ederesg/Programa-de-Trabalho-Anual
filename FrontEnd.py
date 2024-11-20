from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from functools import wraps
import os
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua_chave_secreta_aqui')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['GITHUB_TOKEN'] = os.environ.get('GITHUB_TOKEN')
app.config['GITHUB_REPO'] = os.environ.get('GITHUB_REPO')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

# ... (classes Usuario e Necessidade permanecem as mesmas)

# ... (decoradores login_required e admin_required permanecem os mesmos)

# ... (rotas de registro, login e logout permanecem as mesmas)

@app.route('/necessidade', methods=['POST'])
@login_required
def criar_necessidade():
    dados = request.json
    nova_necessidade = Necessidade(descricao=dados['descricao'], usuario_id=session['usuario_id'])
    db.session.add(nova_necessidade)
    db.session.commit()
    
    # Criar uma issue no GitHub
    criar_issue_github(nova_necessidade)
    
    return jsonify({'mensagem': 'Necessidade criada com sucesso'}), 201

@app.route('/admin/necessidade/<int:id>', methods=['PUT'])
@admin_required
def atualizar_status(id):
    necessidade = Necessidade.query.get_or_404(id)
    dados = request.json
    necessidade.status = dados['status']
    db.session.commit()
    
    # Atualizar a issue no GitHub
    atualizar_issue_github(necessidade)
    
    usuario = Usuario.query.get(necessidade.usuario_id)
    enviar_email_notificacao(usuario.email, necessidade.status)
    
    return jsonify({'mensagem': 'Status atualizado com sucesso'}), 200

def criar_issue_github(necessidade):
    url = f"https://api.github.com/repos/{app.config['GITHUB_REPO']}/issues"
    headers = {
        "Authorization": f"token {app.config['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": f"Necessidade: {necessidade.descricao[:50]}...",
        "body": necessidade.descricao,
        "labels": ["necessidade"]
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        issue_number = response.json()["number"]
        necessidade.github_issue_number = issue_number
        db.session.commit()

def atualizar_issue_github(necessidade):
    url = f"https://api.github.com/repos/{app.config['GITHUB_REPO']}/issues/{necessidade.github_issue_number}"
    headers = {
        "Authorization": f"token {app.config['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "state": "closed" if necessidade.status == "Concluído" else "open",
        "labels": [necessidade.status]
    }
    requests.patch(url, json=data, headers=headers)

def enviar_email_notificacao(email, status):
    msg = Message('Atualização de Status', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'O status da sua necessidade foi atualizado para: {status}'
    mail.send(msg)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
