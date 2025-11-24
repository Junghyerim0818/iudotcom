import os
import secrets
import base64
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, Response
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from . import db, oauth, login_manager
from .models import User, Post
from .forms import PostForm, AdminUserForm

bp = Blueprint('main', __name__)

# Static 파일 직접 서빙 (Vercel 환경 대응)
@bp.route('/static/<path:filename>')
def serve_static(filename):
    """Static 파일을 직접 서빙 (루트의 static 폴더)"""
    from flask import send_from_directory
    # app 폴더의 부모 디렉토리(프로젝트 루트)의 static 폴더
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, 'static')
    return send_from_directory(static_dir, filename)

# Google OAuth Setup
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@bp.route('/')
def index():
    try:
        # 최근 갤러리 글들 가져오기
        gallery_posts = Post.query.filter_by(category='gallery').order_by(Post.created_at.desc()).all()
        latest_post = gallery_posts[0] if gallery_posts else None
        other_posts = gallery_posts[1:] if len(gallery_posts) > 1 else []
        return render_template('index.html', latest_post=latest_post, other_posts=other_posts)
    except Exception as e:
        current_app.logger.error(f"Error in index route: {str(e)}")
        # DB 스키마가 업데이트되지 않은 경우를 대비해 빈 결과 반환
        return render_template('index.html', latest_post=None, other_posts=[])

@bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    redirect_uri = url_for('main.authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@bp.route('/login/callback')
def authorize():
    try:
        # authorize_access_token 내부에서 JWKS 검증을 시도할 수 있으므로
        # fetch_token을 직접 호출하거나 검증 옵션을 끕니다.
        token = google.authorize_access_token()
        
        # 사용자 정보 가져오기
        resp = google.get('https://www.googleapis.com/oauth2/v2/userinfo')
        user_info = resp.json()
        
        user_id = user_info.get('id')
        
        if not user_id:
            flash('사용자 정보를 가져올 수 없습니다.', 'danger')
            return render_template('login_callback.html', success=False, message='사용자 정보를 가져올 수 없습니다.')
        
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            # Create new user
            user = User(
                id=user_id,
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
        return render_template('login_callback.html', success=True, message='로그인되었습니다.')
    except Exception as e:
        flash(f'로그인 실패: {str(e)}', 'danger')
        return render_template('login_callback.html', success=False, message=f'로그인 실패: {str(e)}')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/image/<int:post_id>')
def get_image(post_id):
    """DB에 저장된 이미지를 반환하는 라우트"""
    try:
        post = Post.query.get_or_404(post_id)
        if post.image_data:
            # Postgres의 경우 bytes 객체로 반환되어야 함
            image_bytes = bytes(post.image_data) if not isinstance(post.image_data, bytes) else post.image_data
            return Response(image_bytes, mimetype=post.image_mimetype or 'image/jpeg')
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error serving image for post {post_id}: {str(e)}")
        abort(404)

def save_picture(form_picture):
    """이미지를 DB에 저장하고 (image_data, image_mimetype) 튜플 반환"""
    # 파일 데이터 읽기
    image_data = form_picture.read()
    
    # MIME 타입 결정
    mimetype = form_picture.content_type or 'image/jpeg'
    if not mimetype or not mimetype.startswith('image/'):
        mimetype = 'image/jpeg'
    
    return (image_data, mimetype)

@bp.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if not current_user.is_writer():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {'success': False, 'message': '글쓰기 권한이 없습니다. 관리자에게 문의하세요.'}, 403
        flash('글쓰기 권한이 없습니다. 관리자에게 문의하세요.', 'danger')
        return redirect(url_for('main.index'))
        
    form = PostForm()
    if form.validate_on_submit():
        image_data = None
        image_mimetype = None
        if form.category.data == 'gallery':
            if form.image.data:
                image_data, image_mimetype = save_picture(form.image.data)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return {'success': False, 'message': '갤러리에는 이미지가 필수입니다.'}, 400
                flash('갤러리에는 이미지가 필수입니다.', 'danger')
                return render_template('create_post.html', title='New Post', form=form)
        elif form.image.data:
             image_data, image_mimetype = save_picture(form.image.data)
             
        post = Post(
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            image_data=image_data,
            image_mimetype=image_mimetype,
            author=current_user
        )
        db.session.add(post)
        db.session.commit()
        flash('글이 작성되었습니다!', 'success')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from flask import jsonify
            return jsonify({'success': True, 'message': '글이 작성되었습니다!'})
        return redirect(url_for('main.index'))
        
    # GET 요청 또는 폼 검증 실패 시
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX 요청인 경우 폼만 반환
        from flask import jsonify
        if request.method == 'GET':
            # 폼 HTML 반환
            form_html = render_template('create_post.html', title='New Post', form=form)
            return form_html
        return jsonify({'success': False, 'message': '폼 검증에 실패했습니다.'}), 400
    return render_template('create_post.html', title='New Post', form=form)

@bp.route('/gallery')
def gallery():
    try:
        posts = Post.query.filter_by(category='gallery').order_by(Post.created_at.desc()).all()
        return render_template('gallery.html', posts=posts)
    except Exception as e:
        current_app.logger.error(f"Error in gallery route: {str(e)}")
        return render_template('gallery.html', posts=[])

@bp.route('/archive/<type_name>')
def archive(type_name):
    if type_name not in ['archive_1', 'archive_2']:
        abort(404)
    try:
        posts = Post.query.filter_by(category=type_name).order_by(Post.created_at.desc()).all()
        title = '아카이브 1' if type_name == 'archive_1' else '아카이브 2'
        return render_template('archive.html', posts=posts, title=title)
    except Exception as e:
        current_app.logger.error(f"Error in archive route: {str(e)}")
        title = '아카이브 1' if type_name == 'archive_1' else '아카이브 2'
        return render_template('archive.html', posts=[], title=title)

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


