// 부모 창에 로그인 완료 메시지 전송
if (window.opener) {
    // 성공 여부와 메시지는 템플릿에서 전달받음
    const success = window.loginCallbackSuccess === true;
    const message = window.loginCallbackMessage || '';
    
    window.opener.postMessage({
        type: 'login',
        success: success,
        message: message
    }, '*');
}

// 1초 후 창 닫기
setTimeout(function() {
    window.close();
}, 1000);

