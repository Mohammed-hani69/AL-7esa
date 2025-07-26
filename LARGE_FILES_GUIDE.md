# دليل التعامل مع الملفات الكبيرة | Large Files Guide

## المشكلة | Problem
GitHub لا يسمح برفع ملفات أكبر من 100 ميجابايت، وملفات الفيديو والصور الكبيرة تتجاوز هذا الحد.

GitHub doesn't allow files larger than 100MB, and video/large image files exceed this limit.

## الحلول | Solutions

### 1. استخدام .gitignore
تم إضافة الملفات التالية إلى .gitignore لتجنب رفعها:

The following files have been added to .gitignore to avoid uploading them:

```
# Uploaded files
static/uploads/
uploads/
!static/uploads/.gitkeep
!uploads/.gitkeep

# Large files
*.mp4
*.avi
*.mov
*.wmv
*.flv
*.webm
*.mkv
*.m4v
*.3gp
*.3g2
*.f4v
*.f4p
*.f4a
*.f4b
```

### 2. تخزين الملفات محلياً | Local Storage
- احتفظ بالملفات الكبيرة في مجلدات محلية فقط
- استخدم خدمات التخزين السحابي للملفات الكبيرة

- Keep large files in local folders only
- Use cloud storage services for large files

### 3. خدمات التخزين البديلة | Alternative Storage Services
- **Firebase Storage** - للملفات التعليمية
- **AWS S3** - للتخزين السحابي
- **Google Drive** - للمشاركة
- **Dropbox** - للنسخ الاحتياطي

### 4. تحسين الملفات | File Optimization
- ضغط ملفات الفيديو قبل الرفع
- تحويل الصور إلى تنسيقات أصغر
- استخدام أدوات الضغط

- Compress video files before upload
- Convert images to smaller formats
- Use compression tools

## أوامر Git المفيدة | Useful Git Commands

### إزالة ملف كبير من التاريخ | Remove large file from history
```bash
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch path/to/large/file' --prune-empty --tag-name-filter cat -- --all
```

### فحص أحجام الملفات | Check file sizes
```bash
git ls-tree -r -l HEAD | sort -k 4 -n
```

### التراجع عن آخر commit | Undo last commit
```bash
git reset --soft HEAD~1
```

## ملاحظات مهمة | Important Notes

1. **لا ترفع ملفات أكبر من 50 ميجابايت** - GitHub يحذر من ذلك
2. **استخدم Git LFS للملفات الكبيرة** - إذا كنت بحاجة حقيقية لرفعها
3. **احتفظ بنسخة احتياطية محلية** - للملفات المهمة
4. **استخدم خدمات التخزين السحابي** - للملفات التعليمية

1. **Don't upload files larger than 50MB** - GitHub warns about this
2. **Use Git LFS for large files** - If you really need to upload them
3. **Keep local backups** - Of important files
4. **Use cloud storage services** - For educational files

## التحديث الحالي | Current Update

✅ تم حل مشكلة رفع الملفات الكبيرة
✅ تم تحديث .gitignore
✅ تم رفع الإصدار 1.1.3 بنجاح
✅ المشروع جاهز للتطوير المستمر

✅ Large files upload issue resolved
✅ .gitignore updated
✅ Version 1.1.3 uploaded successfully
✅ Project ready for continuous development
