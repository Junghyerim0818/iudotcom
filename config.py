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
    
    if _is_vercel:
        UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    else:
        # 로컬 개발 환경
        UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
