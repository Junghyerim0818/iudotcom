from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional

class PostForm(FlaskForm):
    title = StringField('제목', validators=[DataRequired()])
    content = TextAreaField('내용', validators=[DataRequired()])
    # Category selection: Gallery or Archive types
    category = SelectField('카테고리', choices=[
        ('gallery', '갤러리'), 
        ('archive_1', '아이유 인증 글'), 
        ('archive_2', '서포트 인증 글')
    ], validators=[DataRequired()])
    image = FileField('이미지 업로드', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')
    ])
    submit = SubmitField('작성하기')

class AdminUserForm(FlaskForm):
    role = SelectField('권한', choices=[
        ('user', '일반 사용자'),
        ('writer', '글쓰기 권한'),
        ('admin', '관리자')
    ])
    submit = SubmitField('수정')


