// 페이지 이동 속도 최적화
document.addEventListener('DOMContentLoaded', function() {
    // 모든 내부 링크에 즉시 이동 처리
    const links = document.querySelectorAll('a[href^="/"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            // 모달이나 외부 링크는 제외
            if (this.getAttribute('data-bs-toggle') || 
                this.getAttribute('target') === '_blank' ||
                (this.href && this.href.startsWith('http') && !this.href.includes(window.location.hostname))) {
                return;
            }
            
            // 즉시 페이지 이동 (애니메이션 없이)
            const href = this.getAttribute('href');
            if (href && href !== '#' && !href.includes('javascript:') && href.startsWith('/')) {
                // 즉시 이동
                window.location.href = href;
            }
        });
    });
});

// 사이드바 및 모바일 메뉴 관리
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const mobileOverlay = document.getElementById('mobileOverlay');
    
    // 데스크톱에서는 항상 펼쳐진 상태
    if (window.innerWidth > 768) {
        if (sidebar) {
            sidebar.classList.add('expanded');
        }
    }
    
    // 모바일 메뉴 토글
    if (mobileMenuToggle && mobileOverlay) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('mobile-open');
            mobileOverlay.classList.toggle('active');
            
            // 아이콘 변경
            const icon = this.querySelector('i');
            if (sidebar.classList.contains('mobile-open')) {
                icon.classList.remove('bi-list');
                icon.classList.add('bi-x-lg');
            } else {
                icon.classList.remove('bi-x-lg');
                icon.classList.add('bi-list');
            }
        });
        
        // 오버레이 클릭 시 메뉴 닫기
        mobileOverlay.addEventListener('click', function() {
            sidebar.classList.remove('mobile-open');
            mobileOverlay.classList.remove('active');
            
            const icon = mobileMenuToggle.querySelector('i');
            if (icon) {
                icon.classList.remove('bi-x-lg');
                icon.classList.add('bi-list');
            }
        });
        
        // 메뉴 링크 클릭 시 메뉴 닫기
        const menuLinks = sidebar.querySelectorAll('.sidebar-menu-link');
        menuLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('mobile-open');
                    mobileOverlay.classList.remove('active');
                    
                    const icon = mobileMenuToggle.querySelector('i');
                    if (icon) {
                        icon.classList.remove('bi-x-lg');
                        icon.classList.add('bi-list');
                    }
                }
            });
        });
    }

    // 로그인 모달에서 Google 로그인 버튼 클릭 시 팝업 열기
    const googleLoginBtn = document.getElementById('googleLoginBtn');
    if (googleLoginBtn) {
        // 기본 링크 동작 방지
        googleLoginBtn.setAttribute('href', 'javascript:void(0)');
        
        googleLoginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            // 실제 로그인 URL 가져오기
            const actualLoginUrl = this.getAttribute('data-login-url') || '/login';
            const popup = window.open(actualLoginUrl, 'GoogleLogin', 'width=500,height=600,scrollbars=yes,resizable=yes');
            
            if (!popup) {
                alert('팝업이 차단되었습니다. 팝업 차단을 해제해주세요.');
                return;
            }
            
            // 팝업에서 로그인 완료 메시지 수신
            const messageHandler = function(event) {
                if (event.data && event.data.type === 'login') {
                    if (event.data.success) {
                        // 로그인 성공 시 모달 닫고 페이지 새로고침
                        const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                        if (modal) modal.hide();
                        window.removeEventListener('message', messageHandler);
                        window.location.reload();
                    } else {
                        alert(event.data.message || '로그인에 실패했습니다.');
                    }
                }
            };
            window.addEventListener('message', messageHandler);
            
            // 팝업이 닫혔는지 확인
            const checkInterval = setInterval(function() {
                if (popup.closed) {
                    clearInterval(checkInterval);
                    window.removeEventListener('message', messageHandler);
                }
            }, 500);
        });
    }

    // 글쓰기 모달이 열릴 때 폼 로드
    const newPostModal = document.getElementById('newPostModal');
    if (newPostModal) {
        newPostModal.addEventListener('show.bs.modal', function() {
            const modalBody = document.getElementById('newPostModalBody');
            // 폼 HTML 가져오기 (URL은 템플릿에서 전달받음)
            const postFormUrl = newPostModal.dataset.formUrl || '/post/new';
            fetch(postFormUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.text())
            .then(html => {
                // 폼 부분만 추출
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const form = doc.querySelector('form');
                if (form) {
                    modalBody.innerHTML = form.outerHTML;
                    // 폼 제출 이벤트 리스너 추가
                    const newPostForm = document.getElementById('newPostForm');
                    if (newPostForm) {
                        newPostForm.addEventListener('submit', function(e) {
                            e.preventDefault();
                            const formData = new FormData(this);
                            
                            fetch(this.action, {
                                method: 'POST',
                                body: formData,
                                headers: {
                                    'X-Requested-With': 'XMLHttpRequest'
                                }
                            })
                            .then(response => {
                                if (response.redirected) {
                                    window.location.href = response.url;
                                } else {
                                    return response.json().then(data => {
                                        if (data.success) {
                                            // 성공 시 모달 닫고 페이지 새로고침
                                            const modal = bootstrap.Modal.getInstance(newPostModal);
                                            modal.hide();
                                            window.location.reload();
                                        } else {
                                            alert(data.message || '글 작성에 실패했습니다.');
                                        }
                                    });
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                // 폼 제출 실패 시 일반 폼 제출로 폴백
                                this.submit();
                            });
                        });
                    }
                } else {
                    modalBody.innerHTML = '<div class="alert alert-danger">폼을 불러올 수 없습니다.</div>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                modalBody.innerHTML = '<div class="alert alert-danger">오류가 발생했습니다.</div>';
            });
        });
    }
    
    // 글 수정 모달 처리
    const editPostModal = document.getElementById('editPostModal');
    if (editPostModal) {
        editPostModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const postId = button.getAttribute('data-post-id');
            const modalBody = document.getElementById('editPostModalBody');
            
            if (postId) {
                fetch(`/post/${postId}/edit`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const form = doc.querySelector('form');
                    if (form) {
                        modalBody.innerHTML = form.outerHTML;
                        // 폼 제출 이벤트 리스너 추가
                        const editPostForm = document.getElementById('editPostForm');
                        if (editPostForm) {
                            editPostForm.addEventListener('submit', function(e) {
                                e.preventDefault();
                                const formData = new FormData(this);
                                
                                fetch(this.action, {
                                    method: 'POST',
                                    body: formData,
                                    headers: {
                                        'X-Requested-With': 'XMLHttpRequest'
                                    }
                                })
                                .then(response => {
                                    if (response.redirected) {
                                        window.location.href = response.url;
                                    } else {
                                        return response.text().then(html => {
                                            // 성공 시 모달 닫고 페이지 새로고침
                                            const modal = bootstrap.Modal.getInstance(editPostModal);
                                            modal.hide();
                                            window.location.reload();
                                        });
                                    }
                                })
                                .catch(error => {
                                    console.error('Error:', error);
                                    this.submit();
                                });
                            });
                        }
                    } else {
                        modalBody.innerHTML = '<div class="alert alert-danger">폼을 불러올 수 없습니다.</div>';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    modalBody.innerHTML = '<div class="alert alert-danger">폼을 불러올 수 없습니다.</div>';
                });
            }
        });
    }
    
    // 갤러리 카드 슬라이더 기능
    const gallerySliderWrapper = document.getElementById('gallerySliderWrapper');
    const gallerySliderTrack = document.getElementById('gallerySliderTrack');
    const gallerySliderPrev = document.getElementById('gallerySliderPrev');
    const gallerySliderNext = document.getElementById('gallerySliderNext');
    const galleryHomeBtn = document.getElementById('galleryHomeBtn');
    
    let currentIndex = 0;
    let cardItems = [];
    
    if (gallerySliderWrapper && gallerySliderTrack) {
        cardItems = gallerySliderTrack.querySelectorAll('.gallery-card-item');
        
        // 배경 이미지 설정
        cardItems.forEach((card) => {
            const bgElement = card.querySelector('.gallery-card-background[data-bg-image]');
            if (bgElement) {
                const imageUrl = bgElement.getAttribute('data-bg-image');
                bgElement.style.backgroundImage = `url('${imageUrl}')`;
            }
        });
        
        // 카드 클릭 이벤트 리스너 추가 (Stack Overflow 예제처럼 중앙으로 이동)
        cardItems.forEach((card, index) => {
            const cardLink = card.querySelector('.gallery-card-link');
            if (cardLink) {
                cardLink.addEventListener('click', function(e) {
                    // 이미 중앙에 있는 카드면 상세 페이지로 이동
                    if (currentIndex === index && card.classList.contains('active')) {
                        return; // 기본 링크 동작 허용
                    }
                    
                    // 중앙에 없는 카드면 중앙으로 이동
                    e.preventDefault();
                    const cardIndex = parseInt(this.getAttribute('data-card-index') || index);
                    currentIndex = cardIndex;
                    scrollToCard(cardIndex);
                    updateActiveCard(cardIndex);
                });
            }
        });
        
        // 카드 너비 계산 (반응형 대응)
        function getCardWidth() {
            if (cardItems.length > 0) {
                const firstCard = cardItems[0];
                const cardStyle = window.getComputedStyle(firstCard);
                const cardWidth = parseInt(cardStyle.width);
                const gap = parseInt(window.getComputedStyle(gallerySliderTrack).gap) || 32;
                return { width: cardWidth, gap: gap };
            }
            return { width: 380, gap: 32 }; // 기본값
        }
        
        // 이전 버튼
        if (gallerySliderPrev) {
            gallerySliderPrev.addEventListener('click', function() {
                if (currentIndex > 0) {
                    currentIndex--;
                    scrollToCard(currentIndex);
                }
            });
        }
        
        // 다음 버튼
        if (gallerySliderNext) {
            gallerySliderNext.addEventListener('click', function() {
                if (currentIndex < cardItems.length - 1) {
                    currentIndex++;
                    scrollToCard(currentIndex);
                }
            });
        }
        
        // 홈 버튼 (첫 번째 카드로 이동)
        if (galleryHomeBtn) {
            galleryHomeBtn.addEventListener('click', function() {
                currentIndex = 0;
                scrollToCard(0);
            });
        }
        
        // 활성 카드 업데이트
        function updateActiveCard(index) {
            cardItems.forEach((card, i) => {
                if (i === index) {
                    card.classList.add('active');
                } else {
                    card.classList.remove('active');
                }
            });
        }
        
        // 카드로 스크롤하는 함수 (클릭한 카드가 중앙에 오도록)
        function scrollToCard(index) {
            if (cardItems[index]) {
                const card = cardItems[index];
                const wrapperWidth = gallerySliderWrapper.offsetWidth;
                const cardDimensions = getCardWidth();
                
                // 카드의 중앙을 화면 중앙에 맞춤
                const cardLeft = card.offsetLeft;
                const cardCenter = cardLeft + cardDimensions.width / 2;
                const wrapperCenter = wrapperWidth / 2;
                const scrollPosition = cardCenter - wrapperCenter;
                
                gallerySliderWrapper.scrollTo({
                    left: Math.max(0, scrollPosition),
                    behavior: 'smooth'
                });
                
                // 활성 카드 업데이트
                updateActiveCard(index);
            }
        }
        
        // 스크롤 이벤트로 현재 인덱스 업데이트
        let scrollTimeout;
        gallerySliderWrapper.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(function() {
                updateCurrentIndex();
            }, 100);
        });
        
        function updateCurrentIndex() {
            const scrollLeft = gallerySliderWrapper.scrollLeft;
            const wrapperWidth = gallerySliderWrapper.offsetWidth;
            const centerPoint = scrollLeft + wrapperWidth / 2;
            const cardDimensions = getCardWidth();
            
            let closestIndex = 0;
            let closestDistance = Infinity;
            
            cardItems.forEach((card, index) => {
                const cardLeft = card.offsetLeft;
                const cardCenter = cardLeft + cardDimensions.width / 2;
                const distance = Math.abs(centerPoint - cardCenter);
                
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closestIndex = index;
                }
            });
            
            if (currentIndex !== closestIndex) {
                currentIndex = closestIndex;
                updateActiveCard(currentIndex);
            }
        }
        
        // 휠 이벤트로 가로 스크롤 (선택사항)
        gallerySliderWrapper.addEventListener('wheel', function(e) {
            if (e.deltaY !== 0) {
                e.preventDefault();
                gallerySliderWrapper.scrollLeft += e.deltaY;
            }
        }, { passive: false });
        
        // 초기 인덱스 설정
        updateCurrentIndex();
        updateActiveCard(0); // 첫 번째 카드를 활성화
    }
});

