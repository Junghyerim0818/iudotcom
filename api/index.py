import os
from app import create_app

# Vercel 환경 감지
os.environ['VERCEL'] = '1'

app = create_app()