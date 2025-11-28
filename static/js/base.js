// 모든 초기화 코드를 하나의 DOMContentLoaded로 통합
document.addEventListener('DOMContentLoaded', function() {
    // 언어 선택 드롭다운 처리
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
        languageSelect.addEventListener('change', function(e) {
            const langCode = this.value;
            if (langCode && (langCode === 'ko' || langCode === 'en')) {
                window.location.href = '/lang/' + langCode;
            }
        });
    }
    
    // 활성 메뉴 배경 사각형 위치 업데이트
    function updateActiveMenuBackground(skipTransition = false, targetLeft = null, targetWidth = null) {
        const topMenu = document.querySelector('.top-menu');
        const activeLink = document.querySelector('.top-menu-link.active');
        
        if (topMenu) {
            let left, width;
            
            if (targetLeft !== null && targetWidth !== null) {
                // 저장된 위치 사용
                left = targetLeft;
                width = targetWidth;
            } else if (activeLink) {
                // 활성 메뉴 위치 계산
                const menuRect = topMenu.getBoundingClientRect();
                const linkRect = activeLink.getBoundingClientRect();
                left = linkRect.left - menuRect.left;
                width = linkRect.width;
            } else {
                // 활성 메뉴가 없으면 숨김
                topMenu.style.setProperty('--active-menu-left', '0px');
                topMenu.style.setProperty('--active-menu-width', '0px');
                topMenu.classList.remove('menu-initialized');
                return;
            }
            
            if (skipTransition) {
                // 초기 로드 시 transition 일시적으로 비활성화하고 위치 설정
                topMenu.style.setProperty('--active-menu-left', left + 'px');
                topMenu.style.setProperty('--active-menu-width', width + 'px');
                // 다음 프레임에서 transition 활성화 및 표시
                requestAnimationFrame(() => {
                    topMenu.classList.add('menu-initialized');
                });
            } else {
                // 메뉴 변경 시 부드럽게 이동
                // 먼저 위치를 설정하고, 그 다음 transition 활성화
                topMenu.style.setProperty('--active-menu-left', left + 'px');
                topMenu.style.setProperty('--active-menu-width', width + 'px');
                // transition이 활성화되도록 클래스 추가
                if (!topMenu.classList.contains('menu-initialized')) {
                    topMenu.classList.add('menu-initialized');
                }
            }
        }
    }
    
    // 페이지 전환 시 저장된 위치 확인
    const savedLeft = sessionStorage.getItem('menu-background-left');
    const savedWidth = sessionStorage.getItem('menu-background-width');
    
    if (savedLeft && savedWidth) {
        // 저장된 위치에서 시작 (transition 없이)
        const savedLeftNum = parseFloat(savedLeft);
        const savedWidthNum = parseFloat(savedWidth);
        updateActiveMenuBackground(true, savedLeftNum, savedWidthNum);
        
        // sessionStorage 정리
        sessionStorage.removeItem('menu-background-left');
        sessionStorage.removeItem('menu-background-width');
        
        // 올바른 활성 메뉴 위치 확인
        const topMenu = document.querySelector('.top-menu');
        const activeLink = document.querySelector('.top-menu-link.active');
        
        if (topMenu && activeLink) {
            const menuRect = topMenu.getBoundingClientRect();
            const linkRect = activeLink.getBoundingClientRect();
            const correctLeft = linkRect.left - menuRect.left;
            const correctWidth = linkRect.width;
            
            // 저장된 위치와 올바른 위치가 다르면 이동
            if (Math.abs(savedLeftNum - correctLeft) > 1 || Math.abs(savedWidthNum - correctWidth) > 1) {
                // 다음 프레임에서 올바른 위치로 이동 (transition 있이)
                requestAnimationFrame(() => {
                    setTimeout(() => {
                        updateActiveMenuBackground(false);
                    }, 50);
                });
            } else {
                // 위치가 같으면 transition만 활성화
                requestAnimationFrame(() => {
                    topMenu.classList.add('menu-initialized');
                });
            }
        }
    } else {
        // 초기 위치 설정 (transition 없이)
        updateActiveMenuBackground(true);
    }
    
    // 리사이즈 시 위치 업데이트
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            updateActiveMenuBackground(false);
        }, 100);
    });
    
    // 메뉴 링크 클릭 시 배경 이동 (페이지 전환 전에 애니메이션 시작)
    const menuLinks = document.querySelectorAll('.top-menu-link');
    menuLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // 모달이나 외부 링크는 제외
            if (this.getAttribute('data-bs-toggle') || 
                this.getAttribute('target') === '_blank') {
                return;
            }
            
            // 같은 페이지 내 링크가 아니면 처리하지 않음
            const href = this.getAttribute('href');
            if (!href || href === '#' || !href.startsWith('/')) {
                return;
            }
            
            // 현재 페이지와 같은 링크면 처리하지 않음
            if (this.classList.contains('active')) {
                return;
            }
            
            const topMenu = document.querySelector('.top-menu');
            if (topMenu && topMenu.classList.contains('menu-initialized')) {
                const menuRect = topMenu.getBoundingClientRect();
                const linkRect = this.getBoundingClientRect();
                
                const left = linkRect.left - menuRect.left;
                const width = linkRect.width;
                
                // 목적지 위치를 sessionStorage에 저장 (새 페이지에서 사용)
                sessionStorage.setItem('menu-background-left', left);
                sessionStorage.setItem('menu-background-width', width);
                
                // 페이지 전환을 잠시 막고 애니메이션 시작
                e.preventDefault();
                
                // 클릭한 메뉴 위치로 배경 이동 (애니메이션 시작)
                topMenu.style.setProperty('--active-menu-left', left + 'px');
                topMenu.style.setProperty('--active-menu-width', width + 'px');
                
                // 애니메이션이 시작된 후 페이지 이동
                setTimeout(() => {
                    window.location.href = href;
                }, 250); // 애니메이션이 보이도록 적절한 딜레이
            }
        });
    });
});

    // 페이지 이동 속도 최적화: 내부 링크를 부분 전환(Partial Navigation)으로 처리
    /**
     * 주어진 URL의 전체 HTML을 가져와서 .main-content 내부만 교체하는 함수
     * - 상단 헤더/메뉴/모달 구조는 그대로 유지
     * - 브라우저 history는 pushState/popstate로 관리
     */
    function loadPagePartial(url, options) {
        const opts = Object.assign({ push: true }, options || {});
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) {
            window.location.href = url;
            return;
        }

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newMain = doc.querySelector('.main-content');
            const newTitle = doc.querySelector('title');

            if (newMain) {
                mainContent.innerHTML = newMain.innerHTML;
            } else {
                // 예상치 못한 경우에는 전체 이동으로 폴백
                window.location.href = url;
                return;
            }

            if (newTitle) {
                document.title = newTitle.textContent;
            }

            if (opts.push) {
                history.pushState({}, '', url);
            }

            // 스크롤 맨 위로
            window.scrollTo({ top: 0, behavior: 'auto' });
        })
        .catch(() => {
            // 에러 시에는 일반 페이지 이동으로 폴백
            window.location.href = url;
        });
    }

    // 링크 클릭을 가로채는 전역 이벤트 (캡처 단계 사용)
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a[href]');
        if (!link) return;

        const href = link.getAttribute('href');

        // 외부 링크, 해시, 자바스크립트 링크, 빈 링크는 무시
        if (!href || href === '#' || href.startsWith('javascript:')) return;
        if (link.getAttribute('target') === '_blank') return;
        if (link.id === 'googleLoginBtn') return;
        if (link.classList.contains('top-menu-link')) return; // 상단 메뉴는 기존 애니메이션/이동 로직 유지
        if (link.getAttribute('data-bs-toggle')) return; // 모달/드롭다운 등 부트스트랩 트리거는 그대로 둠

        // 외부 도메인은 건드리지 않음
        if (link.href && link.href.startsWith('http') && !link.href.includes(window.location.hostname)) {
            return;
        }

        // 루트로 가는 링크 (메인 홈)는 아직 전체 새로고침 사용 (갤러리 카드 스택 초기화 이슈 방지)
        if (href === '/' || href.startsWith('/?')) {
            return;
        }

        // 여기까지 왔다면 내부 페이지 이동이므로 부분 전환 사용
        if (href.startsWith('/')) {
            e.preventDefault();
            loadPagePartial(href, { push: true });
        }
    }, true);

    // 브라우저 뒤로가기/앞으로가기 처리
    window.addEventListener('popstate', function() {
        // 현재 URL 기준으로 다시 부분 로딩 시도
        loadPagePartial(window.location.pathname + window.location.search, { push: false });
    });
    
    // 모바일 메뉴 관리
    const mobileMenu = document.getElementById('mobileMenu');
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const mobileOverlay = document.getElementById('mobileOverlay');
    
    // 모바일 메뉴 토글
    if (mobileMenuToggle && mobileMenu && mobileOverlay) {
        mobileMenuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            mobileMenu.classList.toggle('mobile-open');
            mobileOverlay.classList.toggle('active');
            
            // 아이콘 변경
            const icon = this.querySelector('i');
            if (mobileMenu.classList.contains('mobile-open')) {
                icon.classList.remove('bi-list');
                icon.classList.add('bi-x-lg');
            } else {
                icon.classList.remove('bi-x-lg');
                icon.classList.add('bi-list');
            }
        });
        
        // 오버레이 클릭 시 메뉴 닫기
        mobileOverlay.addEventListener('click', function() {
            mobileMenu.classList.remove('mobile-open');
            mobileOverlay.classList.remove('active');
            
            const icon = mobileMenuToggle.querySelector('i');
            if (icon) {
                icon.classList.remove('bi-x-lg');
                icon.classList.add('bi-list');
            }
        });
        
        // 모바일 메뉴 링크 클릭 시 메뉴 닫기
        const mobileMenuLinks = mobileMenu.querySelectorAll('.mobile-menu-link');
        mobileMenuLinks.forEach(link => {
            link.addEventListener('click', function() {
                // 모달 열기 링크는 제외
                if (this.getAttribute('data-bs-toggle')) {
                    return;
                }
                
                mobileMenu.classList.remove('mobile-open');
                mobileOverlay.classList.remove('active');
                
                const icon = mobileMenuToggle.querySelector('i');
                if (icon) {
                    icon.classList.remove('bi-x-lg');
                    icon.classList.add('bi-list');
                }
            });
        });
    }
    
    // 모바일 언어 선택
    const mobileLanguageSelect = document.getElementById('mobileLanguageSelect');
    if (mobileLanguageSelect) {
        mobileLanguageSelect.addEventListener('change', function(e) {
            const langCode = this.value;
            if (langCode && (langCode === 'ko' || langCode === 'en')) {
                window.location.href = '/lang/' + langCode;
            }
        });
    }

    // Google 로그인 버튼 클릭 처리 함수
    function handleGoogleLogin(btn) {
        const actualLoginUrl = btn.getAttribute('data-login-url') || '/login';
        const popup = window.open(actualLoginUrl, 'GoogleLogin', 'width=500,height=600,scrollbars=yes,resizable=yes');
        
        if (!popup || popup.closed || typeof popup.closed == 'undefined') {
            alert('팝업이 차단되었습니다. 팝업 차단을 해제해주세요.');
            return;
        }
        
        const messageHandler = function(event) {
            if (event.data && event.data.type === 'login') {
                if (event.data.success) {
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
        
        const checkInterval = setInterval(function() {
            if (popup.closed) {
                clearInterval(checkInterval);
                window.removeEventListener('message', messageHandler);
            }
        }, 500);
    }
    
    // 전역 클릭 이벤트 (capture phase) - 모달이 열리기 전에도 작동
    document.addEventListener('click', function(e) {
        const googleLoginBtn = e.target.closest('#googleLoginBtn');
        if (googleLoginBtn) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            handleGoogleLogin(googleLoginBtn);
            return false;
        }
    }, true);
    
    // 로그인 모달이 열릴 때 이벤트 리스너 추가 (이중 안전장치)
    const loginModal = document.getElementById('loginModal');
    if (loginModal) {
        loginModal.addEventListener('shown.bs.modal', function() {
            const googleLoginBtn = document.getElementById('googleLoginBtn');
            if (googleLoginBtn) {
                // 기존 이벤트 리스너가 있더라도 다시 등록
                googleLoginBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    handleGoogleLogin(this);
                    return false;
                });
            }
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
    
    // 홈 화면 배경 이미지 및 스크롤 효과
    const indexHeroBackground = document.getElementById('indexHeroBackground');
    const indexHeroGradient = document.getElementById('indexHeroGradient');
    const gallerySliderContainer = document.getElementById('gallerySliderContainer');
    
    // 배경 이미지가 있는지 확인
    const hasBackground = indexHeroBackground !== null;
    
    if (gallerySliderContainer) {
        if (hasBackground && indexHeroGradient) {
            // 배경 이미지가 있는 경우
            gallerySliderContainer.classList.add('has-background');
            
            const bgImageUrl = indexHeroBackground.getAttribute('data-bg-image');
            if (bgImageUrl) {
                indexHeroBackground.style.backgroundImage = `url('${bgImageUrl}')`;
            }
            
            let ticking = false;
            const scrollHandler = function() {
                if (!ticking) {
                    window.requestAnimationFrame(function() {
                        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                        const windowHeight = window.innerHeight;
                        const headerHeight = 70;
                        const availableHeight = windowHeight - headerHeight;
                        
                        // 배경 이미지는 고정된 위치에 두고 더 이상 움직이지 않음
                        if (indexHeroBackground) {
                            indexHeroBackground.style.transform = 'translateY(0px)';
                        }
                        
                        // 그라데이션 오버레이 표시 (스크롤이 화면의 20% 이상일 때)
                        if (indexHeroGradient) {
                            if (scrollTop > availableHeight * 0.2) {
                                indexHeroGradient.classList.add('scrolled');
                            } else {
                                indexHeroGradient.classList.remove('scrolled');
                            }
                        }
                        
                        // 카드 컨테이너 표시 (스크롤이 화면의 30% 이상일 때 - 더 빨리 나타나도록)
                        if (scrollTop > availableHeight * 0.3) {
                            gallerySliderContainer.classList.add('visible');
                        } else {
                            gallerySliderContainer.classList.remove('visible');
                        }
                        
                        ticking = false;
                    });
                    ticking = true;
                }
            };
            
            // 초기 상태 설정
            scrollHandler();
            
            // 스크롤 이벤트 리스너 (throttled)
            window.addEventListener('scroll', scrollHandler, { passive: true });
            
            // 리사이즈 이벤트
            window.addEventListener('resize', scrollHandler, { passive: true });
        } else {
            // 배경 이미지가 없는 경우 - 카드를 바로 표시
            gallerySliderContainer.classList.remove('has-background');
            gallerySliderContainer.style.opacity = '1';
            gallerySliderContainer.style.transform = 'translateY(0)';
            gallerySliderContainer.style.pointerEvents = 'auto';
            gallerySliderContainer.style.marginTop = '0';
        }
    }
    
    // 갤러리 카드 슬라이더 기능 (CodingTorque 스타일의 data-pos 기반 캐러셀)
    const gallerySliderWrapper = document.getElementById('gallerySliderWrapper');
    const gallerySliderTrack = document.getElementById('gallerySliderTrack');
    const gallerySliderPrev = document.getElementById('gallerySliderPrev');
    const gallerySliderNext = document.getElementById('gallerySliderNext');
    const galleryHomeBtn = document.getElementById('galleryHomeBtn');
    
    if (gallerySliderWrapper && gallerySliderTrack) {
        const cardItems = Array.from(gallerySliderTrack.querySelectorAll('.gallery-card-item'));
        if (cardItems.length === 0) return;

        // 배경 이미지 설정 (최적화된 크기로 로드)
        cardItems.forEach((card) => {
            const bgElement = card.querySelector('.gallery-card-background[data-bg-image]');
            if (bgElement) {
                let imageUrl = bgElement.getAttribute('data-bg-image');
                // 카드 크기: 최대 500px x 600px
                // 레티나 디스플레이 대비 2배 = 1000px x 1200px
                // 하지만 더 가볍게 하기 위해 800px x 960px로 제한
                // 서버 측 이미지인 경우 크기 파라미터 추가
                if (imageUrl.includes('/image/')) {
                    const urlObj = new URL(imageUrl, window.location.origin);
                    urlObj.searchParams.set('w', '800');
                    urlObj.searchParams.set('h', '960');
                    imageUrl = urlObj.pathname + '?' + urlObj.searchParams.toString();
                }
                bgElement.style.backgroundImage = `url('${imageUrl}')`;
            }
        });

        let activeIndex = 0;

        // 현재 activeIndex 기준으로 각 카드의 data-pos 설정 및 z-index 설정
        function assignPositions() {
            cardItems.forEach((card, index) => {
                // 실제 offset 계산 (제한 없음)
                const offset = index - activeIndex;
                card.dataset.pos = String(offset);
                
                // z-index를 실제 인덱스 기반으로 설정 (나중에 오는 카드가 위에)
                // 최대 10개이므로 z-index는 1~10 범위
                card.style.zIndex = String(10 - index);
            });
        }

        // 특정 인덱스를 활성화
        function setActiveIndex(newIndex) {
            const clamped = Math.max(0, Math.min(cardItems.length - 1, newIndex));
            if (clamped === activeIndex) return;
            activeIndex = clamped;
            assignPositions();
        }

        // 초기 위치 설정
        assignPositions();

        // 카드 클릭: 중앙이 아니면 중앙으로 이동, 중앙이면 링크 동작
        cardItems.forEach((card, index) => {
            const cardLink = card.querySelector('.gallery-card-link');
            if (!cardLink) return;

            cardLink.addEventListener('click', function(e) {
                if (index === activeIndex && card.dataset.pos === '0') {
                    // 이미 중앙 카드이면 그대로 상세 페이지 이동
                    return;
                }
                // 중앙이 아니면 중앙으로만 이동
                e.preventDefault();
                setActiveIndex(index);
            });
        });

        // 이전 / 다음 버튼
        if (gallerySliderPrev) {
            gallerySliderPrev.addEventListener('click', function() {
                setActiveIndex(activeIndex - 1);
            });
        }

        if (gallerySliderNext) {
            gallerySliderNext.addEventListener('click', function() {
                setActiveIndex(activeIndex + 1);
            });
        }

        // 홈 버튼: 첫 번째 카드 활성화
        if (galleryHomeBtn) {
            galleryHomeBtn.addEventListener('click', function() {
                setActiveIndex(0);
            });
        }
    }
});

