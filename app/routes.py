import os
import secrets
import base64
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, Response, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from . import db, oauth, login_manager, cache
from .models import User, Post
from .forms import PostForm, AdminUserForm

bp = Blueprint('main', __name__)

# Static 파일 직접 서빙 (Vercel 환경 대응)
@bp.route('/static/<path:filename>')
def serve_static(filename):
    """Static 파일을 직접 서빙 (루트의 static 폴더)"""
    from flask import send_from_directory, current_app
    # Vercel 환경과 로컬 환경 모두 대응
    # app 폴더의 부모 디렉토리(프로젝트 루트)의 static 폴더
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, 'static')
    
    # 경로가 존재하지 않으면 Flask의 기본 static 폴더 사용
    if not os.path.exists(static_dir):
        static_dir = current_app.static_folder
    
    return send_from_directory(static_dir, filename)

# Google OAuth Setup - 지연 등록 방식
def get_google_client():
    """Google OAuth 클라이언트를 가져오거나 등록"""
    if hasattr(oauth, 'google'):
        return oauth.google
    
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return None
    
    return oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@bp.route('/')
@cache.cached(timeout=60, key_prefix='index_gallery_posts')  # 1분 캐싱
def index():
    try:
        # 최근 갤러리 글들 가져오기 (날짜순 정렬 - 최신이 맨 앞)
        # 이미지 데이터는 제외하고 메타데이터만 가져오기 (성능 최적화)
        # 최대 20개만 가져오기 (페이지네이션)
        gallery_posts = db.session.query(Post).options(
            joinedload(Post.author)
        ).filter_by(category='gallery').order_by(Post.created_at.desc()).limit(20).all()
        return render_template('index.html', gallery_posts=gallery_posts)
    except Exception as e:
        current_app.logger.error(f"Error in index route: {str(e)}")
        # DB 스키마가 업데이트되지 않은 경우를 대비해 빈 결과 반환
        return render_template('index.html', gallery_posts=[])

@bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    google = get_google_client()
    if not google:
        flash('OAuth 설정이 올바르지 않습니다. 관리자에게 문의하세요.', 'danger')
        return redirect(url_for('main.index'))
    
    redirect_uri = url_for('main.authorize', _external=True)
    # 계정 선택 화면이 나오도록 prompt 파라미터 추가
    return google.authorize_redirect(redirect_uri, prompt='select_account')

@bp.route('/login/callback')
def authorize():
    import traceback
    error_details = []
    
    try:
        # 1. OAuth 클라이언트 확인
        error_details.append("Step 1: Getting Google OAuth client")
        google = get_google_client()
        if not google:
            error_msg = "Google OAuth client not available"
            error_details.append(f"ERROR: {error_msg}")
            return f"<pre>{chr(10).join(error_details)}</pre>", 500
        
        # 2. 토큰 인증
        error_details.append("Step 2: Authorizing access token")
        try:
            token = google.authorize_access_token()
            error_details.append(f"SUCCESS: Token received")
        except Exception as e:
            error_msg = f"Error authorizing access token: {str(e)}"
            error_details.append(f"ERROR: {error_msg}")
            error_details.append(f"Traceback: {traceback.format_exc()}")
            return f"<pre>{chr(10).join(error_details)}</pre>", 500
        
        # 3. 사용자 정보 가져오기
        error_details.append("Step 3: Fetching user info")
        try:
            resp = google.get('https://www.googleapis.com/oauth2/v2/userinfo')
            user_info = resp.json()
            error_details.append(f"SUCCESS: User info received: {user_info}")
        except Exception as e:
            error_msg = f"Error fetching user info: {str(e)}"
            error_details.append(f"ERROR: {error_msg}")
            error_details.append(f"Traceback: {traceback.format_exc()}")
            return f"<pre>{chr(10).join(error_details)}</pre>", 500
        
        # 4. User ID 확인
        error_details.append("Step 4: Checking user ID")
        user_id = user_info.get('id')
        if not user_id:
            error_msg = "User ID not found in user_info"
            error_details.append(f"ERROR: {error_msg}")
            error_details.append(f"User info keys: {list(user_info.keys())}")
            return f"<pre>{chr(10).join(error_details)}</pre>", 500
        
        # 5. 데이터베이스 작업
        error_details.append("Step 5: Database operations")
        try:
            user = User.query.filter_by(id=user_id).first()
            
            if not user:
                error_details.append("Creating new user")
                user = User(
                    id=user_id,
                    email=user_info.get('email', ''),
                    name=user_info.get('name', 'Unknown'),
                    profile_pic=user_info.get('picture', ''),
                    role='user'
                )
                db.session.add(user)
                db.session.commit()
                error_details.append("SUCCESS: New user created")
            else:
                error_details.append("Updating existing user")
                user.email = user_info.get('email', user.email)
                user.name = user_info.get('name', user.name)
                user.profile_pic = user_info.get('picture', user.profile_pic)
                db.session.commit()
                error_details.append("SUCCESS: User updated")
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            error_details.append(f"ERROR: {error_msg}")
            error_details.append(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return f"<pre>{chr(10).join(error_details)}</pre>", 500
        
        # 6. 로그인 처리
        error_details.append("Step 6: Logging in user")
        try:
            login_user(user)
            error_details.append("SUCCESS: User logged in")
        except Exception as e:
            error_msg = f"Login error: {str(e)}"
            error_details.append(f"ERROR: {error_msg}")
            error_details.append(f"Traceback: {traceback.format_exc()}")
            return f"<pre>{chr(10).join(error_details)}</pre>", 500
        
        # 7. 템플릿 렌더링
        error_details.append("Step 7: Rendering template")
        try:
            return render_template('login_callback.html', success=True, message='로그인되었습니다.')
        except Exception as e:
            error_msg = f"Template rendering error: {str(e)}"
            error_details.append(f"ERROR: {error_msg}")
            error_details.append(f"Traceback: {traceback.format_exc()}")
            return f"<pre>{chr(10).join(error_details)}</pre>", 500
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        error_details.append(f"FATAL ERROR: {error_msg}")
        error_details.append(f"Full traceback: {traceback.format_exc()}")
        return f"<pre>{chr(10).join(error_details)}</pre>", 500

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/lang/<lang_code>')
def change_language(lang_code):
    """언어 변경"""
    if lang_code in ['ko', 'en']:
        session['language'] = lang_code
        session.permanent = True  # 세션을 영구적으로 저장
        session.modified = True  # 세션 수정 표시
    # 리다이렉트할 때 현재 페이지로 돌아가거나 홈으로
    referrer = request.referrer
    if referrer:
        # 같은 호스트인지 확인
        from urllib.parse import urlparse
        referrer_host = urlparse(referrer).netloc
        current_host = request.host
        if referrer_host == current_host or referrer_host == '':
            return redirect(referrer)
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
        image_url = None
        
        # 관리자인 경우 티스토리 이미지 URL 사용 가능
        if current_user.is_admin() and form.image_url.data:
            image_url = form.image_url.data.strip()
        
        if form.category.data == 'gallery':
            if image_url:
                # URL이 있으면 URL 사용 (관리자만)
                pass
            elif form.image.data:
                image_data, image_mimetype = save_picture(form.image.data)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return {'success': False, 'message': '갤러리에는 이미지가 필수입니다.'}, 400
                flash('갤러리에는 이미지가 필수입니다.', 'danger')
                return render_template('create_post.html', title='New Post', form=form)
        elif image_url:
            # URL이 있으면 URL 사용 (관리자만)
            pass
        elif form.image.data:
             image_data, image_mimetype = save_picture(form.image.data)
             
        post = Post(
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            image_data=image_data,
            image_mimetype=image_mimetype,
            image_url=image_url,
            author=current_user
        )
        db.session.add(post)
        db.session.commit()
        
        # 캐시 무효화 (모든 관련 캐시 삭제)
        cache.delete('index_gallery_posts')
        # 갤러리 캐시 삭제 (모든 페이지)
        for i in range(1, 11):  # 최대 10페이지까지
            cache.delete(f'gallery_posts_page_{i}')
        if form.category.data in ['archive_1', 'archive_2']:
            for i in range(1, 11):  # 최대 10페이지까지
                cache.delete(f'archive_{form.category.data}_page_{i}')
        
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
        # 페이지네이션 추가 (페이지당 30개)
        page = request.args.get('page', 1, type=int)
        per_page = 30
        
        # 캐시 키 생성 (페이지 포함)
        cache_key = f'gallery_posts_page_{page}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # 이미지 데이터는 제외하고 메타데이터만 가져오기
        posts_query = db.session.query(Post).options(
            joinedload(Post.author)
        ).filter_by(category='gallery').order_by(Post.created_at.desc())
        
        posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)
        result = render_template('gallery.html', posts=posts.items, pagination=posts)
        cache.set(cache_key, result, timeout=120)  # 2분 캐싱
        return result
    except Exception as e:
        current_app.logger.error(f"Error in gallery route: {str(e)}")
        return render_template('gallery.html', posts=[], pagination=None)

@bp.route('/gallery/<int:post_id>')
def gallery_detail(post_id):
    """갤러리 상세 페이지 - 원본 이미지 보기"""
    try:
        # Eager loading으로 author 정보도 함께 가져오기
        post = db.session.query(Post).options(
            joinedload(Post.author)
        ).filter_by(id=post_id).first_or_404()
        
        if post.category != 'gallery':
            abort(404)
        
        # 이전/다음 포스트 가져오기 (인덱스 활용)
        prev_post = db.session.query(Post).filter(
            Post.category == 'gallery',
            Post.id < post_id
        ).order_by(Post.id.desc()).first()
        
        next_post = db.session.query(Post).filter(
            Post.category == 'gallery',
            Post.id > post_id
        ).order_by(Post.id.asc()).first()
        
        return render_template('gallery_detail.html', post=post, prev_post=prev_post, next_post=next_post)
    except Exception as e:
        current_app.logger.error(f"Error in gallery_detail route: {str(e)}")
        abort(404)

@bp.route('/archive/<type_name>')
def archive(type_name):
    if type_name not in ['archive_1', 'archive_2']:
        abort(404)
    try:
        # 페이지네이션 추가
        page = request.args.get('page', 1, type=int)
        per_page = 30
        
        # 캐시 키 생성 (페이지 포함)
        cache_key = f'archive_{type_name}_page_{page}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        posts_query = db.session.query(Post).options(
            joinedload(Post.author)
        ).filter_by(category=type_name).order_by(Post.created_at.desc())
        
        posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # 언어에 따라 제목 설정
        from flask import session
        current_lang = session.get('language', 'ko')
        if type_name == 'archive_1':
            title = 'IU Verification' if current_lang == 'en' else '아이유 인증 글'
        else:
            title = 'Support Verification' if current_lang == 'en' else '서포트 인증 글'
        
        result = render_template('archive.html', posts=posts.items, pagination=posts, title=title, type_name=type_name)
        cache.set(cache_key, result, timeout=120)  # 2분 캐싱
        return result
    except Exception as e:
        current_app.logger.error(f"Error in archive route: {str(e)}")
        from flask import session
        current_lang = session.get('language', 'ko')
        if type_name == 'archive_1':
            title = 'IU Verification' if current_lang == 'en' else '아이유 인증 글'
        else:
            title = 'Support Verification' if current_lang == 'en' else '서포트 인증 글'
        return render_template('archive.html', posts=[], pagination=None, title=title, type_name=type_name)

@bp.route('/archive/<type_name>/<int:post_id>')
def archive_detail(type_name, post_id):
    """아카이브 상세 페이지 - 원본 이미지 보기"""
    if type_name not in ['archive_1', 'archive_2']:
        abort(404)
    try:
        # Eager loading으로 author 정보도 함께 가져오기
        post = db.session.query(Post).options(
            joinedload(Post.author)
        ).filter_by(id=post_id).first_or_404()
        
        if post.category != type_name:
            abort(404)
        
        # 이전/다음 포스트 가져오기 (인덱스 활용)
        prev_post = db.session.query(Post).filter(
            Post.category == type_name,
            Post.id < post_id
        ).order_by(Post.id.desc()).first()
        
        next_post = db.session.query(Post).filter(
            Post.category == type_name,
            Post.id > post_id
        ).order_by(Post.id.asc()).first()
        
        # 언어에 따라 제목 설정
        from flask import session
        current_lang = session.get('language', 'ko')
        if type_name == 'archive_1':
            title = 'IU Verification' if current_lang == 'en' else '아이유 인증 글'
        else:
            title = 'Support Verification' if current_lang == 'en' else '서포트 인증 글'
        
        return render_template('archive_detail.html', post=post, prev_post=prev_post, next_post=next_post, type_name=type_name, title=title)
    except Exception as e:
        current_app.logger.error(f"Error in archive_detail route: {str(e)}")
        abort(404)

@bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin():
        abort(403)
    
    users = User.query.all()
    return render_template('admin.html', users=users, config=current_app.config)

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

@bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    if not current_user.is_admin():
        abort(403)
    
    post = Post.query.get_or_404(post_id)
    form = PostForm(obj=post)
    
    # AJAX 요청인 경우 폼만 반환
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 폼에 기존 이미지 URL 설정
        if post.image_url:
            form.image_url.data = post.image_url
        return render_template('edit_post.html', form=form, post=post)
    
    if form.validate_on_submit():
        image_data = post.image_data
        image_mimetype = post.image_mimetype
        image_url = post.image_url
        
        # 관리자인 경우 티스토리 이미지 URL 사용 가능
        if form.image_url.data:
            image_url = form.image_url.data.strip()
            # URL이 변경되면 기존 이미지 데이터는 유지하지 않음
            if image_url:
                image_data = None
                image_mimetype = None
        
        # 새 이미지 파일이 업로드된 경우
        if form.image.data:
            image_data, image_mimetype = save_picture(form.image.data)
            # 파일 업로드 시 URL은 무시
            image_url = None
        
        # 갤러리 카테고리인 경우 이미지 필수 체크
        if form.category.data == 'gallery':
            if not image_url and not image_data and not post.image_data:
                flash('갤러리에는 이미지가 필수입니다.', 'danger')
                return render_template('edit_post.html', form=form, post=post)
        
        post.title = form.title.data
        post.content = form.content.data
        post.category = form.category.data
        if image_data is not None:
            post.image_data = image_data
        if image_mimetype is not None:
            post.image_mimetype = image_mimetype
        if image_url is not None:
            post.image_url = image_url
        
        db.session.commit()
        
        # 캐시 무효화 (모든 관련 캐시 삭제)
        cache.delete('index_gallery_posts')
        if post.category == 'gallery':
            for i in range(1, 11):  # 최대 10페이지까지
                cache.delete(f'gallery_posts_page_{i}')
        elif post.category in ['archive_1', 'archive_2']:
            for i in range(1, 11):  # 최대 10페이지까지
                cache.delete(f'archive_{post.category}_page_{i}')
        
        flash('글이 수정되었습니다!', 'success')
        
        # 카테고리에 따라 리다이렉트
        if post.category == 'gallery':
            return redirect(url_for('main.gallery_detail', post_id=post.id))
        elif post.category in ['archive_1', 'archive_2']:
            return redirect(url_for('main.archive', type_name=post.category))
        else:
            return redirect(url_for('main.index'))
    
    # 폼에 기존 이미지 URL 설정
    if post.image_url:
        form.image_url.data = post.image_url
    
    return render_template('edit_post.html', form=form, post=post)

@bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    if not current_user.is_admin():
        abort(403)
    
    post = Post.query.get_or_404(post_id)
    category = post.category
    
    db.session.delete(post)
    db.session.commit()
    
    # 캐시 무효화 (모든 관련 캐시 삭제)
    cache.delete('index_gallery_posts')
    if category == 'gallery':
        for i in range(1, 11):  # 최대 10페이지까지
            cache.delete(f'gallery_posts_page_{i}')
    elif category in ['archive_1', 'archive_2']:
        for i in range(1, 11):  # 최대 10페이지까지
            cache.delete(f'archive_{category}_page_{i}')
    
    flash('글이 삭제되었습니다.', 'success')
    
    # 카테고리에 따라 리다이렉트
    if category == 'gallery':
        return redirect(url_for('main.gallery'))
    elif category in ['archive_1', 'archive_2']:
        return redirect(url_for('main.archive', type_name=category))
    else:
        return redirect(url_for('main.index'))

@bp.route('/admin/tistory/sync', methods=['POST'])
@login_required
def manual_tistory_sync():
    """수동 티스토리 동기화 (관리자 전용)"""
    if not current_user.is_admin():
        abort(403)
    
    rss_url = current_app.config.get('TISTORY_RSS_URL')
    if not rss_url:
        flash('티스토리 RSS URL이 설정되지 않았습니다.', 'danger')
        return redirect(url_for('main.admin'))
    
    default_category = current_app.config.get('TISTORY_DEFAULT_CATEGORY', 'gallery')
    author_id = current_app.config.get('TISTORY_AUTO_AUTHOR_ID')
    
    try:
        from .tistory_sync import sync_tistory_posts
        sync_tistory_posts(current_app, rss_url, default_category, author_id)
        flash('티스토리 동기화가 완료되었습니다.', 'success')
    except Exception as e:
        current_app.logger.error(f"티스토리 동기화 오류: {str(e)}")
        flash(f'티스토리 동기화 중 오류가 발생했습니다: {str(e)}', 'danger')
    
    return redirect(url_for('main.admin'))


