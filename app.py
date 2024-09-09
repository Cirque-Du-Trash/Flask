from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from forms import TestForm, LoginForm, SurveyInfoForm
from models import db, User, TestResponse, Question
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'your_secret_key'

migrate = Migrate(app, db)
db.init_app(app)
login_manager = LoginManager(app)

def create_admin_user():
    if not User.query.filter_by(username='admin').first():  # 중복 방지
        admin_user = User(username='admin')
        admin_user.set_password('admin')  # 비밀번호 해시 설정
        admin_user.is_admin = True
        db.session.add(admin_user)
        db.session.commit()

with app.app_context():
    db.create_all()
    create_admin_user()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def index():
    form = SurveyInfoForm()
    if form.validate_on_submit():
        return redirect(url_for('survey'))
    return render_template('index.html', form=form)

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    form = TestForm()
    if form.validate_on_submit():
        responses = {f'question{i}': form.data[f'question{i}'] for i in range(1, 6)}
        user_id = current_user.id if current_user.is_authenticated else None
        test_response = TestResponse(user_id=user_id, response=json.dumps(responses))  # JSON 형식으로 저장
        db.session.add(test_response)
        db.session.commit()
        return redirect(url_for('result'))
    return render_template('survey.html', form=form)

@app.route('/result')
def result():
    return render_template('result.html')

@app.route('/admin')
@login_required
def admin_view():
    questions = Question.query.all()  # 모든 질문 조회
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

    # 질문별 응답 수 계산
    question_stats = {}
    questions = Question.query.all()
    for question in questions:
        yes_count = TestResponse.query.filter(TestResponse.response.like(f'%"{question.id}": "yes"%')).count()
        no_count = TestResponse.query.filter(TestResponse.response.like(f'%"{question.id}": "no"%')).count()
        question_stats[question.text] = {'yes': yes_count, 'no': no_count}

    # 참가자 정보 수집
    participants = TestResponse.query.all()

    return render_template('stats.html', total_responses=total_responses, question_stats=question_stats, participants=participants)

@app.route('/manage_questions', methods=['POST'])
@login_required
def manage_questions():
    new_question = request.form.get('new_question')
    if new_question:
        # 새로운 질문 추가
        question = Question(text=new_question)
        db.session.add(question)
        db.session.commit()

    return redirect(url_for('admin_view'))

@app.route('/edit_questions', methods=['POST'])
@login_required
def edit_questions():
    edit_question = request.form.get('edit_question')
    question_id = request.form.get('question_id')  # 수정할 질문의 ID

    if edit_question and question_id:
        # 질문 수정
        question = Question.query.get(question_id)
        if question:
            question.text = edit_question
            db.session.commit()

    return redirect(url_for('admin_view'))

admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(TestResponse, db.session))

if __name__ == '__main__':
    app.run(debug=True)
