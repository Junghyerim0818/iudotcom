"""
로컬 개발용 실행 스크립트
"""
import os

# 로컬 개발 환경에서 HTTPS 요구사항 무시
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# index.py의 app을 import하여 사용
from index import app

if __name__ == '__main__':
    # 로컬 개발용 설정
    app.run(debug=True, host='0.0.0.0', port=80)
