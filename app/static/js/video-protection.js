/**
 * حماية الفيديوهات من جانب العميل - حلول مجانية وبسيطة
 * 
 * ملاحظة: هذه الحمايات ليست مطلقة لكنها تمنع المحاولات البسيطة
 */

class VideoProtection {
    constructor() {
        this.initProtection();
        this.setupEventListeners();
    }

    initProtection() {
        // منع النقر بالزر الأيمن
        document.addEventListener('contextmenu', (e) => {
            if (e.target.tagName === 'VIDEO' || e.target.closest('.video-container')) {
                e.preventDefault();
                this.showWarning('غير مسموح بحفظ الفيديو');
                return false;
            }
        });

        // منع اختصارات لوحة المفاتيح
        document.addEventListener('keydown', (e) => {
            // منع Ctrl+S (حفظ)
            if (e.ctrlKey && e.keyCode === 83) {
                e.preventDefault();
                this.showWarning('حفظ الصفحة غير مسموح');
                return false;
            }
            
            // منع F12 (أدوات المطور)
            if (e.keyCode === 123) {
                e.preventDefault();
                this.showWarning('أدوات المطور غير مسموحة');
                return false;
            }
        });

        // مراقبة أدوات المطور
        this.detectDevTools();
    }

    setupEventListeners() {
        // منع السحب والإفلات للفيديو
        document.addEventListener('dragstart', (e) => {
            if (e.target.tagName === 'VIDEO') {
                e.preventDefault();
                this.showWarning('سحب الفيديو غير مسموح');
            }
        });
    }

    detectDevTools() {
        // مراقبة تغيير حجم النافذة للكشف عن أدوات المطور
        let devtools = { open: false };
        setInterval(() => {
            if (window.outerHeight - window.innerHeight > 200 || 
                window.outerWidth - window.innerWidth > 200) {
                if (!devtools.open) {
                    devtools.open = true;
                    this.handleDevToolsDetected();
                }
            } else {
                devtools.open = false;
            }
        }, 1000);
    }

    handleDevToolsDetected() {
        this.showWarning('تم اكتشاف أدوات المطور - الفيديو محمي');
        
        // إيقاف تشغيل الفيديوهات
        document.querySelectorAll('video').forEach(video => {
            video.pause();
            video.style.filter = 'blur(10px)';
        });
    }

    showWarning(message) {
        // إظهار تحذير بسيط
        const warning = document.createElement('div');
        warning.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff6b35;
            color: white;
            padding: 15px;
            border-radius: 5px;
            z-index: 10000;
            font-weight: bold;
        `;
        warning.textContent = message;
        document.body.appendChild(warning);
        
        // إزالة التحذير بعد 3 ثوان
        setTimeout(() => {
            warning.remove();
        }, 3000);
    }
}

// تشغيل الحماية عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    new VideoProtection();
});

// منع النسخ
document.addEventListener('copy', (e) => {
    e.preventDefault();
    return false;
});

// منع السحب والإفلات
document.addEventListener('dragstart', (e) => {
    if (e.target.tagName === 'VIDEO') {
        e.preventDefault();
        return false;
    }
}); 