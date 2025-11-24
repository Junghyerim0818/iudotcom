"""
Flask Application Entry Point
로컬 개발 및 Vercel 배포 모두에서 사용
"""
import os
from app import create_app

# Vercel 환경 감지
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    # Vercel 환경
    os.environ['VERCEL'] = '1'
else:
    # 로컬 개발 환경에서 HTTPS 요구사항 무시
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Flask 앱 생성
app = create_app()

# Vercel Analytics API 엔드포인트
@app.route('/api/analytics', methods=['POST', 'GET'])
def analytics():
    """Vercel Analytics 데이터 수집 엔드포인트"""
    return '', 200

# Flask main 진입점
if __name__ == '__main__':
    # 로컬 개발 환경에서 Flask 앱 실행
    app.run(debug=True, host='127.0.0.1', port=5000)

