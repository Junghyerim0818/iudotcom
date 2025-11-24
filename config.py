import os

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
    # Vercel 환경 감지: /var/task 경로가 있으면 Vercel 환경
    import sys
    is_vercel = (
        os.environ.get('VERCEL') or 
        os.environ.get('VERCEL_ENV') or 
        (sys.path and any('/var/task' in p for p in sys.path))
    )
    
    if is_vercel:
        UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    else:
        # 로컬 개발 환경
        UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
