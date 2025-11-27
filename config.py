import os
import sys

# Vercel 환경 감지 (가장 확실한 방법)
def is_vercel_environment():
    """Vercel 환경인지 확인"""
    # 환경 변수 확인
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        return True
    # sys.path에 /var/task가 있는지 확인
    try:
        if sys.path and any('/var/task' in str(p) for p in sys.path):
            return True
    except:
        pass
    # 현재 파일 경로 확인
    try:
        current_file = os.path.abspath(__file__)
        if '/var/task' in current_file:
            return True
    except:
        pass
    # __file__이 /var/task에 있는지 확인
    try:
        if '__file__' in globals() and '/var/task' in str(__file__):
            return True
    except:
        pass
    return False

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # Vercel Postgres uses POSTGRES_URL or DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # 연결 유효성 검사
        'pool_recycle': 300,     # 연결 재사용 시간
    }
    
    # 캐싱 설정
    CACHE_TYPE = 'SimpleCache'  # 로컬 메모리 캐시 (프로덕션에서는 Redis 권장)
    CACHE_DEFAULT_TIMEOUT = 300  # 5분
    
    # 티스토리 RSS 연동 설정
    TISTORY_RSS_URL = os.environ.get('https://selfiepod.tistory.com/rss', '')  # 예: https://yourblog.tistory.com/rss
    TISTORY_AUTO_SYNC_ENABLED = os.environ.get('TISTORY_AUTO_SYNC_ENABLED', 'False').lower() == 'true'
    TISTORY_SYNC_INTERVAL = int(os.environ.get('TISTORY_SYNC_INTERVAL', '15'))  # 분 단위 (기본 15분)
    TISTORY_DEFAULT_CATEGORY = os.environ.get('TISTORY_DEFAULT_CATEGORY', 'gallery')  # 기본 카테고리
    TISTORY_AUTO_AUTHOR_ID = os.environ.get('thsehddnr68@gmail.com', '')  # 자동 게시글 작성자 ID (관리자)
    
    # Google OAuth Config
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    
    # Uploads
    # Vercel 환경에서는 /tmp 디렉토리 사용 (임시 저장소)
    # 프로덕션에서는 외부 스토리지(S3, Cloudinary 등) 사용 권장
    _is_vercel = is_vercel_environment()
    
    # 추가 안전장치: 경로에 /var/task가 포함되어 있으면 Vercel 환경으로 간주
    if not _is_vercel:
        try:
            _test_path = os.path.abspath(os.path.dirname(__file__))
            if '/var/task' in _test_path:
                _is_vercel = True
        except:
            pass
    
    # 안전장치: sys.path나 환경 변수로도 확인
    if not _is_vercel:
        try:
            if sys.path and any('/var/task' in str(p) for p in sys.path):
                _is_vercel = True
        except:
            pass
    
    # 기본값을 /tmp로 설정 (Vercel 환경에서 안전)
    # app/__init__.py에서 최종적으로 경로를 검증하고 변경함
    # 안전 우선: 확실하지 않으면 /tmp 사용
    if _is_vercel:
        UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    else:
        # 로컬 개발 환경 확인
        try:
            _local_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads')
            _abs_local_path = os.path.abspath(_local_path)
            
            # /var/task가 포함되어 있거나 /var, /usr로 시작하면 무조건 /tmp 사용
            if '/var/task' in _local_path or '/var/task' in _abs_local_path:
                UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
            elif _local_path.startswith('/var') or _local_path.startswith('/usr'):
                UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
            elif _abs_local_path.startswith('/var') or _abs_local_path.startswith('/usr'):
                UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
            else:
                # Windows 경로인 경우에만 로컬 경로 사용
                if os.name == 'nt' and ':' in _local_path:
                    UPLOAD_FOLDER = _local_path
                elif not _local_path.startswith('/'):
                    # 상대 경로인 경우
                    UPLOAD_FOLDER = _local_path
                else:
                    # Unix 계열이고 안전한 경로인 경우
                    UPLOAD_FOLDER = _local_path
        except Exception:
            # 경로 생성 실패 시 기본값으로 /tmp 사용 (안전)
            UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
