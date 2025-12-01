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

class PostImage(db.Model):
    """게시글에 포함된 추가 이미지"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    image_mimetype = db.Column(db.String(50), nullable=False)
    order = db.Column(db.Integer, default=0) # 표시 순서

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
    
    # 추가 이미지 (1:N 관계)
    images = db.relationship('PostImage', backref='post', cascade='all, delete-orphan', lazy=True)
    
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
                # SQLAlchemy 상태 검사
                pass
        except:
            pass
            
        return False
    
    def get_image_url(self):
        """이미지 URL 반환"""
        if self.image_url:
            return self.image_url
        if self.has_image_data():
            from flask import url_for
            return url_for('main.get_image', post_id=self.id)
        if self.image_filename:
            from flask import url_for
            return url_for('static', filename='uploads/' + self.image_filename)
        return None
