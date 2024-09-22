from flask import Flask, render_template, redirect, url_for, request, Response, flash, session
# from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from forms import SurveyInfoForm, LoginForm, TestForm
from supabase import create_client, Client
from models import db, User, TestResponse, Question
from datetime import timedelta, datetime
import pandas as pd
import plotly.express as px
import json
import pytz

app = Flask(__name__)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

url = "https://luxbzbnlwsjnuarhxzry.supabase.co" # Supabase 프로젝트 URL
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx1eGJ6Ym5sd3NqbnVhcmh4enJ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjY5ODQ4MTQsImV4cCI6MjA0MjU2MDgxNH0.frfMFpfq7BIBQIK8-d7DiJSygun-4WFfr1RFifY8ts8"
supabase: Client = create_client(url, key)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)  # 10분 후 만료
app.config['SESSION_PERMANENT'] = False  # 세션을 영구적으로 유지하지 않음

# 데이터베이스 및 마이그레이션 초기화
# migrate = Migrate(app, db)
# db.init_app(app)

# 로그인 관리 초기화
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # 로그인 페이지의 엔드포인트 설정
login_manager.session_protection = 'strong'

def is_response_duplicate(name, age_group, gender):
    response = supabase.table('test_responses').select('id').eq('name', name).eq('age_group', age_group).eq('gender', gender).execute()
    return len(response.data) > 0

@app.context_processor
def utility_processor():
    return dict(json=json)

@login_manager.user_loader
def load_user(user_id):
    user_data = supabase.table('users').select('*').eq('id', user_id).execute()
    if user_data.data:
        user_info = user_data.data[0]
        user = User(id=user_info['id'], username=user_info['username'], is_admin=user_info['is_admin'])
        return user
    return None

# 어드민 패널 설정
class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')
admin.add_view(MyModelView(User, supabase))
admin.add_view(MyModelView(TestResponse, supabase))
admin.add_view(MyModelView(Question, supabase))

# 기본 어드민 계정 생성
def create_admin_user():
    existing_user = supabase.table('users').select('*').eq('username', 'admin').execute()
    
    if not existing_user.data:
        admin_user = {
            'username': 'admin',
            'password_hash': 'admin',  
            'is_admin': True
        }
        supabase.table('users').insert(admin_user).execute()
    else:
        print("Admin user already exists.")

# 초기 질문 생성
def create_initial_questions():
    if not supabase.table('questions').select('*').execute().data:
        for index, question_text in enumerate(TestForm.questions):
            question = {
                'text': question_text,
                'order': index + 1
            }
            supabase.table('questions').insert(question).execute()

# 애플리케이션 시작 시 데이터베이스 및 초기 설정
with app.app_context():
    create_initial_questions()  # 초기 질문 생성
    create_admin_user()  # 기본 어드민 계정 생성

# 인덱스 페이지
@app.route('/')
def index():
    return render_template('index.html')

# 참가자 정보입력 페이지
@app.route('/info', methods=['GET', 'POST'])
def info():
    form = SurveyInfoForm()
    if form.validate_on_submit():
        if not form.name.data:
            flash('이름을 입력해 주세요.', 'error')
            return render_template('info.html', form=form)
        
        age_group = form.calculate_age_group()
        
        # 중복 체크
        if is_response_duplicate(form.name.data, age_group, form.gender.data):
            flash('이미 응답이 기록되어 있습니다.', 'error')
            return render_template('info.html', form=form)

        session['name'] = form.name.data
        session['age_group'] = age_group
        session['gender'] = form.gender.data
        session['step'] = 'survey'
            
        user_id = current_user.id if current_user.is_authenticated else None
        
        return redirect(url_for('survey'))
    return render_template('info.html', form=form)

# 설문 페이지
@app.route('/survey', methods=['GET', 'POST'])
def survey():
    if session.get('step') != 'survey':
        return redirect(url_for('index'))

    questions = supabase.table('questions').select('*').order('order').execute().data

    # 세션 초기화 (GET 요청 시)
    if request.method == 'GET':
        session['responses'] = {}
        print("Current session responses at start:", session['responses'])

    if request.method == 'POST':
        # 응답 저장
        for key, value in request.form.items():
            if key.startswith('question'):
                session['responses'][key] = value

        print("Updated session responses:", session['responses'])

        # 모든 질문에 응답했는지 확인
        if len(session['responses']) == len(questions):
            user_id = current_user.id if current_user.is_authenticated else None
            
            if is_response_duplicate(session.get('name'), session.get('age_group'), session.get('gender')):
                flash('이미 응답이 기록되어 있습니다.', 'error')
                return redirect(url_for('result'))

            # 점수 계산
            score = sum(1 for response in session['responses'].values() if response == 'yes')

            # 결과 메시지 생성
            if score >= 10:
                result_message = (
                    "축하합니다! 당신은 감정적으로 매우 안정된 사람입니다. "
                    "주변 사람들과의 관계를 잘 유지하며, 스트레스를 효과적으로 관리할 수 있는 능력이 뛰어납니다. "
                    "또한, 긍정적인 사고방식을 가지고 있어 어려움 속에서도 희망을 잃지 않습니다."
                )
            elif score >= 8:
                result_message = (
                    "당신은 감정적으로 안정된 편입니다. "
                    "일상에서의 스트레스를 잘 관리하고 있으며, 주변 사람들과도 좋은 관계를 유지합니다. "
                    "자신의 감정을 잘 이해하고, 필요한 경우 도움을 요청하는 것을 두려워하지 않는 모습이 인상적입니다."
                )
            elif score >= 6:
                result_message = (
                    "당신은 감정적으로 약간의 불안정을 느낄 수 있지만, 이를 극복하려는 노력이 돋보입니다. "
                    "일상에서의 스트레스가 때때로 당신의 감정에 영향을 미칠 수 있습니다. "
                    "더욱 안정된 감정을 위해 스스로를 돌아보며 감정을 관리해보세요."
                )
            elif score >= 4:
                result_message = (
                    "당신은 감정적으로 불안정할 수 있습니다. "
                    "주변의 스트레스나 감정적인 어려움이 당신에게 큰 영향을 미치고 있는 것 같습니다. "
                    "이럴 때일수록 주변 사람들과의 소통이 중요하며, 전문적인 도움을 받는 것도 고려해보세요."
                )
            else:
                result_message = (
                    "현재 당신은 감정적으로 매우 불안정한 상태일 수 있습니다. "
                    "일상적인 스트레스가 당신의 감정에 큰 영향을 미치고 있으며, 이럴 때일수록 스스로를 잘 돌보는 것이 필요합니다. "
                    "전문가와의 상담을 통해 감정을 이해하고 관리하는 방법을 찾는 것이 좋겠습니다."
                )

            # 응답 데이터 저장
            test_response = {
                'user_id': user_id,
                'response': json.dumps(session['responses']),
                'name': session.get('name'),
                'age_group': session.get('age_group'),
                'gender': session.get('gender'),
                'result_message': result_message  # 결과 메시지 추가
            }

            supabase.table('test_responses').insert(test_response).execute()
            
            # 세션에 결과 메시지 저장
            session['result_message'] = result_message

            session['step'] = 'result'
            return redirect(url_for('result'))

    return render_template('survey.html', questions=questions)

# 결과 페이지
@app.route('/result', methods=['GET'])
def result():
    if session.get('step') != 'result':
        return redirect(url_for('index'))

    responses = session.get('responses')
    
    if responses is None:
        return render_template('result.html', result="응답이 없습니다.")

    # 세션에서 결과 메시지 가져오기
    result_message = session.get('result_message', "결과를 가져오는 데 실패했습니다.")

    return render_template('result.html', result=result_message)

# 어드민 페이지
@app.route('/admin')
@login_required
def admin_view():
    questions = supabase.table('questions').select('*').order('order').execute().data
    return render_template('admin.html', questions=questions)

# 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_data = supabase.table('users').select('*').eq('username', form.username.data).execute()
        if user_data.data:
            user_info = user_data.data[0]
            if user_info['password_hash'] == 'admin':  # 비밀번호 검증 로직 추가 필요
                login_user(User(id=user_info['id'], username=user_info['username'], is_admin=user_info['is_admin']))
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
    # test_responses 테이블에서 모든 응답을 가져오기
    response = supabase.table('test_responses').select('*').execute()
    
    # 쿼리 결과 출력
    print("Response data:", response.data)

    if response.data is None:
        flash('데이터를 가져오는 데 실패했습니다.', 'error')
        return redirect(url_for('index'))

    total_responses = len(response.data)  # 데이터 개수
    participants = response.data

    # 응답 데이터의 시간 변환
    for participant in participants:
        if 'response_date' in participant:
            # response_date의 타입 확인
            response_date = participant['response_date']
            if isinstance(response_date, str):
                # 문자열인 경우 datetime 객체로 변환
                utc_time = datetime.fromisoformat(response_date)
                # UTC 시간을 Asia/Seoul로 변환
                local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Seoul'))
                participant['response_date'] = local_time  # 변환된 시간을 저장
            else:
                print(f"Unexpected type for response_date: {type(response_date)}")  # 타입 확인용


    # 결과 메시지를 수집
    results = [p['result_message'] for p in participants if 'result_message' in p]

    # 질문 통계 계산
    questions = supabase.table('questions').select('*').execute().data
    question_stats = []
    gender_stats = {'남': 0, '여': 0}

    for participant in participants:
        gender_stats[participant['gender']] += 1
        participant['response_date'] = datetime.fromisoformat(participant['response_date'])

    for question in questions:
        yes_count = sum(1 for response in participants if json.loads(response['response']).get(f'question{question["id"]}') == 'yes')
        no_count = sum(1 for response in participants if json.loads(response['response']).get(f'question{question["id"]}') == 'no')
        question_stats.append({
            'question': question['text'],
            'yes': yes_count,
            'no': no_count
        })

    # 데이터프레임 생성
    df = pd.DataFrame(question_stats)

    # Plotly를 이용한 그래프 생성
    fig = px.bar(df, x='question', y=['yes', 'no'], title='질문별 응답 통계', barmode='group')

    # 배경 색상 및 기타 레이아웃 설정
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',  # 투명 배경
        paper_bgcolor='rgba(0,0,0,0)',  # 투명 배경
        font=dict(color='white'),  # 흰색 폰트
        xaxis=dict(gridcolor='#444444'),  # 어두운 그리드 색상
        yaxis=dict(gridcolor='#444444')
    )

    # 그래프 HTML 생성
    graph_html = fig.to_html(full_html=False)

    # results 변수를 템플릿에 전달
    return render_template('stats.html', total_responses=total_responses, graph_html=graph_html, participants=participants, results=results)

# 질문 관리
@app.route('/edit_questions', methods=['POST'])
@login_required
def edit_questions():
    question_ids = request.form.getlist('question_id[]')  # 여러 개의 질문 ID를 받음
    edit_question_texts = request.form.getlist('edit_question_text[]')  # 여러 개의 질문 텍스트를 받음

    for question_id, edit_question_text in zip(question_ids, edit_question_texts):
        supabase.table('questions').update({'text': edit_question_text}).eq('id', question_id).execute()

    print("Database commit successful.")  # 데이터베이스 커밋 성공 메시지

    return redirect(url_for('admin_view'))

# 질문 삭제
@app.route('/delete_question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    supabase.table('questions').delete().eq('id', question_id).execute()
    return redirect(url_for('admin_view'))

# 질문 추가
@app.route('/manage_questions', methods=['POST'])
@login_required
def manage_questions():
    action = request.form.get('action')

    if action == 'add':
        new_question = request.form.get('new_question')
        if new_question:
            question = {
                'text': new_question,
                'order': 0  # 기본 순서 설정
            }
            supabase.table('questions').insert(question).execute()

    elif action == 'edit':
        question_ids = request.form.getlist('question_id[]')
        question_texts = request.form.getlist('question_text[]')
        orders = request.form.getlist('order[]')

        for q_id, q_text, order in zip(question_ids, question_texts, orders):
            supabase.table('questions').update({'text': q_text, 'order': int(order)}).eq('id', q_id).execute()

    elif action == 'delete':
        question_id = request.form.get('question_id')
        supabase.table('questions').delete().eq('id', question_id).execute()

    elif action == 'reorder':
        question_ids = request.form.getlist('question_id[]')
        orders = request.form.getlist('order[]')

        for index, question_id in enumerate(question_ids):
            supabase.table('questions').update({'order': int(orders[index])}).eq('id', question_id).execute()

    return redirect(url_for('admin_view'))

# 애플리케이션 실행
# if __name__ == '__main__':
#    app.run(host='0.0.0.0', port=5000, debug=True)