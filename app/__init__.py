import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# authlib OAuth import - 여러 버전 호환성
try:
    from authlib.integrations.flask_client import OAuth
except ImportError:
    try:
        from authlib.flask.client import OAuth
    except ImportError:
        from authlib.client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Create DB tables and upload folder
    with app.app_context():
        db.create_all()
        # 업로드 폴더 생성 (Vercel 환경에서는 /tmp 사용)
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            # Vercel 환경 체크: /var/task로 시작하는 경로는 절대 생성하지 않음
            # /tmp로 시작하는 경로만 생성 시도
            if upload_folder.startswith('/var/task'):
                # Vercel 환경에서 잘못된 경로가 설정된 경우 /tmp로 변경
                upload_folder = os.path.join('/tmp', 'uploads')
                app.config['UPLOAD_FOLDER'] = upload_folder
            
            try:
                # /tmp로 시작하는 경로만 생성 시도
                if upload_folder.startswith('/tmp'):
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder, exist_ok=True)
                    # 프로필 폴더 생성
                    profile_folder = os.path.join(upload_folder, 'profiles')
                    if not os.path.exists(profile_folder):
                        os.makedirs(profile_folder, exist_ok=True)
                elif not upload_folder.startswith('/var') and not upload_folder.startswith('/usr'):
                    # 로컬 개발 환경에서만 폴더 생성
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder, exist_ok=True)
                    profile_folder = os.path.join(upload_folder, 'profiles')
                    if not os.path.exists(profile_folder):
                        os.makedirs(profile_folder, exist_ok=True)
            except (OSError, PermissionError) as e:
                # Vercel 환경에서 폴더 생성 실패 시 무시 (외부 스토리지 사용 권장)
                # 로그만 출력하고 계속 진행
                pass

    return app

