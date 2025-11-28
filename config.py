import os
import sys

def is_vercel_environment():
    """Vercel 환경인지 확인"""
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        return True
    try:
        if sys.path and any('/var/task' in str(p) for p in sys.path):
            return True
        current_file = os.path.abspath(__file__)
        if '/var/task' in current_file:
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
    
    # 정적 파일( CSS / JS / 이미지 ) 브라우저 캐싱 강화
    # 한 번 받아온 후에는 1년 동안 다시 받지 않도록 해 로딩 체감 속도를 개선
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 초 단위 (365일)
    
    # 캐싱 설정
    CACHE_TYPE = 'SimpleCache'  # 로컬 메모리 캐시 (프로덕션에서는 Redis 권장)
    CACHE_DEFAULT_TIMEOUT = 300  # 5분
    
    # 티스토리 RSS 연동 설정
    TISTORY_RSS_URL = os.environ.get('TISTORY_RSS_URL', '')  # 예: https://yourblog.tistory.com/rss
    TISTORY_AUTO_SYNC_ENABLED = os.environ.get('TISTORY_AUTO_SYNC_ENABLED', 'False').lower() == 'true'
    TISTORY_SYNC_INTERVAL = int(os.environ.get('TISTORY_SYNC_INTERVAL', '15'))  # 분 단위 (기본 15분)
    TISTORY_DEFAULT_CATEGORY = os.environ.get('TISTORY_DEFAULT_CATEGORY', 'gallery')  # 기본 카테고리
    TISTORY_AUTO_AUTHOR_ID = os.environ.get('TISTORY_AUTO_AUTHOR_ID', '')  # 자동 게시글 작성자 ID (관리자)
    
    # Google OAuth Config
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    
    # Uploads - Vercel 환경에서는 /tmp 사용
    _is_vercel = is_vercel_environment()
    if _is_vercel:
        UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    else:
        try:
            _local_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads')
            _abs_local_path = os.path.abspath(_local_path)
            
            # Vercel 환경 경로 체크
            if '/var/task' in _local_path or '/var/task' in _abs_local_path:
                UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
            elif _local_path.startswith('/var') or _local_path.startswith('/usr') or \
                 _abs_local_path.startswith('/var') or _abs_local_path.startswith('/usr'):
                UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
            elif os.name == 'nt' and ':' in _local_path:
                UPLOAD_FOLDER = _local_path
            elif not _local_path.startswith('/'):
                UPLOAD_FOLDER = _local_path
            else:
                UPLOAD_FOLDER = _local_path
        except Exception:
            UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
