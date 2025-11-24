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

    # Create DB tables
    with app.app_context():
        db.create_all()
        # 이미지는 이제 DB에 저장되므로 파일 시스템에 폴더를 생성할 필요가 없습니다

    return app

