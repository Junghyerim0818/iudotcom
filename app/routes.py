import os
import secrets
import base64
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, Response, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload, defer, load_only
from sqlalchemy import func
from . import db, oauth, login_manager, cache
from .models import User, Post, Setting, PostImage
from .forms import PostForm, AdminUserForm

bp = Blueprint('main', __name__)

# 캐시 무효화 헬퍼 함수
def invalidate_cache(category):
    """카테고리에 따라 관련 캐시 삭제"""
    cache.delete('index_gallery_posts')
    if category == 'gallery':
        for i in range(1, 11):
            cache.delete(f'gallery_posts_page_{i}')
    elif category in ['archive_1', 'archive_2']:
        for i in range(1, 11):
            cache.delete(f'archive_{category}_page_{i}')

# 아카이브 제목 헬퍼 함수
def get_archive_title(type_name, lang='ko'):
    """아카이브 타입과 언어에 따라 제목 반환"""
    if type_name == 'archive_1':
        return 'IU Verification' if lang == 'en' else '아이유 인증 글'
    else:
        return 'Support Verification' if lang == 'en' else '서포트 인증 글'

# Static 파일 직접 서빙 (Vercel 환경 대응, 캐싱 최적화)
@bp.route('/static/<path:filename>')
def serve_static(filename):
    """Static 파일을 직접 서빙 (루트의 static 폴더, 캐싱 헤더 포함)"""
    from flask import send_from_directory, current_app
    # Vercel 환경과 로컬 환경 모두 대응
    # app 폴더의 부모 디렉토리(프로젝트 루트)의 static 폴더
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, 'static')
    
    # 경로가 존재하지 않으면 Flask의 기본 static 폴더 사용
    if not os.path.exists(static_dir):
        static_dir = current_app.static_folder
    
    response = send_from_directory(static_dir, filename)
    
    # 정적 파일 캐싱 헤더 설정
    if filename.endswith(('.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.woff', '.woff2', '.ttf', '.eot')):
        # CSS, JS, 이미지, 폰트 파일은 1년 캐싱
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    else:
        # 기타 파일은 1시간 캐싱
        response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response

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
        # 순차 로딩: 처음에는 첫 10개를 빠르게 로드하여 즉시 표시
        # 나머지는 JavaScript에서 AJAX로 순차적으로 로드
        initial_count = 10  # 초기 로드 개수
        gallery_posts = db.session.query(Post).options(
            joinedload(Post.author),
            defer(Post.image_data),  # 대용량 이미지 데이터 제외 (메모리 및 네트워크 대역폭 절약)
            defer(Post.content)  # content는 필요할 때만 get_image_url()에서 DB에서 가져옴
        ).filter_by(category='gallery').order_by(Post.created_at.desc()).limit(initial_count).all()
        return render_template('index.html', gallery_posts=gallery_posts)
    except Exception as e:
        current_app.logger.error(f"Error in index route: {str(e)}")
        # DB 스키마가 업데이트되지 않은 경우를 대비해 빈 결과 반환
        return render_template('index.html', gallery_posts=[])

@bp.route('/api/gallery-posts')
def api_gallery_posts():
    """갤러리 포스트를 JSON으로 반환 (순차 로딩용)"""
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        posts = db.session.query(Post).options(
            joinedload(Post.author),
            defer(Post.image_data),
            defer(Post.content)
        ).filter_by(category='gallery').order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
        
        posts_data = []
        for post in posts:
            image_url = None
            try:
                if hasattr(post, 'get_image_url'):
                    # 원본 이미지 URL 사용 (use_thumbnail=False)
                    image_url = post.get_image_url(use_thumbnail=False)
            except Exception:
                pass
            
            posts_data.append({
                'id': post.id,
                'title': post.title,
                'created_at': post.created_at.strftime('%Y.%m.%d') if post.created_at else '',
                'author_name': '아이유닷컴' if post.author.is_admin() else post.author.name,
                'image_url': image_url,
                'has_image': post.has_image_data() if hasattr(post, 'has_image_data') else (post.image_filename or post.image_url)
            })
        
        return jsonify({'success': True, 'posts': posts_data, 'count': len(posts_data)})
    except Exception as e:
        current_app.logger.error(f"Error in api_gallery_posts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/stats')
@cache.cached(timeout=300, key_prefix='site_stats')  # 5분 캐싱
def api_stats():
    """사이트 통계 정보 반환"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # 총 게시글 수
        total_posts = db.session.query(func.count(Post.id)).scalar() or 0
        
        # 오늘 게시글 수
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_posts = db.session.query(func.count(Post.id)).filter(
            Post.created_at >= today_start
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'total_posts': total_posts,
            'today_posts': today_posts
        })
    except Exception as e:
        current_app.logger.error(f"Error in api_stats: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    try:
        google = get_google_client()
        if not google:
            flash('OAuth 설정이 올바르지 않습니다.', 'danger')
            return render_template('login_callback.html', success=False, message='OAuth 설정 오류')
        
        token = google.authorize_access_token()
        resp = google.get('https://www.googleapis.com/oauth2/v2/userinfo')
        user_info = resp.json()
        user_id = user_info.get('id')
        
        if not user_id:
            return render_template('login_callback.html', success=False, message='사용자 정보를 가져올 수 없습니다.')
        
        user = User.query.filter_by(id=user_id).first()
        if not user:
            user = User(
                id=user_id,
                email=user_info.get('email', ''),
                name=user_info.get('name', 'Unknown'),
                profile_pic=user_info.get('picture', ''),
                role='user'
            )
            db.session.add(user)
        else:
            user.email = user_info.get('email', user.email)
            user.name = user_info.get('name', user.name)
            user.profile_pic = user_info.get('picture', user.profile_pic)
        
        db.session.commit()
        login_user(user)
        return render_template('login_callback.html', success=True, message='로그인되었습니다.')
            
    except Exception as e:
        current_app.logger.error(f"Login callback error: {str(e)}", exc_info=True)
        db.session.rollback()
        return render_template('login_callback.html', success=False, message='로그인 중 오류가 발생했습니다.')

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
        
        # 캐시 무효화 (언어 변경 시)
        cache.delete('index_gallery_posts')
        for i in range(1, 11):
            cache.delete(f'gallery_posts_page_{i}')
            cache.delete(f'archive_archive_1_page_{i}')
            cache.delete(f'archive_archive_2_page_{i}')
    
    # AJAX 요청인 경우 JSON 응답
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'language': lang_code})
    
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
    """DB에 저장된 이미지를 반환하는 라우트 (WebP 지원 및 캐싱 최적화)"""
    try:
        post = Post.query.get_or_404(post_id)
        if post.image_data:
            # Postgres의 경우 bytes 객체로 반환되어야 함
            image_bytes = bytes(post.image_data) if not isinstance(post.image_data, bytes) else post.image_data
            
            # 쿼리 파라미터로 크기 제한 확인 (카드 스택 최적화용)
            max_width = request.args.get('w', type=int)
            max_height = request.args.get('h', type=int)
            
            # WebP 지원 확인
            accept_header = request.headers.get('Accept', '')
            supports_webp = 'image/webp' in accept_header
            
            # 크기 제한이 있으면 이미지 리사이징
            if max_width or max_height or supports_webp:
                try:
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(image_bytes))
                    
                    # RGBA 모드인 경우 RGB로 변환 (JPEG 호환성)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        if supports_webp:
                            # WebP는 알파 채널 지원
                            pass
                        else:
                            # JPEG는 알파 채널 미지원, RGB로 변환
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                            img = rgb_img
                    elif img.mode != 'RGB' and not supports_webp:
                        img = img.convert('RGB')
                    
                    original_width, original_height = img.size
                    
                    # 비율 유지하며 리사이징
                    if max_width or max_height:
                        if max_width and max_height:
                            # 둘 다 지정된 경우 비율 유지하며 작은 쪽에 맞춤
                            ratio = min(max_width / original_width, max_height / original_height)
                            new_width = int(original_width * ratio)
                            new_height = int(original_height * ratio)
                        elif max_width:
                            ratio = max_width / original_width
                            new_width = max_width
                            new_height = int(original_height * ratio)
                        else:
                            ratio = max_height / original_height
                            new_width = int(original_width * ratio)
                            new_height = max_height
                        
                        # 원본보다 크면 리사이징하지 않음
                        if new_width < original_width or new_height < original_height:
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    output = io.BytesIO()
                    
                    # WebP 지원 시 WebP로 변환 (압축 효율 향상)
                    if supports_webp:
                        img.save(output, format='WEBP', quality=85, method=6)
                        mimetype = 'image/webp'
                    else:
                        img_format = img.format or 'JPEG'
                        if img_format == 'PNG' and img.mode == 'RGB':
                            # PNG를 JPEG로 변환 (더 작은 파일 크기)
                            img_format = 'JPEG'
                        img.save(output, format=img_format, quality=85, optimize=True)
                        mimetype = 'image/jpeg' if img_format == 'JPEG' else (post.image_mimetype or 'image/jpeg')
                    
                    image_bytes = output.getvalue()
                except ImportError:
                    # PIL이 없으면 원본 반환
                    mimetype = post.image_mimetype or 'image/jpeg'
                except Exception as e:
                    current_app.logger.warning(f"Image resize failed: {str(e)}, returning original")
                    mimetype = post.image_mimetype or 'image/jpeg'
            else:
                mimetype = post.image_mimetype or 'image/jpeg'
            
            # ETag 생성 (캐싱 최적화)
            import hashlib
            etag = hashlib.md5(image_bytes).hexdigest()
            
            # If-None-Match 헤더 확인 (304 Not Modified 응답)
            if request.headers.get('If-None-Match') == etag:
                return Response(status=304)
            
            response = Response(image_bytes, mimetype=mimetype)
            # 캐싱 헤더 설정 (1년 캐싱)
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['ETag'] = etag
            response.headers['Vary'] = 'Accept'  # WebP 지원 여부에 따라 다른 응답
            return response
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error serving image for post {post_id}: {str(e)}")
        abort(404)

@bp.route('/image/<int:post_id>/download')
def download_original_image(post_id):
    """원본 이미지를 다운로드하는 라우트 (크기 제한 없음)"""
    try:
        post = Post.query.get_or_404(post_id)
        if post.image_data:
            # Postgres의 경우 bytes 객체로 반환되어야 함
            image_bytes = bytes(post.image_data) if not isinstance(post.image_data, bytes) else post.image_data
            
            # 파일명 생성
            filename = f"image_{post_id}"
            if post.image_mimetype:
                if 'jpeg' in post.image_mimetype or 'jpg' in post.image_mimetype:
                    filename += '.jpg'
                elif 'png' in post.image_mimetype:
                    filename += '.png'
                elif 'gif' in post.image_mimetype:
                    filename += '.gif'
                elif 'webp' in post.image_mimetype:
                    filename += '.webp'
                else:
                    filename += '.jpg'
            else:
                filename += '.jpg'
            
            return Response(
                image_bytes,
                mimetype=post.image_mimetype or 'image/jpeg',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )
        elif post.image_url:
            # 외부 이미지 URL인 경우 리다이렉트
            return redirect(post.image_url)
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error downloading image for post {post_id}: {str(e)}")
        abort(404)

def save_picture(form_picture, max_size=None):
    """이미지를 DB에 저장할 포맷으로 변환하고 (image_data, image_mimetype) 튜플 반환
    
    Args:
        form_picture: 업로드된 파일 객체
        max_size (int, optional): 최대 긴 변의 크기 (px). None이면 썸네일용 기본값(1200) 사용.
    """
    if not form_picture:
        return None, None
        
    # 파일 데이터 읽기
    raw_data = form_picture.read()
    
    # 파일 포인터 리셋 (재사용을 위해)
    form_picture.seek(0)

    # 기본 MIME 타입 (썸네일은 JPEG/WebP 등으로 압축)
    mimetype = form_picture.content_type or 'image/jpeg'
    if not mimetype or not mimetype.startswith('image/'):
        mimetype = 'image/jpeg'

    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(raw_data))

        # 리사이징 크기 설정
        if max_size:
            max_w, max_h = max_size, max_size
        else:
            # 기본 썸네일 크기
            max_w, max_h = 800, 1200
            
        orig_w, orig_h = img.size

        # 비율 유지하며 축소
        ratio = min(max_w / orig_w, max_h / orig_h)
        # 원본보다 작게 설정된 경우에만 축소
        if ratio < 1.0:
            new_w = int(orig_w * ratio)
            new_h = int(orig_h * ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 알파 채널이 있는 경우 배경 흰색으로 합성하여 JPEG로 저장
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        output = io.BytesIO()
        # 썸네일은 JPEG로 저장 (용량 절감)
        img.save(output, format='JPEG', quality=85, optimize=True)
        image_data = output.getvalue()
        mimetype = 'image/jpeg'
    except Exception as e:
        # Pillow가 없거나 변환 실패 시 원본 데이터를 그대로 저장 (최후의 보루)
        current_app.logger.warning(f"Thumbnail generation failed, storing original image: {str(e)}")
        image_data = raw_data

    return (image_data, mimetype)

@bp.route('/post/image/<int:image_id>')
def get_post_image(image_id):
    """게시글의 추가 이미지 서빙"""
    try:
        image = PostImage.query.get_or_404(image_id)
        
        # ETag 생성
        import hashlib
        etag = hashlib.md5(image.image_data).hexdigest()
        
        if request.headers.get('If-None-Match') == etag:
            return Response(status=304)
            
        response = Response(image.image_data, mimetype=image.image_mimetype)
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        response.headers['ETag'] = etag
        return response
    except Exception as e:
        current_app.logger.error(f"Error serving post image {image_id}: {str(e)}")
        abort(404)

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
            
        # 다중 파일 가져오기
        files = request.files.getlist('image')
        # 빈 파일 필터링
        files = [f for f in files if f.filename]
        
        if form.category.data == 'gallery':
            if image_url:
                # URL이 있으면 URL 사용 (관리자만)
                pass
            elif files:
                # 첫 번째 이미지를 대표 썸네일로 사용
                image_data, image_mimetype = save_picture(files[0])
                files[0].seek(0) # 포인터 초기화
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return {'success': False, 'message': '갤러리에는 이미지가 필수입니다.'}, 400
                flash('갤러리에는 이미지가 필수입니다.', 'danger')
                return render_template('create_post.html', title='New Post', form=form)
        elif image_url:
            # URL이 있으면 URL 사용 (관리자만)
            pass
        elif files:
             image_data, image_mimetype = save_picture(files[0])
             files[0].seek(0)
             
        post = Post(
            title=form.title.data,
            content=form.content.data.strip() if form.content.data else '',
            category=form.category.data,
            image_data=image_data,
            image_mimetype=image_mimetype,
            image_url=image_url,
            author=current_user
        )
        db.session.add(post)
        db.session.flush() # ID 생성을 위해 flush
        
        # 추가 이미지 저장 (모든 업로드된 이미지 저장)
        if files:
            for i, file in enumerate(files):
                if file.filename:
                    # 상세 페이지용 고화질 (최대 2500px)
                    img_data, img_mime = save_picture(file, max_size=2500)
                    post_image = PostImage(
                        image_data=img_data, 
                        image_mimetype=img_mime,
                        order=i
                    )
                    post.images.append(post_image)
        
        db.session.commit()
        
        # 캐시 무효화
        invalidate_cache(form.category.data)
        
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
        # 페이지네이션 추가 (페이지당 8개)
        page = request.args.get('page', 1, type=int)
        per_page = 8
        
        # 순차 로딩: 첫 페이지만 먼저 빠르게 로드
        # 첫 페이지가 아닌 경우에도 캐시 활용
        cache_key = f'gallery_posts_page_{page}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # 이미지 데이터는 제외하고 메타데이터만 가져오기 (성능 최적화)
        # content는 썸네일 이미지 추출을 위해 로드 필요
        posts_query = db.session.query(Post).options(
            joinedload(Post.author),
            defer(Post.image_data)  # 대용량 이미지 데이터 제외
            # content는 썸네일 이미지 추출을 위해 로드
        ).filter_by(category='gallery').order_by(Post.created_at.desc())
        
        posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # 첫 페이지인 경우 즉시 반환 (나머지 페이지는 백그라운드에서 캐싱)
        if page == 1:
            result = render_template('gallery.html', posts=posts.items, pagination=posts)
            # 첫 페이지 캐싱
            cache.set(cache_key, result, timeout=120)
            
            # 백그라운드에서 다음 페이지들을 미리 캐싱 (비동기, 블로킹하지 않음)
            # 이 부분은 실제로는 클라이언트 측에서 AJAX로 처리하거나
            # 별도의 백그라운드 작업으로 처리하는 것이 좋습니다
            
            return result
        
        # 첫 페이지가 아닌 경우 정상적으로 반환
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
        
        # 이미지 데이터는 제외하고 메타데이터만 가져오기 (성능 최적화)
        # content는 썸네일 이미지 추출을 위해 로드 필요
        posts_query = db.session.query(Post).options(
            joinedload(Post.author),
            defer(Post.image_data)  # 대용량 이미지 데이터 제외
            # content는 썸네일 이미지 추출을 위해 로드
        ).filter_by(category=type_name).order_by(Post.created_at.desc())
        
        posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)
        
        title = get_archive_title(type_name, session.get('language', 'ko'))
        result = render_template('archive.html', posts=posts.items, pagination=posts, title=title, type_name=type_name)
        cache.set(cache_key, result, timeout=120)
        return result
    except Exception as e:
        current_app.logger.error(f"Error in archive route: {str(e)}")
        title = get_archive_title(type_name, session.get('language', 'ko'))
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
        
        title = get_archive_title(type_name, session.get('language', 'ko'))
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
    
    # 티스토리 설정 가져오기 (데이터베이스 우선, 없으면 환경 변수)
    tistory_rss_url = Setting.get('TISTORY_RSS_URL') or current_app.config.get('TISTORY_RSS_URL', '')
    tistory_auto_sync = Setting.get('TISTORY_AUTO_SYNC_ENABLED', 'false').lower() == 'true' or current_app.config.get('TISTORY_AUTO_SYNC_ENABLED', False)
    tistory_sync_interval = int(Setting.get('TISTORY_SYNC_INTERVAL') or current_app.config.get('TISTORY_SYNC_INTERVAL', 15))
    tistory_default_category = Setting.get('TISTORY_DEFAULT_CATEGORY') or current_app.config.get('TISTORY_DEFAULT_CATEGORY', 'gallery')
    
    return render_template('admin.html', 
                         users=users, 
                         config=current_app.config,
                         tistory_rss_url=tistory_rss_url,
                         tistory_auto_sync=tistory_auto_sync,
                         tistory_sync_interval=tistory_sync_interval,
                         tistory_default_category=tistory_default_category)

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
        
        # 캐시 무효화
        invalidate_cache(post.category)
        
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
    
    # 캐시 무효화
    invalidate_cache(category)
    
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
    
    # 데이터베이스에서 설정 가져오기 (없으면 환경 변수 사용)
    rss_url = Setting.get('TISTORY_RSS_URL') or current_app.config.get('TISTORY_RSS_URL')
    if not rss_url:
        flash('티스토리 RSS URL이 설정되지 않았습니다.', 'danger')
        return redirect(url_for('main.admin'))
    
    default_category = Setting.get('TISTORY_DEFAULT_CATEGORY') or current_app.config.get('TISTORY_DEFAULT_CATEGORY', 'gallery')
    author_id = Setting.get('TISTORY_AUTO_AUTHOR_ID') or current_app.config.get('TISTORY_AUTO_AUTHOR_ID')
    
    try:
        from .tistory_sync import sync_tistory_posts
        sync_tistory_posts(current_app, rss_url, default_category, author_id)
        flash('티스토리 동기화가 완료되었습니다.', 'success')
    except Exception as e:
        current_app.logger.error(f"티스토리 동기화 오류: {str(e)}")
        flash(f'티스토리 동기화 중 오류가 발생했습니다: {str(e)}', 'danger')
    
    return redirect(url_for('main.admin'))

@bp.route('/admin/tistory/settings', methods=['POST'])
@login_required
def update_tistory_settings():
    """티스토리 설정 업데이트 (관리자 전용)"""
    if not current_user.is_admin():
        abort(403)
    
    rss_url = request.form.get('rss_url', '').strip()
    auto_sync_enabled = request.form.get('auto_sync_enabled') == 'on'
    sync_interval = int(request.form.get('sync_interval', 15))
    default_category = request.form.get('default_category', 'gallery').strip()
    
    # 설정 저장
    if rss_url:
        Setting.set('TISTORY_RSS_URL', rss_url)
    else:
        Setting.set('TISTORY_RSS_URL', '')
    
    Setting.set('TISTORY_AUTO_SYNC_ENABLED', 'true' if auto_sync_enabled else 'false')
    Setting.set('TISTORY_SYNC_INTERVAL', str(sync_interval))
    Setting.set('TISTORY_DEFAULT_CATEGORY', default_category)
    
    flash('티스토리 설정이 저장되었습니다.', 'success')
    return redirect(url_for('main.admin'))


