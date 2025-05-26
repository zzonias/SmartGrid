from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func 
from werkzeug.security import generate_password_hash, check_password_hash
import random
import datetime
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = 'segredo-super-seguro'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Equipamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    localizacao = db.Column(db.String(100))
    medicoes = db.relationship('Medicao', backref='equipamento', lazy=True, cascade="all, delete-orphan")

class Medicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=datetime.date.today)
    valor = db.Column(db.Float, nullable=False)
    equipamento_id = db.Column(db.Integer, db.ForeignKey('equipamento.id'), nullable=False)

with app.app_context():
    db.create_all()

@app.template_filter('today_date_str')
def today_date_string(value):
    return datetime.date.today().strftime('%Y-%m-%d')

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Usuário ou senha inválidos.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Usuário já existe.')
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Definir os últimos 7 dias (incluindo hoje)
    dias = []
    datas_calculo = []
    for i in range(6, -1, -1): # Começa 6 dias atrás até hoje
        data_atual = datetime.date.today() - datetime.timedelta(days=i)
        dias.append(data_atual.strftime('%d/%m')) # Formato (DD/MM) para exibição no gráfico
        datas_calculo.append(data_atual)

    consumo_total_diario = []

    for data_referencia in datas_calculo:
        # Calcular o consumo total para cada dia, filtra as medições para o dia específico e soma os valores, ou 0.0 se não houver medições
        total_do_dia = db.session.query(func.sum(Medicao.valor)).filter(
            func.date(Medicao.data) == data_referencia # Garante que estamos comparando apenas a data
        ).scalar() 

        consumo_total_diario.append(round(total_do_dia if total_do_dia is not None else 0.0, 2))

    return render_template('dashboard.html', dias=dias, consumo_total=consumo_total_diario)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/equipamentos')
def listar_equipamentos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    equipamentos = Equipamento.query.all()
    return render_template('equipamentos/listar.html', equipamentos=equipamentos)

@app.route('/equipamentos/novo', methods=['GET', 'POST'])
def novo_equipamento():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form['nome']
        localizacao = request.form['localizacao']
        novo_equipamento = Equipamento(nome=nome, localizacao=localizacao)
        db.session.add(novo_equipamento)
        db.session.commit()
        return redirect(url_for('listar_equipamentos'))
    return render_template('equipamentos/novo.html')

@app.route('/equipamentos/editar/<int:id>', methods=['GET', 'POST'])
def editar_equipamento(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    equipamento = Equipamento.query.get_or_404(id)
    if request.method == 'POST':
        equipamento.nome = request.form['nome']
        equipamento.localizacao = request.form['localizacao']
        db.session.commit()
        return redirect(url_for('listar_equipamentos'))
    return render_template('equipamentos/editar.html', equipamento=equipamento)

@app.route('/equipamentos/deletar/<int:id>', methods=['POST'])
def deletar_equipamento(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    equipamento = Equipamento.query.get_or_404(id)
    db.session.delete(equipamento)
    db.session.commit()
    return redirect(url_for('listar_equipamentos'))

@app.route('/equipamentos/<int:equipamento_id>/medicoes')
def listar_medicoes(equipamento_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    equipamento = Equipamento.query.get_or_404(equipamento_id)
    medicoes = Medicao.query.filter_by(equipamento_id=equipamento_id).order_by(Medicao.data.desc()).all()
    return render_template('medicoes/listar.html', equipamento=equipamento, medicoes=medicoes)

@app.route('/equipamentos/<int:equipamento_id>/medicoes/nova', methods=['GET', 'POST'])
def nova_medicao(equipamento_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    equipamento = Equipamento.query.get_or_404(equipamento_id)
    if request.method == 'POST':
        data_str = request.form['data']
        data = datetime.datetime.strptime(data_str, '%Y-%m-%d').date()
        valor = float(request.form['valor'])
        nova_medicao = Medicao(data=data, valor=valor, equipamento_id=equipamento.id)
        db.session.add(nova_medicao)
        db.session.commit()
        return redirect(url_for('listar_medicoes', equipamento_id=equipamento.id))
    return render_template('medicoes/nova.html', equipamento=equipamento)

@app.route('/equipamentos/<int:equipamento_id>/medicoes/editar/<int:medicao_id>', methods=['GET', 'POST'])
def editar_medicao(equipamento_id, medicao_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    medicao = Medicao.query.get_or_404(medicao_id)
    if request.method == 'POST':
        data_str = request.form['data']
        medicao.data = datetime.datetime.strptime(data_str, '%Y-%m-%d').date()
        medicao.valor = float(request.form['valor'])
        db.session.commit()
        return redirect(url_for('listar_medicoes', equipamento_id=equipamento_id))
    return render_template('medicoes/editar.html', medicao=medicao, equipamento_id=equipamento_id)

@app.route('/equipamentos/<int:equipamento_id>/medicoes/deletar/<int:medicao_id>', methods=['POST'])
def deletar_medicao(equipamento_id, medicao_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    medicao = Medicao.query.get_or_404(medicao_id)
    db.session.delete(medicao)
    db.session.commit()
    return redirect(url_for('listar_medicoes', equipamento_id=equipamento_id))

@app.route('/medicoes/todas')
def todas_medicoes():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = Medicao.query

    # Variáveis para armazenar os parâmetros de filtro
    selected_equipamento_id = request.args.get('equipamento_id', '0')
    selected_data_inicial = request.args.get('data_inicial')
    selected_data_final = request.args.get('data_final')

    # Filtra por equipamento
    if selected_equipamento_id != '0':
        query = query.filter_by(equipamento_id=selected_equipamento_id)

    # Filtra por data inicial
    if selected_data_inicial:
        try:
            data_inicial = datetime.datetime.strptime(selected_data_inicial, '%Y-%m-%d').date()
            query = query.filter(Medicao.data >= data_inicial)
        except ValueError:
            pass # Ignora se a data for inválida

    # Filtra por data final
    if selected_data_final:
        try:
            data_final = datetime.datetime.strptime(selected_data_final, '%Y-%m-%d').date()
            query = query.filter(Medicao.data <= data_final)
        except ValueError:
            pass # Ignora se a data for inválida

    medicoes = query.order_by(Medicao.data.desc()).all()
    soma_total_medicoes = sum(medicao.valor for medicao in medicoes)

    # Carrega todos os equipamentos para o dropdown de filtro
    equipamentos = Equipamento.query.all()

    return render_template(
        'medicoes/todas.html',
        medicoes=medicoes,
        equipamentos=equipamentos,
        selected_equipamento_id=selected_equipamento_id,
        selected_data_inicial=selected_data_inicial,
        selected_data_final=selected_data_final,
        soma_total_medicoes=soma_total_medicoes
    )


@app.route('/medicoes/adicionar', methods=['GET', 'POST'])
def adicionar_medicao():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    equipamentos = Equipamento.query.all()

    if request.method == 'POST':
        equipamento_id = int(request.form['equipamento_id'])
        data_str = request.form['data']
        data = datetime.datetime.strptime(data_str, '%Y-%m-%d').date()
        valor = float(request.form['valor'])

        nova_medicao = Medicao(data=data, valor=valor, equipamento_id=equipamento_id)
        db.session.add(nova_medicao)
        db.session.commit()

        return redirect(url_for('listar_medicoes', equipamento_id=equipamento_id))

    return render_template('medicoes/adicionar.html', equipamentos=equipamentos)

if __name__ == '__main__':
    app.run(debug=True)