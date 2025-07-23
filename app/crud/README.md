# CRUD Operations for Academy Content Management

This directory contains comprehensive CRUD (Create, Read, Update, Delete) operations for managing academy content including templates, FAQs, opinions, about information, sliders, and settings.

## File Structure

```
app/crud/
├── base.py              # Base CRUD class with common operations
├── template.py          # Template management operations
├── faq.py              # FAQ management operations
├── opinion.py          # Opinion/review management operations
├── about.py            # About information management operations
├── slider.py           # Slider/banner management operations
├── settings.py         # Platform settings management operations
├── academy_content.py  # Unified CRUD operations for all academy content
└── __init__.py         # Package exports
```

## Usage Examples

### 1. Template Management

```python
from app.crud import template
from app.deps.database import get_db

# Get template for academy
db = next(get_db())
academy_template = template.get_by_academy_id(db, academy_id=1)

# Create or update template
template_data = {
    "primary_color": "#007bff",
    "secondary_color": "#6c757d",
    "font_family": "Cairo",
    "font_size": "16px",
    "font_weight": "400",
    "custom_css": "body { font-family: 'Cairo', sans-serif; }"
}
updated_template = template.create_or_update(db, academy_id=1, template_data=template_data)

# Update font settings
template.update_font_settings(db, academy_id=1, font_family="Tajawal", font_size="18px", font_weight="500")

# Get available font options
font_options = template.get_font_options()
```
```

### 2. FAQ Management

```python
from app.crud import faq

# Get all FAQs for academy
faqs = faq.get_active_faqs(db, academy_id=1)

# Create new FAQ
faq_data = {
    "question": "How do I enroll in a course?",
    "answer": "You can enroll by clicking the enroll button on any course page.",
    "category": "Enrollment",
    "order": 1
}
new_faq = faq.create_faq(db, academy_id=1, faq_data=faq_data)

# Search FAQs
search_results = faq.search_faqs(db, academy_id=1, search_term="enroll")
```

### 3. Opinion Management

```python
from app.crud import opinion

# Get approved opinions
approved_opinions = opinion.get_approved_opinions(db, academy_id=1)

# Create new opinion
opinion_data = {
    "name": "Ahmed Ali",
    "content": "Great academy with excellent courses!",
    "rating": 5
}
new_opinion = opinion.create_opinion(db, academy_id=1, opinion_data=opinion_data)

# Approve opinion
approved = opinion.approve_opinion(db, opinion_id=1, academy_id=1)
```

### 4. About Information Management

```python
from app.crud import about

# Get about information
about_info = about.get_by_academy_id(db, academy_id=1)

# Create or update about
about_data = {
    "title": "About Our Academy",
    "content": "We are a leading online education platform...",
    "mission": "To provide quality education to everyone",
    "vision": "To be the number one online academy"
}
updated_about = about.create_or_update(db, academy_id=1, about_data=about_data)
```

### 5. Slider Management

```python
from app.crud import slider

# Get active sliders
active_sliders = slider.get_active_sliders(db, academy_id=1)

# Create new slider
slider_data = {
    "title": "Welcome to Our Academy",
    "subtitle": "Start your learning journey today",
    "image": "/uploads/slider1.jpg",
    "link": "/courses",
    "button_text": "Browse Courses"
}
new_slider = slider.create_slider(db, academy_id=1, slider_data=slider_data)
```

### 6. Settings Management

```python
from app.crud import settings

# Get current settings
current_settings = settings.get_settings(db)

# Update settings with social media and domain
settings_data = {
    "title": "أكاديمية سايان",
    "email": "info@sayan.academy",
    "phone": "+966501234567",
    "address": "الرياض، المملكة العربية السعودية",
    "facebook": "https://facebook.com/sayanacademy",
    "twitter": "https://twitter.com/sayanacademy",
    "instagram": "https://instagram.com/sayanacademy",
    "youtube": "https://youtube.com/sayanacademy",
    "linkedin": "https://linkedin.com/company/sayanacademy",
    "whatsapp": "+966501234567",
    "snapchat": "sayanacademy",
    "tiktok": "@sayanacademy",
    "telegram": "@sayanacademy",
    "discord": "https://discord.gg/sayanacademy",
    "subdomain": "example",
    "domain": "sayan.academy"
}
updated_settings = settings.create_or_update_settings(db, settings_data)

# Update social media links
social_links = {
    "facebook": "https://facebook.com/newsayanacademy",
    "instagram": "https://instagram.com/newsayanacademy"
}
settings.update_social_links(db, social_links)

# Update domain information
settings.update_domain_info(db, subdomain="myacademy", domain="sayan.academy")
```

### 7. Unified Academy Content Management

```python
from app.crud import academy_content

# Get content summary for academy
summary = academy_content.get_academy_content_summary(db, academy_id=1)

# Get all content for academy
template = academy_content.get_template(db, academy_id=1)
about = academy_content.get_about(db, academy_id=1)
sliders = academy_content.get_active_sliders(db, academy_id=1)
faqs = academy_content.get_faqs(db, academy_id=1)
opinions = academy_content.get_approved_opinions(db, academy_id=1)
```

## Error Handling

All CRUD operations include comprehensive error handling with try-catch blocks. Errors are raised with descriptive messages in Arabic for user-facing operations.

## Key Features

1. **Type Safety**: All operations use proper type hints
2. **Error Handling**: Comprehensive exception handling with descriptive messages
3. **Validation**: Input validation through Pydantic schemas
4. **Flexibility**: Support for both individual and unified operations
5. **Performance**: Optimized database queries with proper indexing
6. **Maintainability**: Clean, well-documented code following best practices

## Database Relationships

- All content is linked to academies through `academy_id`
- Opinions can be linked to students through `student_id`
- Templates have a unique relationship with academies (one-to-one)
- About information has a unique relationship with academies (one-to-one)
- Sliders, FAQs, and Opinions have many-to-one relationships with academies

## Font Management

The system supports comprehensive font management with Arabic and English fonts:

### Available Arabic Fonts
- Cairo (default) - Modern and elegant
- Tajawal - Comfortable for reading
- Almarai - Modern interface font
- Changa - Elegant headings
- IBM Plex Sans Arabic - Professional
- Noto Sans Arabic - Comprehensive support

### Available English Fonts
- Arial - Classic and readable
- Helvetica - Modern design
- Times New Roman - Formal content
- Georgia - Elegant reading
- Roboto - Modern applications
- Open Sans - Open source

### Font Settings Example
```python
# Update font settings
template.update_font_settings(
    db, 
    academy_id=1, 
    font_family="Cairo",
    font_size="18px", 
    font_weight="500"
)

# Get font options
font_options = template.get_font_options()
print(font_options["arabic_fonts"])  # List of Arabic fonts
print(font_options["english_fonts"]) # List of English fonts
```

## Social Media Integration

The system supports comprehensive social media integration:

### Supported Platforms
- Facebook, Twitter, Instagram, YouTube, LinkedIn
- WhatsApp, Snapchat, TikTok, Telegram, Discord

### Social Media Management Example
```python
# Update social media links
social_links = {
    "facebook": "https://facebook.com/sayanacademy",
    "instagram": "https://instagram.com/sayanacademy",
    "youtube": "https://youtube.com/sayanacademy",
    "whatsapp": "+966501234567"
}
settings.update_social_links(db, social_links)

# Get social links
links = settings.get_social_links(db)
```

## Domain Management

Support for subdomain and custom domain configuration:

### Domain Configuration Example
```python
# Update domain information
settings.update_domain_info(
    db, 
    subdomain="example", 
    domain="sayan.academy"
)

# Get domain info
domain_info = settings.get_domain_info(db)
# Returns: {"subdomain": "example", "domain": "sayan.academy"}
```

## Best Practices

1. Always use the appropriate CRUD operation for your use case
2. Handle exceptions properly in your API endpoints
3. Use the unified `academy_content` for operations that involve multiple content types
4. Validate input data before passing to CRUD operations
5. Use pagination for large datasets (skip/limit parameters)
6. Consider caching for frequently accessed data
7. Choose appropriate fonts for your content type (Arabic vs English)
8. Validate social media URLs before saving
9. Use consistent font families across your academy
10. Test font rendering on different devices and browsers 
 
 
 