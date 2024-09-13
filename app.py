from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from forms import SurveyInfoForm, LoginForm, TestForm
from models import db, User, TestResponse, Question
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'your_secret_key'

migrate = Migrate(app, db)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # 로그인 페이지의 엔드포인트 설정

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin  # 로그인 여부 및 관리자 여부 확인

admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(TestResponse, db.session))

def create_admin_user():
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin')
        admin_user.set_password('admin')  # 비밀번호 설정
        admin_user.is_admin = True
        db.session.add(admin_user)
        db.session.commit()

with app.app_context():
    db.create_all()  # 테이블 생성
    create_admin_user()  # 기본 어드민 계정 생성

@app.route('/', methods=['GET', 'POST'])
def index():
    form = SurveyInfoForm()
    if form.validate_on_submit():
        return redirect(url_for('survey'))
    return render_template('index.html', form=form)

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    questions = Question.query.all()
    if request.method == 'POST':
        responses = {}
        for i, question in enumerate(questions):
            response_key = f'question{i + 1}'
            responses[response_key] = request.form.get(response_key)

        user_id = current_user.id if current_user.is_authenticated else None
        test_response = TestResponse(user_id=user_id, response=json.dumps(responses))
        db.session.add(test_response)
        db.session.commit()
        return redirect(url_for('result'))
    
    return render_template('survey.html', questions=questions)

@app.route('/result')
def result():
    return render_template('result.html')

@app.route('/admin')
@login_required
def admin_view():
    questions = Question.query.all()
    return render_template('admin.html', questions=questions)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user)
            return redirect(url_for('admin_view'))
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/stats')
@login_required
def stats():
    total_responses = TestResponse.query.count()
    question_stats = {question.text: {
        'yes': TestResponse.query.filter(TestResponse.response.like(f'%"{question.id}": "yes"%')).count(),
        'no': TestResponse.query.filter(TestResponse.response.like(f'%"{question.id}": "no"%')).count()
    } for question in Question.query.all()}

    participants = TestResponse.query.all()
    return render_template('stats.html', total_responses=total_responses, question_stats=question_stats, participants=participants)

@app.route('/manage_questions', methods=['POST'])
@login_required
def manage_questions():
    new_question = request.form.get('new_question')
    if new_question:
        question = Question(text=new_question)
        db.session.add(question)
        db.session.commit()
    return redirect(url_for('admin_view'))

@app.route('/edit_questions', methods=['POST'])
@login_required
def edit_questions():
    edit_question_text = request.form.get('edit_question_text')
    question_id = request.form.get('question_id')
    if edit_question_text and question_id:
        question = Question.query.get(question_id)
        if question:
            question.text = edit_question_text
            db.session.commit()
    return redirect(url_for('admin_view'))

if __name__ == '__main__':
    app.run(debug=True)