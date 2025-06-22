#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def update_auth_schemas():
    """تحديث ملف auth.py لتحويل class Config إلى model_config"""
    
    # قراءة الملف
    with open('app/schemas/auth.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # النمط القديم والجديد
    old_pattern = r'(\s+)class Config:\s*\n(\s+)json_schema_extra = {'
    new_pattern = r'\1model_config = {\n\2"json_schema_extra": {'
    
    # التبديل
    updated_content = re.sub(old_pattern, new_pattern, content)
    
    # كتابة الملف المحدث
    with open('app/schemas/auth.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("✅ تم تحديث ملف app/schemas/auth.py بنجاح")
    print("🔄 تم تحويل جميع class Config إلى model_config")

if __name__ == "__main__":
    update_auth_schemas() 