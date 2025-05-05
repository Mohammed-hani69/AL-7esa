"""
منصة الحصة التعليمية - ملف المسارات الرئيسي
يحتوي على مسارات الصفحة الرئيسية والصفحات العامة
"""

from flask import render_template, redirect, url_for, request
from flask_login import current_user
from app import app

@app.route('/')
def index():
    """عرض الصفحة الرئيسية"""
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500