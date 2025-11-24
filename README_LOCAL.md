# 로컬 개발 환경 설정 가이드

## 1. 가상 환경 설정 (권장)

```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

## 2. 패키지 설치

```bash
pip install -r requirements.txt
```

## 3. 환경 변수 설정

`.env.example` 파일을 참고하여 `.env` 파일을 생성하거나, 환경 변수를 직접 설정하세요.

### 필수 설정 (최소한)
- `SECRET_KEY`: Flask 세션 암호화용 키 (임의의 문자열)
- `GOOGLE_CLIENT_ID`: Google OAuth 클라이언트 ID (선택사항, 로그인 기능 사용 시)
- `GOOGLE_CLIENT_SECRET`: Google OAuth 클라이언트 Secret (선택사항, 로그인 기능 사용 시)

### Google OAuth 설정 방법
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성
3. API 및 서비스 > 사용자 인증 정보
4. OAuth 2.0 클라이언트 ID 생성
5. 승인된 리디렉션 URI에 `http://127.0.0.1:5000/login/callback` 추가

## 4. 애플리케이션 실행

```bash
python run.py
```

브라우저에서 `http://127.0.0.1:5000` 접속

## 5. 데이터베이스

- 로컬 개발 시 SQLite 데이터베이스(`app.db`)가 자동으로 생성됩니다.
- 업로드 폴더(`app/static/uploads`)도 자동으로 생성됩니다.

## 문제 해결

### authlib import 오류
```bash
pip install --upgrade authlib
```

### 포트가 이미 사용 중인 경우
`run.py`에서 포트 번호를 변경하세요:
```python
app.run(debug=True, host='127.0.0.1', port=5001)
```

