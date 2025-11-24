import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# authlib OAuth import
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()

def create_app(config_class=Config):
    # static과 templates 폴더를 명시적으로 지정 (app 폴더 기준)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, 
                static_folder=os.path.join(base_dir, 'static'),
                static_url_path='/static',  # static URL 경로 명시
                template_folder=os.path.join(base_dir, 'templates'))
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
        try:
            # 데이터베이스 테이블 생성 시도
            # Vercel 환경에서는 Postgres가 이미 설정되어 있어야 하며,
            # SQLite를 사용하려고 하면 실패할 수 있음
            db.create_all()
        except Exception as e:
            # 데이터베이스 연결 또는 테이블 생성 실패 시 로깅만 하고 계속 진행
            # (Vercel 환경에서 Postgres가 제대로 설정되지 않은 경우 등)
            import sys
            print(f"Warning: Could not create database tables: {str(e)}", file=sys.stderr)
            # 앱은 계속 실행됨 (테이블이 이미 존재하거나 다른 이유일 수 있음)

    return app

