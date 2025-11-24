import os
from app import create_app

# 로컬 개발 환경에서 HTTPS 요구사항 무시 (배포 시 제거해야 함)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = create_app()

if __name__ == '__main__':
    # 로컬 개발용 설정
    app.run(debug=True, host='127.0.0.1', port=5000)
