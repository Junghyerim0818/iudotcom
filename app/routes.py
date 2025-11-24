import os
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from . import db, oauth, login_manager
from .models import User, Post
from .forms import PostForm, AdminUserForm, ProfileForm

bp = Blueprint('main', __name__)

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
    # 최근 갤러리 글들 가져오기
    gallery_posts = Post.query.filter_by(category='gallery').order_by(Post.created_at.desc()).all()
    latest_post = gallery_posts[0] if gallery_posts else None
    other_posts = gallery_posts[1:] if len(gallery_posts) > 1 else []
    return render_template('index.html', latest_post=latest_post, other_posts=other_posts)

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

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
    form_picture.save(picture_path)
    return picture_fn

def save_profile_picture(form_picture, user_id):
    """프로필 사진을 저장하고 500x500으로 리사이즈"""
    # 안전한 디렉토리 생성 헬퍼 함수
    def safe_makedirs(path):
        """안전하게 디렉토리 생성 (/var 경로 차단)"""
        if '/var/task' in path or path.startswith('/var') or path.startswith('/usr'):
            raise OSError(f"Unsafe path: {path}")
        try:
            os.makedirs(path, exist_ok=True)
        except (OSError, PermissionError):
            # 이미 존재하거나 권한 문제 시 무시
            pass
    
    try:
        from PIL import Image
    except ImportError:
        # PIL이 없으면 기본 저장만 수행
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_picture.filename)
        picture_fn = f'profile_{user_id}_{random_hex}{f_ext}'
        profile_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
        safe_makedirs(profile_folder)
        picture_path = os.path.join(profile_folder, picture_fn)
        form_picture.save(picture_path)
        return picture_fn
    
    # 파일 크기 확인 (2MB)
    form_picture.seek(0, os.SEEK_END)
    file_size = form_picture.tell()
    form_picture.seek(0)
    
    if file_size > 2 * 1024 * 1024:
        raise ValueError('파일 크기는 2MB 이하여야 합니다.')
    
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = f'profile_{user_id}_{random_hex}{f_ext}'
    profile_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
    safe_makedirs(profile_folder)
    picture_path = os.path.join(profile_folder, picture_fn)
    
    # 이미지 열기 및 리사이즈
    image = Image.open(form_picture)
    # RGB로 변환 (RGBA인 경우)
    if image.mode in ('RGBA', 'LA', 'P'):
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
        image = rgb_image
    
    # 500x500으로 리사이즈 (비율 유지)
    image.thumbnail((500, 500), Image.Resampling.LANCZOS)
    
    # 정사각형으로 만들기 (중앙 정렬)
    width, height = image.size
    size = max(width, height)
    new_image = Image.new('RGB', (size, size), (255, 255, 255))
    new_image.paste(image, ((size - width) // 2, (size - height) // 2))
    new_image = new_image.resize((500, 500), Image.Resampling.LANCZOS)
    
    # 저장
    new_image.save(picture_path, 'JPEG', quality=85)
    return picture_fn

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
        image_file = None
        if form.category.data == 'gallery':
            if form.image.data:
                image_file = save_picture(form.image.data)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return {'success': False, 'message': '갤러리에는 이미지가 필수입니다.'}, 400
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

@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    try:
        # 이름 업데이트
        new_name = request.form.get('name', '').strip()
        if new_name:
            current_user.name = new_name
        
        # 프로필 사진 업데이트
        if 'profile_image' in request.files:
            profile_image = request.files['profile_image']
            if profile_image and profile_image.filename:
                # 기존 프로필 사진 삭제 (로컬에 저장된 경우)
                if current_user.profile_pic and current_user.profile_pic.startswith('profile_'):
                    old_pic_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], 
                        'profiles', 
                        current_user.profile_pic
                    )
                    if os.path.exists(old_pic_path):
                        try:
                            os.remove(old_pic_path)
                        except:
                            pass
                
                # 새 프로필 사진 저장
                picture_fn = save_profile_picture(profile_image, current_user.id)
                current_user.profile_pic = picture_fn
        
        db.session.commit()
        flash('프로필이 수정되었습니다.', 'success')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from flask import jsonify
            return jsonify({'success': True, 'message': '프로필이 수정되었습니다.'})
        
        return redirect(url_for('main.index'))
    except Exception as e:
        db.session.rollback()
        error_msg = str(e) if str(e) else '프로필 수정에 실패했습니다.'
        flash(error_msg, 'danger')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from flask import jsonify
            return jsonify({'success': False, 'message': error_msg}), 400
        
        return redirect(url_for('main.index'))

