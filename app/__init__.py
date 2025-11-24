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
            # 안전한 디렉토리 생성 함수
            def safe_makedirs(path):
                """안전하게 디렉토리 생성 - /var/task 경로는 절대 생성하지 않음"""
                # 절대 경로로 변환하여 확인
                try:
                    abs_path = os.path.abspath(path)
                    # /var/task가 포함되어 있거나 /var, /usr로 시작하면 생성하지 않음
                    if '/var/task' in abs_path or '/var/task' in path:
                        return False
                    if abs_path.startswith('/var') or abs_path.startswith('/usr'):
                        return False
                    if path.startswith('/var') or path.startswith('/usr'):
                        return False
                except:
                    # 경로 변환 실패 시 안전하게 처리
                    if '/var/task' in path or path.startswith('/var') or path.startswith('/usr'):
                        return False
                
                # 안전한 경로만 생성 시도
                try:
                    if not os.path.exists(path):
                        os.makedirs(path, exist_ok=True)
                    return True
                except (OSError, PermissionError):
                    # 생성 실패 시 무시
                    return False
            
            # 먼저 경로를 검증하고 필요하면 /tmp로 변경
            original_folder = upload_folder
            try:
                abs_original = os.path.abspath(original_folder)
                if '/var/task' in abs_original or '/var/task' in original_folder:
                    upload_folder = os.path.join('/tmp', 'uploads')
                    app.config['UPLOAD_FOLDER'] = upload_folder
                elif abs_original.startswith('/var') or abs_original.startswith('/usr'):
                    upload_folder = os.path.join('/tmp', 'uploads')
                    app.config['UPLOAD_FOLDER'] = upload_folder
                elif original_folder.startswith('/var') or original_folder.startswith('/usr'):
                    upload_folder = os.path.join('/tmp', 'uploads')
                    app.config['UPLOAD_FOLDER'] = upload_folder
            except:
                # 경로 변환 실패 시 안전하게 /tmp 사용
                upload_folder = os.path.join('/tmp', 'uploads')
                app.config['UPLOAD_FOLDER'] = upload_folder
            
            # 안전한 경로인 경우에만 디렉토리 생성 시도
            if safe_makedirs(upload_folder):
                # 프로필 폴더도 생성
                profile_folder = os.path.join(upload_folder, 'profiles')
                safe_makedirs(profile_folder)

    return app

