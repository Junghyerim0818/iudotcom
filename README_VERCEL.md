# Vercel 배포 가이드

## 환경 변수 설정

Vercel 대시보드에서 다음 환경 변수를 설정하세요:

### 필수 환경 변수
- `SECRET_KEY`: Flask 세션 암호화용 키 (임의의 긴 문자열)
- `POSTGRES_URL` 또는 `DATABASE_URL`: Neon 데이터베이스 연결 문자열

### Google OAuth (선택사항)
- `GOOGLE_CLIENT_ID`: Google OAuth 클라이언트 ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth 클라이언트 Secret

## Vercel Analytics

Vercel Analytics는 자동으로 활성화됩니다. Vercel 대시보드에서 Analytics를 활성화하면 자동으로 수집됩니다.

## 이미지 저장 주의사항

⚠️ **중요**: Vercel은 서버리스 환경이므로 로컬 파일 시스템에 이미지를 저장하면:
- 배포 시 파일이 사라질 수 있습니다
- 함수 실행 간 파일이 유지되지 않을 수 있습니다

### 권장 해결 방법

1. **Vercel Blob Storage** 사용 (권장)
2. **Cloudinary** 사용
3. **AWS S3** 사용
4. **Base64 인코딩** 후 DB에 저장 (작은 이미지에만 적합)

현재는 `/tmp` 디렉토리를 사용하지만, 프로덕션에서는 외부 스토리지 사용을 강력히 권장합니다.

## 배포 방법

1. GitHub에 코드 푸시
2. Vercel 대시보드에서 프로젝트 import
3. 환경 변수 설정
4. 배포 완료!

## 로컬 개발

로컬 개발 시에는 `run.py`를 사용하세요:
```bash
python run.py
```

