from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, PasswordField, SelectField
from wtforms.validators import DataRequired, InputRequired
from datetime import datetime

class TestForm(FlaskForm):
    questions = [
        ('당신은 새로운 사람을 만나는 것이 즐겁다고 느끼나요?'),
        ('일상에서 스트레스를 자주 느끼나요?'),
        ('당신은 목표를 세우고 그것을 달성하는 데 집중하는 편인가요?'),
        ('혼자 있는 시간을 좋아하나요?'),
        ('가끔 감정적으로 불안정하다고 느끼나요?')
    ]
    question1 = RadioField(questions[0], choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question2 = RadioField(questions[1], choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question3 = RadioField(questions[2], choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question4 = RadioField(questions[3], choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question5 = RadioField(questions[4], choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    submit = SubmitField('제출')

class LoginForm(FlaskForm):
    username = StringField('사용자 이름', validators=[DataRequired()])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    submit = SubmitField('로그인')
    
class SurveyInfoForm(FlaskForm):
    current_year = datetime.now().year
    birth_year_choices = [(str(year), str(year)) for year in range(current_year, current_year - 101, -1)]
    birth_year = SelectField('출생년도', choices=birth_year_choices, validators=[InputRequired()])
    gender = SelectField('성별', choices=[('남', '남성'), ('여', '여성')])
    submit = SubmitField('설문 시작')
    name = StringField('이름', validators=[DataRequired()])