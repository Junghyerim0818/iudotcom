import os
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from . import db, oauth, login_manager
from .models import User, Post
from .forms import PostForm, AdminUserForm

bp = Blueprint('main', __name__)

# Google OAuth Setup
# 가장 단순하고 확실한 설정 (OpenID 검증 우회)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'email profile'}, # openid 제거
    # 아래 설정을 추가하여 메타데이터 자동 탐색을 원천 차단
    server_metadata_url=None,
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    redirect_uri = url_for('main.authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@bp.route('/login/callback')
def authorize():
    try:
        token = google.authorize_access_token()
        # 직접 API를 호출해서 정보 가져오기 (가장 안전함)
        resp = google.get('https://www.googleapis.com/oauth2/v1/userinfo')
        user_info = resp.json()
        
        # 구글이 주는 id는 'id' 필드에 있음 (openid 미사용 시)
        user_id = user_info.get('id')
        
        if not user_id:
            flash('사용자 정보를 가져올 수 없습니다.', 'danger')
            return redirect(url_for('main.index'))

        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            # Create new user
            user = User(
                id=user_info['sub'],
                email=user_info['email'],
                name=user_info.get('name', 'Unknown'),
                profile_pic=user_info.get('picture', ''),
                role='user' # Default role
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Update info just in case
            user.email = user_info['email']
            user.name = user_info.get('name', user.name)
            user.profile_pic = user_info.get('picture', user.profile_pic)
            db.session.commit()
            
        login_user(user)
        flash('로그인되었습니다.', 'success')
        return redirect(url_for('main.index'))
    except Exception as e:
        flash(f'로그인 실패: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('main.index'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
    form_picture.save(picture_path)
    return picture_fn

@bp.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if not current_user.is_writer():
        flash('글쓰기 권한이 없습니다. 관리자에게 문의하세요.', 'danger')
        return redirect(url_for('main.index'))
        
    form = PostForm()
    if form.validate_on_submit():
        image_file = None
        if form.category.data == 'gallery':
            if form.image.data:
                image_file = save_picture(form.image.data)
            else:
                flash('갤러리에는 이미지가 필수입니다.', 'danger')
                return render_template('create_post.html', title='New Post', form=form)
        elif form.image.data:
             image_file = save_picture(form.image.data)
             
        post = Post(
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            image_filename=image_file,
            author=current_user
        )
        db.session.add(post)
        db.session.commit()
        flash('글이 작성되었습니다!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('create_post.html', title='New Post', form=form)

@bp.route('/gallery')
def gallery():
    posts = Post.query.filter_by(category='gallery').order_by(Post.created_at.desc()).all()
    return render_template('gallery.html', posts=posts)

@bp.route('/archive/<type_name>')
def archive(type_name):
    if type_name not in ['archive_1', 'archive_2']:
        abort(404)
    posts = Post.query.filter_by(category=type_name).order_by(Post.created_at.desc()).all()
    title = '아카이브 1' if type_name == 'archive_1' else '아카이브 2'
    return render_template('archive.html', posts=posts, title=title)

@bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin():
        abort(403)
    
    users = User.query.all()
    return render_template('admin.html', users=users)

@bp.route('/admin/user/<user_id>', methods=['POST'])
@login_required
def update_user_role(user_id):
    if not current_user.is_admin():
        abort(403)
        
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if new_role in ['user', 'writer', 'admin']:
        user.role = new_role
        db.session.commit()
        flash(f'{user.name}님의 권한이 {new_role}로 변경되었습니다.', 'success')
    else:
        flash('잘못된 권한 설정입니다.', 'danger')
        
    return redirect(url_for('main.admin'))

