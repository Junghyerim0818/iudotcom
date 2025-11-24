"""
Vercel Serverless Function Entry Point
Vercel은 이 파일에서 'app'이라는 전역 변수를 찾습니다.
"""
import os
import sys

# Vercel 환경 감지 - import 전에 설정해야 함
os.environ['VERCEL'] = '1'

try:
    # Flask와 앱 생성 함수 import
    from flask import Flask, request, jsonify
    from app import create_app
    
    # Flask 앱 생성 - 반드시 'app'이라는 이름으로 생성해야 합니다
    # Vercel은 이 변수를 자동으로 감지합니다
    app = create_app()
    
    # Vercel Analytics API 엔드포인트 (선택사항)
    @app.route('/api/analytics', methods=['POST', 'GET'])
    def analytics():
        """Vercel Analytics 데이터 수집 엔드포인트"""
        return '', 200
    
    # 디버깅: 앱이 제대로 생성되었는지 확인
    if app is None:
        print("ERROR: app is None", file=sys.stderr)
    else:
        print(f"SUCCESS: Flask app created: {type(app)}", file=sys.stderr)
        
except Exception as e:
    # 에러 발생 시 로깅 - Vercel 로그에서 확인 가능
    error_msg = f"ERROR creating Flask app: {type(e).__name__}: {str(e)}"
    print(error_msg, file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    
    # 최소한의 Flask 앱을 생성하여 Vercel이 인식할 수 있도록 함
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        return f"Application Error: {error_msg}", 500
    
    # 원래 에러는 다시 raise하지 않고 로깅만 함
    # (이렇게 하면 Vercel이 Flask 앱을 찾을 수 있음)