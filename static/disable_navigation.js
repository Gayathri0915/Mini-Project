(function () {
    // 1. Force state into history API immediately and periodically
    function preventBack() {
        window.history.pushState(null, null, window.location.href);
    }
    
    preventBack();
    
    window.addEventListener('popstate', function () {
        preventBack();
    });

    // 2. Intercept click events on links and force location.replace to avoid generating browser history entries
    document.addEventListener('click', function (e) {
        let target = e.target;
        while (target && target.tagName !== 'A') {
            target = target.parentNode;
        }
        if (target && target.tagName === 'A' && target.href && !target.hasAttribute('download')) {
            if (target.origin === window.location.origin) {
                e.preventDefault();
                window.location.replace(target.href);
            }
        }
    });

    // 3. Prevent standard back keyboard shortcuts, refresh, and dev tools keys
    window.addEventListener('keydown', function (e) {
        // Backspace key
        if (e.key === 'Backspace' || e.keyCode === 8) {
            const activeEl = document.activeElement;
            if (activeEl) {
                const tag = activeEl.tagName.toLowerCase();
                const isEditable = activeEl.isContentEditable || 
                                   tag === 'input' || 
                                   tag === 'textarea' ||
                                   (activeEl.getAttribute('contenteditable') === 'true');
                if (!isEditable) {
                    e.preventDefault();
                }
            }
        }
        
        // Alt + Left Arrow (back)
        if (e.altKey && (e.key === 'ArrowLeft' || e.keyCode === 37)) {
            e.preventDefault();
        }
        
        // Alt + Right Arrow (forward)
        if (e.altKey && (e.key === 'ArrowRight' || e.keyCode === 39)) {
            e.preventDefault();
        }

        // F5 or Ctrl+R (reload)
        if (e.key === 'F5' || e.keyCode === 116 || (e.ctrlKey && (e.key === 'r' || e.keyCode === 82))) {
            e.preventDefault();
        }

        // F12 or Ctrl+Shift+I (dev tools)
        if (e.key === 'F12' || e.keyCode === 123 || (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.keyCode === 73))) {
            e.preventDefault();
        }
    });

    // 4. Disable right click (context menu) to prevent manual reloading
    document.addEventListener('contextmenu', function (e) {
        e.preventDefault();
    });

    // 5. Automatically convert all inline 'location.href = ...' redirects to 'location.replace(...)'
    // to prevent new history entries from being created on navigation.
    const rewriteRedirects = function () {
        const elements = document.querySelectorAll('[onclick]');
        elements.forEach(function (el) {
            const onclickAttr = el.getAttribute('onclick');
            if (onclickAttr && (onclickAttr.indexOf('location.href') !== -1 || onclickAttr.indexOf('window.location.href') !== -1)) {
                const rewritten = onclickAttr.replace(/(?:window\.)?location\.href\s*=\s*(['"`].*?['"`])/g, 'window.location.replace($1)');
                el.setAttribute('onclick', rewritten);
            }
        });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', rewriteRedirects);
    } else {
        rewriteRedirects();
    }
})();
