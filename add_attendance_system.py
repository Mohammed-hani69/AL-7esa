#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إضافة نظام الحضور والغياب ورقم هاتف ولي الأمر
Adding Attendance System and Parent Phone Migration
"""

from app import app, db
from models import User, Classroom, Attendance
from sqlalchemy import text
import logging

def add_attendance_system():
    """إضافة نظام الحضور والغياب مع رقم هاتف ولي الأمر"""
    with app.app_context():
        try:
            print("🔄 بدء إضافة نظام الحضور والغياب...")
            
            # إضافة عمود رقم هاتف ولي الأمر إلى جدول المستخدمين
            try:
                db.session.execute(text("ALTER TABLE user ADD COLUMN parent_phone VARCHAR(20)"))
                print("✅ تم إضافة عمود رقم هاتف ولي الأمر")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    print("⚠️ عمود رقم هاتف ولي الأمر موجود بالفعل")
                else:
                    print(f"❌ خطأ في إضافة عمود ولي الأمر: {str(e)}")
            
            # إنشاء جدول الحضور والغياب
            try:
                db.session.execute(text("""
                    CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        classroom_id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        date DATE NOT NULL DEFAULT (date('now')),
                        status VARCHAR(20) NOT NULL,
                        notes TEXT,
                        recorded_by INTEGER NOT NULL,
                        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (classroom_id) REFERENCES classroom (id),
                        FOREIGN KEY (student_id) REFERENCES user (id),
                        FOREIGN KEY (recorded_by) REFERENCES user (id),
                        UNIQUE (classroom_id, student_id, date)
                    )
                """))
                print("✅ تم إنشاء جدول الحضور والغياب")
            except Exception as e:
                print(f"❌ خطأ في إنشاء جدول الحضور: {str(e)}")
            
            # إضافة الفهارس لتحسين الأداء
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_attendance_classroom_date ON attendance (classroom_id, date)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_attendance_student_date ON attendance (student_id, date)"))
                print("✅ تم إنشاء الفهارس")
            except Exception as e:
                print(f"❌ خطأ في إنشاء الفهارس: {str(e)}")
            
            # حفظ التغييرات
            db.session.commit()
            print("🎉 تم إضافة نظام الحضور والغياب بنجاح!")
            
            # إضافة بيانات تجريبية للحضور (اختياري)
            add_sample_attendance_data()
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطأ في إضافة نظام الحضور: {str(e)}")

def add_sample_attendance_data():
    """إضافة بيانات تجريبية للحضور"""
    try:
        from datetime import date, timedelta
        
        # الحصول على أول فصل ومعلم وطلاب
        classroom = Classroom.query.first()
        if not classroom:
            print("⚠️ لا توجد فصول لإضافة بيانات تجريبية")
            return
        
        teacher = classroom.teacher
        students = [enrollment.user for enrollment in classroom.enrollments if enrollment.user.role == 'student']
        
        if not students:
            print("⚠️ لا يوجد طلاب في الفصل لإضافة بيانات تجريبية")
            return
        
        print(f"📊 إضافة بيانات تجريبية للحضور في فصل: {classroom.name}")
        
        # إضافة حضور للأسبوع الماضي
        for i in range(7):
            attendance_date = date.today() - timedelta(days=i)
            
            for student in students[:3]:  # أول 3 طلاب فقط
                # تحديد حالة الحضور عشوائياً
                import random
                status = random.choices(
                    ['present', 'absent', 'late', 'excused'],
                    weights=[70, 15, 10, 5]  # نسب واقعية
                )[0]
                
                # التحقق من عدم وجود سجل للحضور في نفس اليوم
                existing = db.session.execute(text(
                    "SELECT id FROM attendance WHERE classroom_id = :classroom_id AND student_id = :student_id AND date = :date"
                ), {
                    'classroom_id': classroom.id,
                    'student_id': student.id,
                    'date': attendance_date
                }).fetchone()
                
                if not existing:
                    db.session.execute(text("""
                        INSERT INTO attendance (classroom_id, student_id, date, status, recorded_by, notes)
                        VALUES (:classroom_id, :student_id, :date, :status, :recorded_by, :notes)
                    """), {
                        'classroom_id': classroom.id,
                        'student_id': student.id,
                        'date': attendance_date,
                        'status': status,
                        'recorded_by': teacher.id,
                        'notes': f'حضور تجريبي - {status}'
                    })
        
        db.session.commit()
        print(f"✅ تم إضافة {len(students[:3]) * 7} سجل حضور تجريبي")
        
    except Exception as e:
        print(f"❌ خطأ في إضافة البيانات التجريبية: {str(e)}")

if __name__ == "__main__":
    add_attendance_system()
