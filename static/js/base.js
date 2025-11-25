// 사이드바 토글 기능
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarIcon = document.getElementById('sidebarToggleIcon');

    // 로컬 스토리지에서 사이드바 상태 불러오기 (기본값: 접힌 상태)
    // 기본적으로 접힌 상태로 시작 (localStorage에 값이 없으면 접힌 상태)
    const sidebarExpanded = localStorage.getItem('sidebarExpanded') === 'true';
    if (sidebarExpanded) {
        sidebar.classList.add('expanded');
        sidebarIcon.classList.remove('bi-list');
        sidebarIcon.classList.add('bi-x-lg');
    } else {
        // 명시적으로 접힌 상태로 설정
        sidebar.classList.remove('expanded');
        sidebarIcon.classList.remove('bi-x-lg');
        sidebarIcon.classList.add('bi-list');
        localStorage.setItem('sidebarExpanded', 'false');
    }

    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('expanded');
        
        // 아이콘 변경
        if (sidebar.classList.contains('expanded')) {
            sidebarIcon.classList.remove('bi-list');
            sidebarIcon.classList.add('bi-x-lg');
            localStorage.setItem('sidebarExpanded', 'true');
        } else {
            sidebarIcon.classList.remove('bi-x-lg');
            sidebarIcon.classList.add('bi-list');
            localStorage.setItem('sidebarExpanded', 'false');
        }
    });

    // 로그인 모달에서 Google 로그인 버튼 클릭 시 팝업 열기
    const googleLoginBtn = document.getElementById('googleLoginBtn');
    if (googleLoginBtn) {
        googleLoginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const loginUrl = this.getAttribute('href');
            const popup = window.open(loginUrl, 'GoogleLogin', 'width=500,height=600,scrollbars=yes,resizable=yes');
            
            // 팝업에서 로그인 완료 메시지 수신
            window.addEventListener('message', function(event) {
                if (event.data && event.data.type === 'login') {
                    if (event.data.success) {
                        // 로그인 성공 시 모달 닫고 페이지 새로고침
                        const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                        if (modal) modal.hide();
                        window.location.reload();
                    } else {
                        alert(event.data.message || '로그인에 실패했습니다.');
                    }
                }
            });
            
            // 팝업이 닫혔는지 확인
            const checkInterval = setInterval(function() {
                if (popup.closed) {
                    clearInterval(checkInterval);
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
});

