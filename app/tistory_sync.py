"""
티스토리 RSS 피드 자동 동기화 모듈
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger(__name__)


def extract_image_from_content(content_html):
    """HTML 콘텐츠에서 첫 번째 이미지 URL 추출 (티스토리 이미지 URL 처리 포함)"""
    if not content_html:
        return None
    
    try:
        from urllib.parse import unquote, urlparse, parse_qs
        
        soup = BeautifulSoup(content_html, 'html.parser')
        # img 태그 찾기
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            img_url = img_tag.get('src')
            
            # 티스토리 이미지 URL 처리 (daumcdn.net 링크)
            if 'daumcdn.net' in img_url and 'fname=' in img_url:
                try:
                    # fname 파라미터 추출
                    parsed = urlparse(img_url)
                    params = parse_qs(parsed.query)
                    if 'fname' in params and params['fname']:
                        # URL 디코딩: %3A → :, %2F → /, %3F → ?, %26 → &, %253D → =
                        encoded_url = params['fname'][0]
                        # URL 디코딩 (여러 번 디코딩 필요할 수 있음)
                        decoded_url = unquote(encoded_url)
                        # 한 번 더 디코딩 (이중 인코딩된 경우)
                        if '%' in decoded_url:
                            decoded_url = unquote(decoded_url)
                        img_url = decoded_url
                        logger.info(f"티스토리 이미지 URL 변환: {decoded_url}")
                except Exception as e:
                    logger.warning(f"티스토리 이미지 URL 변환 실패, 원본 사용: {str(e)}")
            
            # 상대 경로를 절대 경로로 변환
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                # 티스토리 도메인 추출 필요 시 추가 처리
                pass
            
            return img_url
        
        # background-image 스타일에서 추출 시도
        style_tags = soup.find_all(style=re.compile(r'background-image'))
        for tag in style_tags:
            style = tag.get('style', '')
            match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
            if match:
                img_url = match.group(1)
                
                # 티스토리 이미지 URL 처리
                if 'daumcdn.net' in img_url and 'fname=' in img_url:
                    try:
                        from urllib.parse import unquote, urlparse, parse_qs
                        parsed = urlparse(img_url)
                        params = parse_qs(parsed.query)
                        if 'fname' in params and params['fname']:
                            encoded_url = params['fname'][0]
                            decoded_url = unquote(encoded_url)
                            if '%' in decoded_url:
                                decoded_url = unquote(decoded_url)
                            img_url = decoded_url
                            logger.info(f"티스토리 이미지 URL 변환 (스타일): {decoded_url}")
                    except Exception as e:
                        logger.warning(f"티스토리 이미지 URL 변환 실패: {str(e)}")
                
                return img_url
    except Exception as e:
        logger.error(f"이미지 추출 중 오류: {str(e)}")
    
    return None


def parse_tistory_rss(rss_url):
    """티스토리 RSS 피드 파싱"""
    try:
        feed = feedparser.parse(rss_url)
        
        if feed.bozo and feed.bozo_exception:
            logger.error(f"RSS 파싱 오류: {feed.bozo_exception}")
            return []
        
        posts = []
        for entry in feed.entries:
            # 티스토리 글 ID 추출 (링크에서)
            link = entry.get('link', '')
            post_id_match = re.search(r'/(\d+)(?:[/?#]|$)', link)
            tistory_post_id = post_id_match.group(1) if post_id_match else None
            
            # 날짜 파싱
            published_time = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_time = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_time = datetime(*entry.updated_parsed[:6])
            
            # 콘텐츠 추출
            content = entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
            if not content:
                content = entry.get('summary', '')
            
            # 이미지 URL 추출
            image_url = extract_image_from_content(content)
            
            post_data = {
                'tistory_post_id': tistory_post_id,
                'title': entry.get('title', '제목 없음'),
                'content': content,
                'link': link,
                'image_url': image_url,
                'published_time': published_time or datetime.utcnow()
            }
            
            posts.append(post_data)
        
        return posts
    except Exception as e:
        logger.error(f"RSS 피드 파싱 중 오류: {str(e)}")
        return []


def sync_tistory_posts(app, rss_url, default_category='gallery', author_id=None):
    """티스토리 RSS에서 새 글을 가져와서 Post로 생성"""
    with app.app_context():
        from .models import Post, User
        from . import db, cache
        
        try:
            # RSS 피드 파싱
            tistory_posts = parse_tistory_rss(rss_url)
            
            if not tistory_posts:
                logger.info("티스토리 RSS에서 새 글이 없습니다.")
                return
            
            # 작성자 찾기
            author = None
            if author_id:
                author = User.query.get(author_id)
            
            if not author:
                # 관리자 중 첫 번째 사용자 찾기
                author = User.query.filter_by(role='admin').first()
            
            if not author:
                logger.error("티스토리 동기화를 위한 작성자를 찾을 수 없습니다.")
                return
            
            new_posts_count = 0
            
            for tistory_post in tistory_posts:
                # 이미 가져온 글인지 확인
                if tistory_post['tistory_post_id']:
                    existing = Post.query.filter_by(
                        tistory_post_id=tistory_post['tistory_post_id']
                    ).first()
                    if existing:
                        continue
                
                # 제목으로도 중복 체크 (티스토리 ID가 없는 경우)
                if not tistory_post['tistory_post_id']:
                    existing = Post.query.filter_by(
                        title=tistory_post['title'],
                        tistory_link=tistory_post['link']
                    ).first()
                    if existing:
                        continue
                
                # 새 Post 생성
                post = Post(
                    title=tistory_post['title'][:100],  # 제목 길이 제한
                    content=tistory_post['content'],
                    category=default_category,
                    image_url=tistory_post['image_url'],
                    image_data=None,
                    image_mimetype=None,
                    author=author,
                    tistory_post_id=tistory_post['tistory_post_id'],
                    tistory_link=tistory_post['link'],
                    created_at=tistory_post['published_time']
                )
                
                db.session.add(post)
                new_posts_count += 1
                logger.info(f"새 티스토리 글 추가: {tistory_post['title']}")
            
            if new_posts_count > 0:
                db.session.commit()
                
                # 캐시 무효화
                cache.delete('index_gallery_posts')
                for i in range(1, 11):
                    cache.delete(f'gallery_posts_page_{i}')
                    cache.delete(f'archive_archive_1_page_{i}')
                    cache.delete(f'archive_archive_2_page_{i}')
                
                logger.info(f"티스토리 동기화 완료: {new_posts_count}개의 새 글이 추가되었습니다.")
            else:
                logger.info("티스토리 동기화 완료: 새 글이 없습니다.")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"티스토리 동기화 중 오류: {str(e)}", exc_info=True)

