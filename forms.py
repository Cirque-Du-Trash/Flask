from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, PasswordField, SelectField
from wtforms.validators import DataRequired, InputRequired
from datetime import datetime

class TestForm(FlaskForm):
    questions = [
        ('새로운 사람과의 만남이 당신에게 즐거움을 주나요?'),
        ('일상에서 스트레스를 자주 느끼며 이를 잘 관리하고 있나요?'),
        ('목표를 설정하고 이를 달성하기 위해 계획을 세우는 편인가요?'),
        ('혼자 있는 시간을 통해 자신을 돌아보는 것을 좋아하나요?'),
        ('가끔 감정적으로 불안정하다고 느끼며, 이를 극복하려고 노력하나요?')
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
    name = StringField('이름', validators=[DataRequired()])
    submit = SubmitField('설문 시작')
    
    def calculate_age_group(self):
        birth_year = int(self.birth_year.data)
        age = self.current_year - birth_year
        if age < 20:
            return '10대'
        elif age < 30:
            return '20대'
        elif age < 40:
            return '30대'
        elif age < 50:
            return '40대'
        elif age < 60:
            return '50대'
        else:
            return '60대 이상'