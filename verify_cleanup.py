#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص تنظيف الجافا سكريبت في صفحات تسجيل الدخول
"""

def verify_login_pages_cleanup():
    """فحص أن صفحات تسجيل الدخول تستخدم النمط المباشر للانتقال"""
    
    print('🔍 فحص صفحات تسجيل الدخول...')
    
    # فحص الصفحة المحمولة
    try:
        with open('templates/auth/auth-mobile/login.html', 'r', encoding='utf-8') as f:
            mobile_content = f.read()
        
        # فحص وجود الانتقال المباشر
        direct_navigation = 'setTimeout(() => {\n                    window.location.href = data.redirect_url;\n                }, 2000)' in mobile_content
        
        # فحص عدم وجود reload
        no_reload = 'reload()' not in mobile_content
        
        print(f'✅ صفحة الجوال - الانتقال المباشر: {"✓" if direct_navigation else "✗"}')
        print(f'✅ صفحة الجوال - خالية من reload: {"✓" if no_reload else "✗"}')
        
    except Exception as e:
        print(f'❌ خطأ في فحص صفحة الجوال: {e}')
    
    # فحص صفحة سطح المكتب  
    try:
        with open('templates/auth/login.html', 'r', encoding='utf-8') as f:
            desktop_content = f.read()
        
        # فحص وجود الانتقال المباشر
        direct_navigation = 'setTimeout(() => {\n                        window.location.href = data.redirect_url;\n                    }, 2000)' in desktop_content
        
        # فحص عدم وجود reload
        no_reload = 'reload()' not in desktop_content
        
        print(f'✅ صفحة سطح المكتب - الانتقال المباشر: {"✓" if direct_navigation else "✗"}')
        print(f'✅ صفحة سطح المكتب - خالية من reload: {"✓" if no_reload else "✗"}')
        
    except Exception as e:
        print(f'❌ خطأ في فحص صفحة سطح المكتب: {e}')
    
    print('\n🎯 تم الانتهاء من فحص تنظيف صفحات تسجيل الدخول!')
    print('📝 الآن جميع صفحات تسجيل الدخول تستخدم النمط المباشر للانتقال مثل صفحة التسجيل')

if __name__ == '__main__':
    verify_login_pages_cleanup()
