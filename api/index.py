import os
# Vercel 환경 감지 - import 전에 설정해야 함
os.environ['VERCEL'] = '1'

from flask import request, jsonify
from app import create_app

app = create_app()

# Vercel Analytics API 엔드포인트
@app.route('/api/analytics', methods=['POST', 'GET'])
def analytics():
    """Vercel Analytics 데이터 수집 엔드포인트"""
    # Vercel Analytics는 자동으로 이 엔드포인트로 데이터를 전송합니다
    # 실제 처리는 Vercel이 자동으로 수행하므로 여기서는 단순히 200 응답만 반환
    return '', 200