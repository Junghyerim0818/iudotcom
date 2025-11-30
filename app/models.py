from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import Index
from . import db
import re

class Setting(db.Model):
    """애플리케이션 설정 저장"""
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get(key, default=None):
        """설정 값 가져오기"""
        setting = Setting.query.get(key)
        return setting.value if setting else default
    
    @staticmethod
    def set(key, value):
        """설정 값 저장"""
        setting = Setting.query.get(key)
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting

class User(UserMixin, db.Model):
    id = db.Column(db.String(100), primary_key=True) # Google ID
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100))
    profile_pic = db.Column(db.String(200))
    role = db.Column(db.String(20), default='user') # 'user', 'writer', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_admin(self):
        return self.role == 'admin'
    
    def is_writer(self):
        return self.role in ['writer', 'admin']

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text)
    image_filename = db.Column(db.String(100), nullable=True) # For gallery images (deprecated, use image_data)
    image_data = db.Column(db.LargeBinary, nullable=True) # 이미지 바이너리 데이터 (DB에 저장)
    image_mimetype = db.Column(db.String(50), nullable=True) # 이미지 MIME 타입 (예: 'image/jpeg', 'image/png')
    image_url = db.Column(db.String(500), nullable=True) # 외부 이미지 URL (티스토리 등)
    
    # Category: 'gallery', 'archive_tech', 'archive_daily' (example names for the two archive types)
    # User asked for "two types of archive". Let's name them 'archive_1', 'archive_2' for now or allow user to rename.
    # Let's use 'gallery', 'archive_1', 'archive_2'
    category = db.Column(db.String(50), nullable=False, index=True) 
    
    user_id = db.Column(db.String(100), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 티스토리 연동용 필드
    tistory_post_id = db.Column(db.String(100), nullable=True, unique=True) # 티스토리 글 ID (중복 방지)
    tistory_link = db.Column(db.String(500), nullable=True) # 티스토리 원본 링크
    
    # 복합 인덱스 추가 (category와 created_at 조합 쿼리 최적화)
    __table_args__ = (
        Index('idx_category_created_at', 'category', 'created_at'),
    )
    
    # Eager loading을 위한 관계 설정
    author = db.relationship('User', backref=db.backref('posts', lazy='dynamic'))
    
    def has_image_data(self):
        """이미지 데이터가 있는지 안전하게 체크 (이미지 데이터 로드 없이도 체크 가능)"""
        # image_url이 있으면 이미지 있음
        if self.image_url:
            return True
        # image_filename이 있으면 이미지 있음
        if self.image_filename:
            return True
        # image_mimetype이 있으면 이미지 데이터 있음 (로드되지 않았어도 판단 가능)
        if self.image_mimetype:
            return True
        # image_data가 로드된 경우 체크
        try:
            if hasattr(self, 'image_data') and self.image_data is not None:
                try:
                    if len(self.image_data) > 0:
                        return True
                except (TypeError, AttributeError):
                    pass
        except (AttributeError, TypeError):
            pass
        
        # image_data가 로드되지 않았을 경우, DB에서 실제 존재 여부 확인
        # (최적화로 인해 로드되지 않은 경우를 대비 - DB에 직접 추가된 포스트 처리)
        try:
            if hasattr(self, '_sa_instance_state'):
                insp = self._sa_instance_state
                # image_data 컬럼이 있는데 로드되지 않았으면, 실제 DB에서 존재하는지 확인
                if hasattr(insp, 'unloaded') and 'image_data' in insp.unloaded:
                    # 실제 DB 쿼리로 존재 여부만 확인 (데이터는 로드하지 않음)
                    from . import db
                    from sqlalchemy import func
                    count = db.session.query(func.count(Post.id)).filter(
                        Post.id == self.id,
                        Post.image_data.isnot(None)
                    ).scalar()
                    if count and count > 0:
                        return True
        except Exception:
            # 에러가 발생하면 안전하게 False 반환
            pass
        
        return False
    
    def _extract_first_image_from_content(self, content_html):
        """HTML 콘텐츠에서 첫 번째 이미지 URL 추출 (내부 헬퍼 메서드)"""
        if not content_html:
            return None
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content_html, 'html.parser')
            
            # img 태그 찾기
            img_tag = soup.find('img')
            if img_tag and img_tag.get('src'):
                img_url = img_tag.get('src')
                
                # 상대 경로 처리
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    # 절대 경로는 그대로 유지
                    pass
                elif not img_url.startswith('http'):
                    # 상대 경로는 그대로 유지 (브라우저가 처리)
                    pass
                
                return img_url
            
            # background-image 스타일에서 추출 시도
            style_tags = soup.find_all(style=re.compile(r'background-image'))
            for tag in style_tags:
                style = tag.get('style', '')
                match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                if match:
                    img_url = match.group(1)
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    return img_url
        except Exception as e:
            # BeautifulSoup이 없거나 파싱 에러가 발생해도 계속 진행
            import sys
            print(f"Warning: 이미지 추출 중 오류 (무시): {str(e)}", file=sys.stderr)
        
        return None
    
    def get_image_url(self):
        """포스트의 이미지 URL을 반환하는 헬퍼 메서드 (content에서 첫 이미지 추출 우선)"""
        # 1. 외부 이미지 URL이 있으면 우선 사용
        if self.image_url:
            return self.image_url
        
        # 2. DB에 저장된 이미지 데이터 확인 (image_mimetype 또는 실제 image_data 존재)
        has_db_image = False
        if self.image_mimetype:
            has_db_image = True
        elif hasattr(self, 'image_data') and self.image_data is not None:
            try:
                if len(self.image_data) > 0:
                    has_db_image = True
            except (TypeError, AttributeError):
                pass
        else:
            # image_data가 로드되지 않았을 경우, DB에서 실제 존재 여부 확인
            try:
                if hasattr(self, '_sa_instance_state'):
                    insp = self._sa_instance_state
                    if hasattr(insp, 'unloaded') and 'image_data' in insp.unloaded:
                        from . import db
                        from sqlalchemy import func
                        count = db.session.query(func.count(Post.id)).filter(
                            Post.id == self.id,
                            Post.image_data.isnot(None)
                        ).scalar()
                        if count and count > 0:
                            has_db_image = True
            except Exception:
                pass
        
        if has_db_image:
            from flask import url_for
            try:
                return url_for('main.get_image', post_id=self.id)
            except RuntimeError:
                # request context가 없는 경우 (예: 백그라운드 작업)
                return f'/image/{self.id}'
        
        # 3. 파일 시스템에 저장된 이미지 파일이 있으면 static 파일 사용
        if self.image_filename:
            from flask import url_for
            try:
                return url_for('static', filename='uploads/' + self.image_filename)
            except RuntimeError:
                return f'/static/uploads/{self.image_filename}'
        
        # 4. content 영역에서 첫 번째 이미지 추출 (새로운 우선순위)
        # content가 로드되지 않았을 경우 DB에서 가져오기
        content_html = None
        if self.content:
            content_html = self.content
        else:
            # content가 로드되지 않았을 경우 (defer로 인해), DB에서 content만 가져오기
            try:
                if hasattr(self, '_sa_instance_state'):
                    insp = self._sa_instance_state
                    if hasattr(insp, 'unloaded') and 'content' in insp.unloaded:
                        from . import db
                        content_result = db.session.query(Post.content).filter(
                            Post.id == self.id
                        ).scalar()
                        if content_result:
                            content_html = content_result
            except Exception:
                pass
        
        if content_html:
            content_image_url = self._extract_first_image_from_content(content_html)
            if content_image_url:
                return content_image_url
        
        # 이미지가 없는 경우
        return None

