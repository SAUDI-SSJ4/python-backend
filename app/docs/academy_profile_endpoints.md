# Academy Profile Endpoints Documentation

## نظرة عامة

تم إنشاء نظام شامل لإدارة بروفايل الأكاديمية يتضمن جميع البيانات المطلوبة مع الحقول الاختيارية. النظام يدعم:

- **بروفايل شامل**: جميع معلومات الأكاديمية مع القوالب والإعدادات
- **بروفايل مختصر**: معلومات أساسية فقط
- **بروفايل عام**: معلومات متاحة للجميع
- **جميع الحقول اختيارية**: لا توجد حقول إجبارية

## الروابط المتاحة

### 1. بروفايل الأكاديمية الشامل

```
GET /api/v1/academy/profile
```

**الوصف**: يعيد بروفايل شامل للأكاديمية يتضمن جميع المعلومات

**المصادقة**: مطلوبة (Bearer Token)

**الاستجابة**:
```json
{
  "status": 200,
  "message": "تم جلب بروفايل الأكاديمية بنجاح",
  "data": {
    "academy": {
      "id": 1,
      "name": "أكاديمية سايان",
      "slug": "sayan-academy",
      "about": "منصة تعليمية رائدة",
      "image": "/uploads/academy.jpg",
      "email": "info@sayan.academy",
      "phone": "+966501234567",
      "address": "الرياض، المملكة العربية السعودية",
      "status": "active",
      "trial_status": "available",
      "users_count": 1000,
      "courses_count": 50,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    },
    "template": {
      "theme_name": "modern",
      "primary_color": "#007bff",
      "secondary_color": "#6c757d",
      "font_family": "Cairo",
      "font_size": "16px",
      "font_weight": "400",
      "custom_css": "body { font-family: 'Cairo', sans-serif; }",
      "custom_js": "console.log('Template loaded');"
    },
    "about": {
      "title": "من نحن",
      "content": "نحن منصة تعليمية رائدة",
      "mission": "تقديم تعليم عالي الجودة",
      "vision": "أن نكون الأكاديمية الأولى",
      "values": {
        "quality": "الجودة العالية",
        "innovation": "الابتكار"
      },
      "image": "/uploads/about.jpg",
      "video_url": "https://youtube.com/watch?v=example",
      "statistics": {
        "students": 1000,
        "courses": 50,
        "instructors": 25
      }
    },
    "social_links": {
      "facebook": "https://facebook.com/sayanacademy",
      "twitter": "https://twitter.com/sayanacademy",
      "instagram": "https://instagram.com/sayanacademy",
      "youtube": "https://youtube.com/sayanacademy",
      "linkedin": "https://linkedin.com/company/sayanacademy",
      "whatsapp": "+966501234567",
      "snapchat": "sayanacademy",
      "tiktok": "@sayanacademy",
      "telegram": "@sayanacademy",
      "discord": "https://discord.gg/sayanacademy"
    },
    "settings": {
      "title": "أكاديمية سايان",
      "logo": "/uploads/logo.png",
      "favicon": "/uploads/favicon.ico",
      "email": "info@sayan.academy",
      "phone": "+966501234567",
      "address": "الرياض، المملكة العربية السعودية",
      "terms": "شروط الاستخدام...",
      "privacy": "سياسة الخصوصية...",
      "description": "منصة تعليمية رائدة",
      "keywords": "تعليم، دورات، أكاديمية",
      "subdomain": "example",
      "domain": "sayan.academy"
    },
    "membership": {
      "membership_id": 1,
      "user_role": "owner",
      "is_active": true,
      "joined_at": "2024-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z"
    },
    "statistics": {
      "sliders_count": 5,
      "faqs_count": 10,
      "opinions_count": 25,
      "users_count": 1000,
      "courses_count": 50
    }
  }
}
```

### 2. بروفايل الأكاديمية المختصر

```
GET /api/v1/academy/profile/summary
```

**الوصف**: يعيد ملخص مختصر لبروفايل الأكاديمية

**المصادقة**: مطلوبة (Bearer Token)

**الاستجابة**:
```json
{
  "status": 200,
  "message": "تم جلب ملخص بروفايل الأكاديمية بنجاح",
  "data": {
    "academy": {
      "id": 1,
      "name": "أكاديمية سايان",
      "slug": "sayan-academy",
      "status": "active",
      "email": "info@sayan.academy",
      "phone": "+966501234567"
    },
    "template": {
      "theme_name": "modern",
      "primary_color": "#007bff",
      "font_family": "Cairo"
    },
    "about": {
      "title": "من نحن",
      "has_mission": true,
      "has_vision": true,
      "has_image": true
    },
    "content_summary": {
      "academy_id": 1,
      "has_template": true,
      "has_about": true,
      "sliders_count": 5,
      "faqs_count": 10,
      "opinions_count": 25
    }
  }
}
```

### 3. بروفايل الأكاديمية العام

```
GET /api/v1/academy/profile/public/{academy_slug}
```

**الوصف**: يعيد معلومات الأكاديمية المتاحة للجميع

**المصادقة**: غير مطلوبة

**المعاملات**:
- `academy_slug`: معرف الأكاديمية (مثال: `sayan-academy`)

**الاستجابة**:
```json
{
  "status": 200,
  "message": "تم جلب بروفايل الأكاديمية العام بنجاح",
  "data": {
    "academy": {
      "id": 1,
      "name": "أكاديمية سايان",
      "slug": "sayan-academy",
      "about": "منصة تعليمية رائدة",
      "image": "/uploads/academy.jpg",
      "email": "info@sayan.academy",
      "phone": "+966501234567",
      "address": "الرياض، المملكة العربية السعودية",
      "users_count": 1000,
      "courses_count": 50,
      "created_at": "2024-01-01T00:00:00Z"
    },
    "template": {
      "theme_name": "modern",
      "primary_color": "#007bff",
      "secondary_color": "#6c757d",
      "font_family": "Cairo"
    },
    "about": {
      "title": "من نحن",
      "content": "نحن منصة تعليمية رائدة",
      "mission": "تقديم تعليم عالي الجودة",
      "vision": "أن نكون الأكاديمية الأولى",
      "image": "/uploads/about.jpg",
      "statistics": {
        "students": 1000,
        "courses": 50,
        "instructors": 25
      }
    },
    "social_links": {
      "facebook": "https://facebook.com/sayanacademy",
      "twitter": "https://twitter.com/sayanacademy",
      "instagram": "https://instagram.com/sayanacademy",
      "snapchat": "sayanacademy"
    },
    "sliders": [
      {
        "id": 1,
        "title": "مرحباً بكم في أكاديميتنا",
        "subtitle": "ابدأ رحلة التعلم اليوم",
        "image": "/uploads/slider1.jpg",
        "link": "/courses",
        "button_text": "تصفح الدورات",
        "order": 1
      }
    ],
    "faqs": [
      {
        "id": 1,
        "question": "كيف يمكنني التسجيل في دورة؟",
        "answer": "يمكنك التسجيل بالضغط على زر التسجيل في صفحة الدورة",
        "category": "التسجيل",
        "order": 1
      }
    ],
    "opinions": [
      {
        "id": 1,
        "name": "أحمد علي",
        "title": "تجربة رائعة",
        "content": "أكاديمية ممتازة مع دورات عالية الجودة",
        "rating": 5,
        "image": "/uploads/student1.jpg",
        "featured": true,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

## الحقول الاختيارية

جميع الحقول في النظام اختيارية، مما يعني:

### 1. معلومات الأكاديمية الأساسية
- `about`: وصف الأكاديمية
- `image`: صورة الأكاديمية
- `email`: البريد الإلكتروني
- `phone`: رقم الهاتف
- `address`: العنوان
- `trial_status`: حالة التجربة
- `trial_start`: بداية التجربة
- `trial_end`: نهاية التجربة

### 2. معلومات القالب
- `theme_name`: اسم الثيم
- `primary_color`: اللون الأساسي
- `secondary_color`: اللون الثانوي
- `font_family`: نوع الخط
- `font_size`: حجم الخط
- `font_weight`: وزن الخط
- `custom_css`: CSS مخصص
- `custom_js`: JavaScript مخصص

### 3. معلومات "من نحن"
- `title`: العنوان
- `content`: المحتوى
- `mission`: الرسالة
- `vision`: الرؤية
- `values`: القيم
- `image`: الصورة
- `video_url`: رابط الفيديو
- `statistics`: الإحصائيات

### 4. وسائل التواصل الاجتماعي
- `facebook`: فيسبوك
- `twitter`: تويتر
- `instagram`: إنستغرام
- `youtube`: يوتيوب
- `linkedin`: لينكد إن
- `whatsapp`: واتساب
- `snapchat`: سناب شات
- `tiktok`: تيك توك
- `telegram`: تليجرام
- `discord`: ديسكورد

### 5. الإعدادات العامة
- `logo`: الشعار
- `favicon`: أيقونة الموقع
- `terms`: شروط الاستخدام
- `privacy`: سياسة الخصوصية
- `description`: الوصف
- `keywords`: الكلمات المفتاحية
- `subdomain`: النطاق الفرعي
- `domain`: النطاق الرئيسي

## أمثلة الاستخدام

### 1. جلب بروفايل الأكاديمية (JavaScript)
```javascript
const response = await fetch('/api/v1/academy/profile', {
  headers: {
    'Authorization': 'Bearer ' + token
  }
});
const data = await response.json();
console.log(data.data.academy.name);
```

### 2. جلب البروفايل العام (JavaScript)
```javascript
const response = await fetch('/api/v1/academy/profile/public/sayan-academy');
const data = await response.json();
console.log(data.data.social_links.facebook);
```

### 3. جلب البروفايل المختصر (Python)
```python
import requests

headers = {'Authorization': f'Bearer {token}'}
response = requests.get('/api/v1/academy/profile/summary', headers=headers)
data = response.json()
print(data['data']['content_summary']['sliders_count'])
```

## ملاحظات مهمة

1. **جميع الحقول اختيارية**: لا توجد حقول إجبارية في النظام
2. **الاستجابة الموحدة**: جميع الروابط تستخدم نفس تنسيق الاستجابة
3. **المصادقة**: الروابط الخاصة تتطلب مصادقة، العامة لا تتطلب
4. **الأداء**: البروفايل المختصر أسرع من الشامل
5. **الأمان**: البروفايل العام لا يحتوي على معلومات حساسة

## رموز الحالة

- `200`: نجح الطلب
- `401`: غير مصرح (مصادقة مطلوبة)
- `403`: محظور (صلاحيات غير كافية)
- `404`: الأكاديمية غير موجودة
- `500`: خطأ في الخادم 
 
 
 