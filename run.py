"""
프로덕션/배포용 실행 스크립트
"""
import os
from index import app

if __name__ == '__main__':
    # 프로덕션 환경 설정
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    #app.run(debug=True, host='127.0.0.1', port=5000)