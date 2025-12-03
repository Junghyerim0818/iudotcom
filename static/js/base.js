// Google 로그인 버튼 클릭 처리 함수 (최우선 등록)
function handleGoogleLogin(btn) {
    console.log('handleGoogleLogin 호출됨');
    const actualLoginUrl = btn.getAttribute('data-login-url') || '/login';
    console.log('로그인 URL:', actualLoginUrl);
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

                // 캐시된 HTML 때문에 비로그인 화면이 남는 경우를 방지하기 위해
                // 현재 URL에 타임스탬프 쿼리를 추가해서 완전히 새로 요청
                const currentUrl = window.location.pathname + window.location.search;
                const sep = currentUrl.includes('?') ? '&' : '?';
                window.location.href = currentUrl + sep + '_login_ts=' + Date.now();
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

// 구글 로그인 버튼 전역 이벤트 (최우선 등록 - 다른 이벤트보다 먼저)
// DOMContentLoaded 전에 등록하여 최우선 처리
document.addEventListener('click', function(e) {
    // 버튼 자체 또는 내부 요소(i 태그, 텍스트 등) 클릭 확인
    const googleLoginBtn = e.target.closest('#googleLoginBtn');
    if (googleLoginBtn) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        console.log('구글 로그인 버튼 클릭 감지');
        handleGoogleLogin(googleLoginBtn);
        return false;
    }
}, true); // capture phase에서 최우선 처리

// 모든 초기화 코드를 하나의 DOMContentLoaded로 통합
// HTML이 먼저 표시되도록 약간 지연
document.addEventListener('DOMContentLoaded', function() {
    // HTML이 먼저 렌더링되도록 약간 지연
    requestAnimationFrame(function() {
    // 커스텀 언어 드롭다운 처리
    const customLanguageDropdown = document.getElementById('customLanguageDropdown');
    const customDropdownSelected = document.getElementById('customDropdownSelected');
    const customDropdownOptions = document.getElementById('customDropdownOptions');
    
    if (customLanguageDropdown && customDropdownSelected && customDropdownOptions) {
        // 드롭다운 열기/닫기
        customDropdownSelected.addEventListener('click', function(e) {
            e.stopPropagation();
            customLanguageDropdown.classList.toggle('active');
        });
        
        // 옵션 클릭 처리
        const options = customDropdownOptions.querySelectorAll('.custom-dropdown-option');
        options.forEach(option => {
            option.addEventListener('click', function(e) {
                e.stopPropagation();
                const value = this.getAttribute('data-value');
                const text = this.textContent.trim();
                
                // 선택된 값 업데이트
                customDropdownSelected.querySelector('.dropdown-text').textContent = text;
                
                // 모든 옵션의 selected 속성 제거
                options.forEach(opt => opt.removeAttribute('data-selected'));
                this.setAttribute('data-selected', 'true');
                
                // 드롭다운 닫기
                customLanguageDropdown.classList.remove('active');
                
                // 언어 변경 API 호출
                if (value && (value === 'ko' || value === 'en')) {
                    fetch('/lang/' + value, {
                        method: 'GET',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    })
                    .then(response => response.json())
                    .then(() => {
                        const currentUrl = window.location.pathname + window.location.search;
                        window.location.href = currentUrl + (currentUrl.includes('?') ? '&' : '?') + '_t=' + Date.now();
                    })
                    .catch(() => {
                        window.location.reload();
                    });
                }
            });
        });
        
        // 외부 클릭 시 드롭다운 닫기
        document.addEventListener('click', function(e) {
            if (!customLanguageDropdown.contains(e.target)) {
                customLanguageDropdown.classList.remove('active');
            }
        });
    }
    
    // 사이드바 통계 데이터 로드
    function loadSidebarStats() {
        fetch('/api/stats', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
            .then(data => {
            if (data.success) {
                const totalPostsEl = document.getElementById('totalPostsCount');
                const todayPostsEl = document.getElementById('todayPostsCount');
                const mobileTotalEl = document.getElementById('mobileTotalPostsCount');
                const mobileTodayEl = document.getElementById('mobileTodayPostsCount');

                if (totalPostsEl) {
                    totalPostsEl.textContent = data.total_posts.toLocaleString();
                }
                if (todayPostsEl) {
                    todayPostsEl.textContent = data.today_posts.toLocaleString();
                }
                if (mobileTotalEl) {
                    mobileTotalEl.textContent = data.total_posts.toLocaleString();
                }
                if (mobileTodayEl) {
                    mobileTodayEl.textContent = data.today_posts.toLocaleString();
                }
            }
        })
        .catch(err => {
            console.error('Failed to load stats:', err);
        });
    }
    
    // 페이지 로드 시 통계 데이터 로드
    loadSidebarStats();
    
    // 활성 메뉴 배경 부드럽게 이동 (KWANGYA 스타일)
    function updateActiveMenu(activeLink, animate = true) {
        const menuLinks = document.querySelectorAll('.top-menu-link');
        menuLinks.forEach(link => {
            link.classList.remove('active');
        });
        if (activeLink) {
            activeLink.classList.add('active');
        }
        
        // 배경 요소 이동 애니메이션
        const menuWrapper = document.querySelector('.top-menu-wrapper');
        const menu = document.querySelector('.top-menu');
        if (!menuWrapper || !menu || !activeLink) return;
        
        // 배경 요소가 없으면 생성
        let menuBackground = menuWrapper.querySelector('.menu-active-background');
        if (!menuBackground) {
            menuBackground = document.createElement('div');
            menuBackground.className = 'menu-active-background';
            menuWrapper.appendChild(menuBackground);
        }
        
        // 활성 링크의 위치 계산
        const activeItem = activeLink.closest('.top-menu-item');
        if (activeItem) {
            const itemRect = activeItem.getBoundingClientRect();
            const wrapperRect = menuWrapper.getBoundingClientRect();
            
            // 정확한 중앙 정렬을 위해 패딩 고려
            const left = itemRect.left - wrapperRect.left;
            const width = itemRect.width;
            
            // 배경 박스가 메뉴 항목의 정 중앙에 오도록 조정
            const backgroundLeft = left;
            const backgroundWidth = width;
            
            if (animate) {
                // 애니메이션 적용
                requestAnimationFrame(() => {
                    menuBackground.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), width 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                    menuBackground.style.transform = `translateX(${backgroundLeft}px)`;
                    menuBackground.style.width = `${backgroundWidth}px`;
                    menuBackground.style.opacity = '1';
                });
            } else {
                // 애니메이션 없이 즉시 위치 설정 (로딩 완료 시)
                menuBackground.style.transition = 'none';
                menuBackground.style.transform = `translateX(${backgroundLeft}px)`;
                menuBackground.style.width = `${backgroundWidth}px`;
                menuBackground.style.opacity = '1';
            }
        }
    }
    
    // URL로 활성 메뉴 찾기
    function findActiveMenuByUrl(url) {
        const menuLinks = document.querySelectorAll('.top-menu-link');
        const urlPath = url.split('?')[0]; // 쿼리 스트링 제거
        
        for (let link of menuLinks) {
            const linkHref = link.getAttribute('href');
            if (linkHref) {
                const linkPath = linkHref.split('?')[0];
                // 1) 정확히 일치하는 경우
                if (linkPath === urlPath) {
                    return link;
                }

                // 2) 상세 페이지 등에서 아카이브 타입 매칭
                //    /archive/archive_1/123 → /archive/archive_1
                if (urlPath.startsWith('/archive/archive_1') && linkPath.startsWith('/archive/archive_1')) {
                    return link;
                }
                if (urlPath.startsWith('/archive/archive_2') && linkPath.startsWith('/archive/archive_2')) {
                    return link;
                }
            }
        }
        return null;
    }
    
    // 초기 활성 메뉴 배경 위치 설정
    function initActiveMenuBackground(animate = false) {
        const activeLink = document.querySelector('.top-menu-link.active');
        if (activeLink) {
            // DOM이 완전히 렌더링된 후 실행
            requestAnimationFrame(() => {
                updateActiveMenu(activeLink, animate);
            });
        }
    }
    
    // 메뉴 위치를 메인 영역 기준으로 조정하고 콘텐츠 여백 설정
    function updateMenuPosition() {
        const mainContentArea = document.querySelector('.main-content-area');
        const menuNav = document.querySelector('.main-menu-nav');
        const scrollableArea = document.querySelector('.main-content-scrollable');
        if (!mainContentArea || !menuNav || !scrollableArea) return;

        // 모바일(1024px 이하)에서는 CSS에서 여백을 처리하므로 JS 조정 불필요
        if (window.innerWidth <= 1024) {
            return;
        }
        
        // 메뉴탭의 높이 계산 (top + 메뉴 높이 + 여백)
        const menuRect = menuNav.getBoundingClientRect();
        const menuHeight = menuRect.height;
        const menuTop = parseFloat(getComputedStyle(menuNav).top) || 32; // 2rem = 32px
        
    }
    
    // 윈도우 리사이즈 시 메뉴 위치 업데이트
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            updateMenuPosition();
            const activeLink = document.querySelector('.top-menu-link.active');
            if (activeLink) {
                updateActiveMenu(activeLink, false);
            }
        }, 100);
    });
    
    // 초기화 - 애니메이션 없이 즉시 위치 설정
    initActiveMenuBackground(false);
    
    // DOM 로드 완료 후 메뉴 위치 및 콘텐츠 여백 설정
    function initializeMenuAndContent() {
        updateMenuPosition();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(initializeMenuAndContent, 100);
        });
    } else {
        setTimeout(initializeMenuAndContent, 100);
    }
    
    // 페이지 이동 속도 최적화: 내부 링크를 부분 전환(Partial Navigation)으로 처리
    /**
     * 주어진 URL의 전체 HTML을 가져와서 .main-content 내부만 교체하는 함수
     * - 상단 헤더/메뉴/모달 구조는 그대로 유지
     * - 브라우저 history는 pushState/popstate로 관리
     */
    function loadPagePartial(url, options) {
        const opts = Object.assign({ push: true }, options || {});
        // 중앙 콘텐츠 영역 내부의 .main-content를 찾음
        const mainContentArea = document.querySelector('.main-content-area');
        const mainContent = mainContentArea ? mainContentArea.querySelector('.main-content') : document.querySelector('.main-content');
        if (!mainContent) {
            window.location.href = url;
            return;
        }

        // 로딩 인디케이터 제거됨

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            // 새 HTML에서 .main-content 영역 찾기
            const newMain = doc.querySelector('.main-content-area .main-content') || doc.querySelector('.main-content');
            const newTitle = doc.querySelector('title');

            if (newMain) {
                // 새 콘텐츠 적용 전 살짝 페이드 아웃
                mainContent.style.opacity = '0';
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
            if (mainContentArea) {
                mainContentArea.scrollTo({ top: 0, behavior: 'auto' });
            } else {
                window.scrollTo({ top: 0, behavior: 'auto' });
            }

            // 콘텐츠 페이드 인으로 깜빡임 최소화
            requestAnimationFrame(() => {
                mainContent.style.opacity = '1';
            });

            // 로딩 인디케이터 제거됨

            // 통계 데이터 다시 로드 (사이드바 업데이트)
            loadSidebarStats();
            
            // 새 콘텐츠에서 활성 메뉴 업데이트 (로딩 완료 후이므로 애니메이션 없이)
            const urlPath = url.split('?')[0];
            const activeLink = findActiveMenuByUrl(urlPath);
            if (activeLink) {
                // 로딩 중에는 이미 애니메이션이 실행되었으므로, 완료 시에는 즉시 위치만 맞춤
                setTimeout(() => {
                    updateActiveMenu(activeLink, false);
                    updateMenuPosition(); // 콘텐츠 변경 후 메뉴 위치 및 여백 재계산
                }, 100);
            } else {
                // 활성 메뉴가 없어도 메뉴 위치는 업데이트
                setTimeout(() => {
                    updateMenuPosition();
                }, 100);
            }
        })
        .catch(() => {
            // 에러 시에는 일반 페이지 이동으로 폴백
            window.location.href = url;
        });
    }

    // 링크 클릭을 가로채는 전역 이벤트 (캡처 단계 사용)
    document.addEventListener('click', function(e) {
        // 구글 로그인 버튼은 최우선으로 제외
        const googleLoginBtn = e.target.closest('#googleLoginBtn');
        if (googleLoginBtn) {
            return; // 구글 로그인 버튼은 다른 이벤트에서 처리
        }
        
        const link = e.target.closest('a[href]');
        if (!link) return;

        // 구글 로그인 버튼 ID 확인 (추가 안전장치)
        if (link.id === 'googleLoginBtn') {
            return;
        }

        const href = link.getAttribute('href');

        // 외부 링크, 해시, 자바스크립트 링크, 빈 링크는 무시
        if (!href || href === '#' || href.startsWith('javascript:')) return;
        if (link.getAttribute('target') === '_blank') return;
        if (link.getAttribute('data-bs-toggle')) return; // 모달/드롭다운 등 부트스트랩 트리거는 그대로 둠

        // 외부 도메인은 건드리지 않음
        if (link.href && link.href.startsWith('http') && !link.href.includes(window.location.hostname)) {
            return;
        }

        // 메뉴 링크는 AJAX로 처리 (부드러운 전환)
        if (link.classList.contains('top-menu-link')) {
            e.preventDefault();
            e.stopPropagation();
            
            // 활성 메뉴 업데이트 (애니메이션 적용)
            updateActiveMenu(link, true);
            
            // 콘텐츠 로드
            if (href.startsWith('/')) {
                loadPagePartial(href, { push: true });
            }
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
        
        // 활성 메뉴 업데이트
        setTimeout(() => {
            const currentPath = window.location.pathname;
            const activeLink = findActiveMenuByUrl(currentPath);
            if (activeLink) {
                updateActiveMenu(activeLink);
            }
        }, 100);
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
    
    // 모바일 언어 선택 (즉시 반영)
    const mobileLanguageSelect = document.getElementById('mobileLanguageSelect');
    if (mobileLanguageSelect) {
        mobileLanguageSelect.addEventListener('change', function(e) {
            const langCode = this.value;
            if (langCode && (langCode === 'ko' || langCode === 'en')) {
                // 언어 변경 API 호출 후 즉시 리로드
                fetch('/lang/' + langCode, {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin' // 쿠키 포함
                })
                .then(response => response.json())
                .then(() => {
                    // 캐시 무효화를 위해 타임스탬프 추가하여 리로드
                    const currentUrl = window.location.pathname + window.location.search;
                    window.location.href = currentUrl + (currentUrl.includes('?') ? '&' : '?') + '_t=' + Date.now();
                })
                .catch(() => {
                    // 실패 시 전체 리로드
                    window.location.reload();
                });
            }
        });
    }

    // 로그인 모달이 열릴 때 버튼에 직접 이벤트 리스너 추가 (이중 안전장치)
    const loginModal = document.getElementById('loginModal');
    if (loginModal) {
        loginModal.addEventListener('shown.bs.modal', function() {
            const googleLoginBtn = document.getElementById('googleLoginBtn');
            if (googleLoginBtn) {
                // 직접 이벤트 리스너 추가 (이미 전역 핸들러가 있지만 추가 안전장치)
                googleLoginBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    console.log('모달 내 구글 로그인 버튼 클릭');
                    handleGoogleLogin(this);
                    return false;
                }, true);
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
    
    // 본문 내 이미지에 자동으로 lazy loading 적용 (아직 로드되지 않은 이미지만)
    const contentImages = document.querySelectorAll('.gallery-detail-content img:not([loading])');
    contentImages.forEach(img => {
        if (!img.complete && !img.loading) {
            img.loading = 'lazy';
        }
    });
    
    // 카드 스택 관련 코드 모두 제거됨 - 원페이지 빌드로 변경
    
    });
});

