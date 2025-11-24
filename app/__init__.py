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
            # Vercel 환경 체크: /var/task가 포함된 경로나 /var, /usr로 시작하는 경로는 절대 생성하지 않음
            # 즉시 /tmp로 변경 (가장 먼저 체크)
            needs_redirect = (
                '/var/task' in upload_folder or 
                upload_folder.startswith('/var') or 
                upload_folder.startswith('/usr')
            )
            
            if needs_redirect:
                upload_folder = os.path.join('/tmp', 'uploads')
                app.config['UPLOAD_FOLDER'] = upload_folder
            
            # os.makedirs 호출 전 최종 검증: /var 또는 /usr로 시작하거나 /var/task를 포함하면 절대 생성하지 않음
            # 경로의 모든 부분을 검사하여 안전성 확인
            path_parts = upload_folder.split(os.sep)
            is_safe_path = (
                not upload_folder.startswith('/var') and 
                not upload_folder.startswith('/usr') and 
                '/var/task' not in upload_folder and
                '/var' not in path_parts and
                '/usr' not in path_parts
            )
            
            if is_safe_path:
                # /tmp로 시작하는 경로만 생성 시도
                if upload_folder.startswith('/tmp'):
                    try:
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder, exist_ok=True)
                        # 프로필 폴더 생성
                        profile_folder = os.path.join(upload_folder, 'profiles')
                        if not os.path.exists(profile_folder):
                            os.makedirs(profile_folder, exist_ok=True)
                    except (OSError, PermissionError):
                        # Vercel 환경에서 폴더 생성 실패 시 무시 (외부 스토리지 사용 권장)
                        pass
                else:
                    # 로컬 개발 환경에서만 폴더 생성
                    # 경로에 /var/task가 포함되어 있는지 다시 한 번 확인
                    try:
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder, exist_ok=True)
                        profile_folder = os.path.join(upload_folder, 'profiles')
                        if not os.path.exists(profile_folder):
                            os.makedirs(profile_folder, exist_ok=True)
                    except (OSError, PermissionError):
                        pass
            # is_safe_path가 False이면 디렉토리 생성을 시도하지 않음 (Vercel 환경)

    return app

