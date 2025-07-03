"""
أداة للتحكم في نظام Rate Limiting
تسمح بتفعيل وتعطيل النظام حسب الحاجة
"""

import os
import sys
import argparse

def set_rate_limiting_status(enabled=True):
    """
    تعيين حالة نظام Rate Limiting
    
    Args:
        enabled (bool): True لتفعيل النظام، False لتعطيله
    """
    if enabled:
        if 'DISABLE_RATE_LIMITING' in os.environ:
            del os.environ['DISABLE_RATE_LIMITING']
        print("✅ تم تفعيل نظام Rate Limiting")
    else:
        os.environ['DISABLE_RATE_LIMITING'] = 'True'
        print("❌ تم تعطيل نظام Rate Limiting")

def get_rate_limiting_status():
    """الحصول على حالة نظام Rate Limiting الحالية"""
    is_disabled = os.environ.get('DISABLE_RATE_LIMITING') == 'True'
    if is_disabled:
        print("❌ نظام Rate Limiting معطل حاليًا")
    else:
        print("✅ نظام Rate Limiting مُفعل حاليًا")
    return not is_disabled

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="أداة التحكم في نظام Rate Limiting")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--enable', action='store_true', help='تفعيل نظام Rate Limiting')
    group.add_argument('--disable', action='store_true', help='تعطيل نظام Rate Limiting')
    group.add_argument('--status', action='store_true', help='عرض حالة نظام Rate Limiting الحالية')
    
    args = parser.parse_args()
    
    if args.enable:
        set_rate_limiting_status(True)
    elif args.disable:
        set_rate_limiting_status(False)
    elif args.status:
        get_rate_limiting_status()
    else:
        # اعرض المساعدة إذا لم يتم تمرير أية وسائط
        parser.print_help()
