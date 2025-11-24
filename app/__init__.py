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
            try:
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                # 프로필 폴더 생성
                profile_folder = os.path.join(upload_folder, 'profiles')
                if not os.path.exists(profile_folder):
                    os.makedirs(profile_folder)
            except (OSError, PermissionError) as e:
                # Vercel 환경에서 폴더 생성 실패 시 무시 (외부 스토리지 사용 권장)
                print(f"Warning: Could not create upload folder: {e}")

    return app

