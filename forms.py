from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, PasswordField, EmailField, SelectField
from wtforms.validators import DataRequired

class TestForm(FlaskForm):
    question1 = RadioField('당신은 새로운 사람을 만나는 것이 즐겁다고 느끼나요?', choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question2 = RadioField('일상에서 스트레스를 자주 느끼나요?', choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question3 = RadioField('당신은 목표를 세우고 그것을 달성하는 데 집중하는 편인가요?', choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question4 = RadioField('혼자 있는 시간을 좋아하나요?', choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    question5 = RadioField('가끔 감정적으로 불안정하다고 느끼나요?', choices=[('yes', '예'), ('no', '아니오')], validators=[DataRequired()])
    submit = SubmitField('제출')

class LoginForm(FlaskForm):
    username = StringField('사용자 이름', validators=[DataRequired()])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    submit = SubmitField('로그인')
    
class SurveyInfoForm(FlaskForm):
    name = StringField('이름', validators=[DataRequired()])
    email = EmailField('메일주소', validators=[DataRequired()])
    age = SelectField('연령대', choices=[('10대', '10대'), ('20대', '20대'), ('30대', '30대'), ('40대', '40대'), ('50대 이상', '50대 이상')])
    submit = SubmitField('정보 제출')