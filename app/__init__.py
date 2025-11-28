import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from config import Config

# authlib OAuth import
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()
cache = Cache()

def create_app(config_class=Config):
    # static과 templates 폴더를 명시적으로 지정 (루트 폴더 기준)
    # app 폴더의 부모 디렉토리(프로젝트 루트)를 기준으로 설정
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__, 
                static_folder=os.path.join(base_dir, 'static'),
                static_url_path='/static',  # static URL 경로 명시
                template_folder=os.path.join(base_dir, 'templates'))
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)
    cache.init_app(app)

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    # 인덱스 생성 (Postgres용)
    with app.app_context():
        try:
            from sqlalchemy import text
            indexes = [
                ("idx_category_created_at", "ON post (category, created_at DESC)"),
                ("idx_post_category", "ON post (category)"),
                ("idx_post_created_at", "ON post (created_at DESC)")
            ]
            for idx_name, idx_def in indexes:
                db.session.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} {idx_def};"))
            db.session.commit()
        except Exception as idx_error:
            db.session.rollback()
            import sys
            print(f"Info: Index creation check: {str(idx_error)}", file=sys.stderr)
    
    # 언어 설정을 템플릿에 전달하는 컨텍스트 프로세서
    @app.context_processor
    def inject_language():
        from flask import session
        # 세션에서 언어 가져오기, 없으면 기본값 'ko' (한국어)
        lang = session.get('language')
        if not lang or lang not in ['ko', 'en']:
            lang = 'ko'  # 기본값: 한국어
            session['language'] = lang
        return dict(current_lang=lang)

    # Create DB tables and add missing columns
    with app.app_context():
        try:
            # 데이터베이스 테이블 생성 시도
            # Vercel 환경에서는 Postgres가 이미 설정되어 있어야 하며,
            # SQLite를 사용하려고 하면 실패할 수 있음
            db.create_all()
            
            # 기존 테이블에 누락된 컬럼 추가 (Postgres용)
            try:
                from sqlalchemy import text
                columns = [
                    ("image_data", "BYTEA"),
                    ("image_mimetype", "VARCHAR(50)"),
                    ("image_url", "VARCHAR(500)"),
                    ("tistory_post_id", "VARCHAR(100)"),
                    ("tistory_link", "VARCHAR(500)")
                ]
                for col_name, col_type in columns:
                    db.session.execute(text(f"""
                        DO $$ 
                        BEGIN 
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name='post' AND column_name='{col_name}'
                            ) THEN
                                ALTER TABLE post ADD COLUMN {col_name} {col_type};
                            END IF;
                        END $$;
                    """))
                # tistory_post_id에 유니크 인덱스 추가
                db.session.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_post_tistory_post_id 
                    ON post (tistory_post_id) 
                    WHERE tistory_post_id IS NOT NULL;
                """))
                db.session.commit()
            except Exception as col_error:
                db.session.rollback()
                import sys
                print(f"Info: Column migration check: {str(col_error)}", file=sys.stderr)
        except Exception as e:
            # 데이터베이스 연결 또는 테이블 생성 실패 시 로깅만 하고 계속 진행
            # (Vercel 환경에서 Postgres가 제대로 설정되지 않은 경우 등)
            import sys
            print(f"Warning: Could not create database tables: {str(e)}", file=sys.stderr)
            # 앱은 계속 실행됨 (테이블이 이미 존재하거나 다른 이유일 수 있음)

    # 티스토리 RSS 자동 동기화 스케줄러 설정
    # 데이터베이스 설정 우선, 없으면 환경 변수 사용
    with app.app_context():
        from .models import Setting
        try:
            # 데이터베이스에서 설정 가져오기
            tistory_auto_sync = Setting.get('TISTORY_AUTO_SYNC_ENABLED', 'false').lower() == 'true'
            tistory_rss_url = Setting.get('TISTORY_RSS_URL') or app.config.get('TISTORY_RSS_URL')
            
            # 환경 변수도 확인
            if not tistory_auto_sync:
                tistory_auto_sync = app.config.get('TISTORY_AUTO_SYNC_ENABLED', False)
            if not tistory_rss_url:
                tistory_rss_url = app.config.get('TISTORY_RSS_URL')
            
            if tistory_auto_sync and tistory_rss_url:
                try:
                    from apscheduler.schedulers.background import BackgroundScheduler
                    from apscheduler.triggers.interval import IntervalTrigger
                    from .tistory_sync import sync_tistory_posts
                    
                    scheduler = BackgroundScheduler()
                    scheduler.start()
                    
                    default_category = Setting.get('TISTORY_DEFAULT_CATEGORY') or app.config.get('TISTORY_DEFAULT_CATEGORY', 'gallery')
                    author_id = Setting.get('TISTORY_AUTO_AUTHOR_ID') or app.config.get('TISTORY_AUTO_AUTHOR_ID')
                    interval_minutes = int(Setting.get('TISTORY_SYNC_INTERVAL') or app.config.get('TISTORY_SYNC_INTERVAL', 15))
                    
                    # 주기적 동기화 작업 추가
                    scheduler.add_job(
                        func=sync_tistory_posts,
                        trigger=IntervalTrigger(minutes=interval_minutes),
                        args=[app, tistory_rss_url, default_category, author_id],
                        id='tistory_sync',
                        name='티스토리 RSS 동기화',
                        replace_existing=True
                    )
                    
                    # 앱 종료 시 스케줄러 종료
                    import atexit
                    atexit.register(lambda: scheduler.shutdown())
                    
                    app.logger.info(f"티스토리 RSS 자동 동기화가 활성화되었습니다. (간격: {interval_minutes}분)")
                except Exception as e:
                    import sys
                    print(f"Warning: 티스토리 스케줄러 설정 실패: {str(e)}", file=sys.stderr)
                    app.logger.warning(f"티스토리 스케줄러 설정 실패: {str(e)}")
        except Exception as e:
            # Setting 테이블이 아직 생성되지 않았을 수 있음 (첫 실행)
            app.logger.debug(f"Setting 테이블 확인 중 오류 (무시 가능): {str(e)}")

    return app

