from flask import Flask, render_template, redirect, url_for, request, Response, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from forms import SurveyInfoForm, LoginForm, TestForm
from models import db, User, TestResponse, Question
from datetime import timedelta
import pandas as pd
import plotly.express as px
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)  # 10분 후 만료
app.config['SESSION_PERMANENT'] = False  # 세션을 영구적으로 유지하지 않음

# 데이터베이스 및 마이그레이션 초기화
migrate = Migrate(app, db)
db.init_app(app)

# 로그인 관리 초기화
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # 로그인 페이지의 엔드포인트 설정
login_manager.session_protection = 'strong'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# 어드민 패널 설정
class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(TestResponse, db.session))

# 기본 어드민 계정 생성
def create_admin_user():
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin')
        admin_user.set_password('admin')  # 비밀번호 설정
        admin_user.is_admin = True
        db.session.add(admin_user)
        db.session.commit()

# 초기 질문 생성
def create_initial_questions():
    if not Question.query.first():
        for index, question_text in enumerate(TestForm.questions):
            question = Question(text=question_text, order=index + 1)  # 순서 지정
            db.session.add(question)
        db.session.commit()

# 애플리케이션 시작 시 데이터베이스 및 초기 설정
with app.app_context():
    db.create_all()  # 테이블 생성
    create_initial_questions()  # 초기 질문 생성
    create_admin_user()  # 기본 어드민 계정 생성

# 기본 페이지
@app.route('/', methods=['GET', 'POST'])
def index():
    form = SurveyInfoForm()
    if form.validate_on_submit():
        if not form.name.data:
            flash('이름을 입력해 주세요.', 'error')
            return render_template('index.html', form=form)
        
        age_group = form.calculate_age_group()
        
        session['name'] = form.name.data
        session['age_group'] = age_group
        session['gender'] = form.gender.data
        
        print("Name:", form.name.data)
        print("Age Group:", age_group)
        print("Gender:", form.gender.data)
        
        user_id = current_user.id if current_user.is_authenticated else None
        
        test_response = TestResponse(
            user_id=user_id,
            response=json.dumps({}),
            name=form.name.data,
            age_group=age_group,
            gender=form.gender.data
        )
        
        print("Attempting to save:", test_response.name, test_response.age_group)
        
        db.session.add(test_response)
        db.session.commit()
        
        print("Saved Response:", test_response)
        
        return redirect(url_for('survey'))
    return render_template('index.html', form=form)

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    questions = Question.query.order_by(Question.order).all()  # 질문 순서 정렬
    if request.method == 'POST':
        responses = {}
        for i, question in enumerate(questions):
            response_key = f'question{i + 1}'
            responses[response_key] = request.form.get(response_key)

        user_id = current_user.id if current_user.is_authenticated else None

        # 여기에서 TestResponse 객체를 생성할 때 name과 age_group을 포함해야 합니다.
        test_response = TestResponse(
            user_id=user_id,
            response=json.dumps(responses),
            name=session.get('name'),  # 이름 필드 추가
            age_group=session.get('age_group'),  # 연령대 필드 추가
            gender=session.get('gender')
        )

        db.session.add(test_response)
        db.session.commit()
        return redirect(url_for('result'))

    return render_template('survey.html', questions=questions)

# 결과 페이지
@app.route('/result')
def result():
    return render_template('result.html')

# 어드민 페이지
@app.route('/admin')
@login_required
def admin_view():
    questions = Question.query.order_by(Question.order).all()  # 순서 기준으로 정렬
    return render_template('admin.html', questions=questions)

# 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user)
            return redirect(url_for('admin_view'))
    return render_template('login.html', form=form)

# 로그아웃
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# 통계 페이지
@app.route('/stats')
@login_required
def stats():
    total_responses = TestResponse.query.count()
    participants = TestResponse.query.all()
    
    print("Total Responses:", total_responses)
    print("Participants:", [(p.name, p.age_group, p.gender) for p in participants])
    
    # 질문 통계 계산
    questions = Question.query.all()
    question_stats = []
    gender_stats = {'남': 0 , '여': 0}
    
    for participant in participants:
        gender_stats[participant.gender] += 1
        
    for question in questions:
        yes_count = sum(1 for response in participants if response.responses.get(f'question{question.id}') == 'yes')
        no_count = sum(1 for response in participants if response.responses.get(f'question{question.id}') == 'no')
        question_stats.append({
            'question': question.text,
            'yes': yes_count,
            'no': no_count
        })

    # 데이터프레임 생성
    df = pd.DataFrame(question_stats)

    # Plotly를 이용한 그래프 생성
    fig = px.bar(df, x='question', y=['yes', 'no'], title='질문별 응답 통계', barmode='group')
    graph_html = fig.to_html(full_html=False)

    return render_template('stats.html', total_responses=total_responses, graph_html=graph_html, participants=participants)


# 질문 관리
@app.route('/edit_questions', methods=['POST'])
@login_required
def edit_questions():
    question_ids = request.form.getlist('question_id[]')  # 여러 개의 질문 ID를 받음
    edit_question_texts = request.form.getlist('edit_question_text[]')  # 여러 개의 질문 텍스트를 받음

    # 디버깅을 위한 프린트
    print("Received question IDs:", question_ids)
    print("Received edited question texts:", edit_question_texts)

    for question_id, edit_question_text in zip(question_ids, edit_question_texts):
        question = Question.query.get(question_id)
        if question:
            print(f"Updating question ID {question_id} to text: {edit_question_text}")  # 어떤 질문이 수정되는지 출력
            question.text = edit_question_text  # 질문 텍스트 수정

    db.session.commit()
    print("Database commit successful.")  # 데이터베이스 커밋 성공 메시지

    return redirect(url_for('admin_view'))

# 질문 삭제
@app.route('/delete_question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    question = Question.query.get(question_id)
    if question:
        db.session.delete(question)
        db.session.commit()
    return redirect(url_for('admin_view'))

# 질문 추가
@app.route('/manage_questions', methods=['POST'])
@login_required
def manage_questions():
    action = request.form.get('action')

    if action == 'add':
        new_question = request.form.get('new_question')
        if new_question:
            question = Question(text=new_question)
            db.session.add(question)
            db.session.commit()

    elif action == 'edit':
        question_ids = request.form.getlist('question_id[]')
        question_texts = request.form.getlist('question_text[]')
        orders = request.form.getlist('order[]')

        for q_id, q_text, order in zip(question_ids, question_texts, orders):
            question = Question.query.get(q_id)
            if question:
                question.text = q_text
                question.order = int(order)
        
        db.session.commit()

    elif action == 'delete':
        question_id = request.form.get('question_id')
        question = Question.query.get(question_id)
        if question:
            db.session.delete(question)
            db.session.commit()
            
    elif action == 'reorder':
        question_ids = request.form.getlist('question_id[]')
        orders = request.form.getlist('order[]')

        for index, question_id in enumerate(question_ids):
            question = Question.query.get(question_id)
            if question:
                question.order = int(orders[index])  # 새로운 순서 저장

        db.session.commit()

    return redirect(url_for('admin_view'))

# 애플리케이션 실행
if __name__ == '__main__':
    app.run(debug=True)
