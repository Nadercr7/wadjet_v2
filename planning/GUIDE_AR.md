<div dir="rtl" align="right">

# 𓂀 دليل مشروع وادجت — كيف تشتغل عليه

---

## ١. هيكل المشروع

المشروع موجود في:
```
D:\Personal attachements\Projects\Wadjet
```

### الفولدرات الأساسية:

| الفولدر | الوظيفة |
|---------|---------|
| `app/` | كود التطبيق — السيرفر والصفحات والـ API |
| `app/api/` | الـ route handlers — كل صفحة ليها فايل |
| `app/core/` | البيزنس لوجيك — الكلاسيفاير والترجمة والكويز |
| `app/templates/` | صفحات الـ HTML (Jinja2) |
| `app/static/css/input.css` | الـ CSS الرئيسي — فيه كل الألوان والكومبوننتس |
| `app/static/js/` | الجافاسكريبت — Alpine.js والـ ML pipeline |
| `models/` | الموديلز بتاعت الـ ML (ONNX) |
| `data/` | داتا الهيروغليفي والمعالم والـ embeddings |
| `scripts/` | سكريبتات البناء والأدوات |
| `planning/` | فايلات التخطيط والتوثيق |
| `archive/` | أرشيف النسخ القديمة (Horus + v1 + سكريبتات التدريب) |

---

## ٢. الفايلات المهمة

### فايلات لازم تقراها قبل أي شغل:

| الفايل | ليه مهم |
|--------|---------|
| `CLAUDE.md` | تعليمات المشروع الكاملة — التيك ستاك، الدزاين سيستم، الراوتس، الكوماندز |
| `planning/CONSTITUTION.md` | القواعد اللي مفيش تنازل عنها — الألوان، الستاك، الأركيتكتشر |
| `planning/EXPANSION_PLAN.md` | خطة التوسع — الفيتشرز الجاية |
| `JOURNEY.md` | قصة المشروع من البداية — عشان تفهم ليه الحاجات اتعملت كده |
| `planning/TASK_PROMPT.md` | البرومبت اللي بتبعته للإيجنت عشان يشتغل على مهمة جديدة |

---

## ٣. إزاي تبدأ مهمة جديدة

### الخطوة ١: حضّر البرومبت

١. افتح `planning/TASK_PROMPT.md`
٢. انسخ المحتوى كله
٣. غيّر `[TASK DESCRIPTION]` بوصف المهمة بتاعتك
٤. ارفق `CLAUDE.md` كملف تعليمات المشروع (attachment)
٥. ابعت البرومبت في شات جديد

### الخطوة ٢: الإيجنت هيعمل إيه

الإيجنت هيعمل الآتي بالترتيب:
1. **يقرأ فايلات المشروع** — `CLAUDE.md`، `CONSTITUTION.md`، الكودبيس
2. **يبحث أونلاين** — دوكيومنتيشن FastAPI، TailwindCSS v4، Alpine.js
3. **يشيك الـ Skills** — يحمّل سكيلز مناسبة من `D:\Personal attachements\Repos\antigravity-awesome-skills\`
4. **يعمل فولدر تخطيط** — فولدر برا المشروع فيه:
   - `spec.md` — مواصفات الفيتشر
   - `tasks.md` — تقسيم المهام
   - `checklist.md` — تشيكلست الجودة
   - `notes.md` — ملاحظات وقرارات
   - `progress.md` — تتبع التقدم
5. **يراجع الخطة** — يراجعها كذا مرة قبل ما يبدأ كود
6. **ينفذ** — مهمة مهمة، يتست بعد كل واحدة
7. **يعمل كوميت وبوش** — لما يخلص كل حاجة

### الخطوة ٣: التمبلتس

الفولدر `planning/templates/` فيه ٣ تمبلتس جاهزة:
- `spec-template.md` — تمبلت المواصفات — استخدمه لكل فيتشر جديدة
- `tasks-template.md` — تمبلت تقسيم المهام
- `checklist-template.md` — تمبلت تشيكلست الجودة

---

## ٤. الدزاين سيستم

### الألوان (مفيش تغيير):

| اللون | الكود | الاستخدام |
|-------|-------|-----------|
| Night | `#0A0A0A` | خلفية الصفحات |
| Surface | `#141414` | خلفية الكاردز والسكشنز |
| Gold | `#D4AF37` | اللون الرئيسي — الأزرار والعناوين المميزة |
| Ivory | `#F5F0E8` | النص الأساسي |
| Sand | `#C4A265` | النص الثانوي |

### الفونتات:
- **عناوين**: Playfair Display
- **نص عادي**: Inter
- **هيروغليفي**: Noto Sans Egyptian Hieroglyphs

### الكومبوننتس الجاهزة (في `input.css`):
- `.btn-gold` — زر دهبي للـ CTAs
- `.btn-ghost` — زر شفاف بحدود
- `.card` / `.card-glow` — كارد عادي أو بتوهج دهبي
- `.badge-gold` — بادج دهبي صغير
- `.input` — حقل إدخال مُنسّق
- `.text-gold-gradient` — نص بتدرج دهبي متحرك

### ⚠️ تحذير مهم:
**لا تستخدم أبداً** `--color-bg` كاسم متغير CSS — ده بيعمل تضارب مع TailwindCSS v4.

---

## ٥. كوماندز التطوير

```bash
# تفعيل البيئة الافتراضية
.venv\Scripts\activate

# تثبيت الـ dependencies
pip install -r requirements.txt
npm install

# بناء الـ CSS
npm run build          # بناء لمرة واحدة
npm run watch          # وضع المراقبة (للتطوير)

# تشغيل السيرفر
uvicorn app.main:app --reload --port 8000

# Docker
docker build -t wadjet .
docker-compose up
```

---

## ٦. الـ Git

### الريموتات:
| الريموت | الغرض | الرابط |
|---------|-------|--------|
| `origin` | GitHub | `https://github.com/Nadercr7/wadjet_v2.git` |
| `hf` | HuggingFace Spaces | `https://huggingface.co/spaces/nadercr7/wadjet-v2` |

### البرانش: `clean-main`

### كوماندز الكوميت والبوش:
```bash
git add -A
git commit -m "feat: وصف التعديل"
git push origin clean-main
git push hf clean-main:main
```

### تنبيهات:
- الأرشيف في `.gitignore` فيه: فايلات `.keras` (248MB)، `.mp4` (92MB)، `.pdf`
- الموديلز الكبيرة متتبّعة بـ Git LFS (`.onnx`، `.ttf`، `.index`، الصور)

---

## ٧. الراوتس

| المسار | الوصف |
|--------|-------|
| `/` | الصفحة الرئيسية — اختار مسار الهيروغليفي أو المعالم |
| `/hieroglyphs` | هاب الهيروغليفي |
| `/landmarks` | هاب المعالم |
| `/scan` | رفع صورة → كشف الرموز → تصنيف → ترجمة |
| `/dictionary` | تصفح ١٠٢٣ رمز هيروغليفي مع بحث وفلترة |
| `/write` | حوّل نص إلى كتابة هيروغليفية |
| `/explore` | استكشف ٢٦٠+ معلم مصري |
| `/chat` | ثوث — شاتبوت متخصص في علم المصريات |
| `/quiz` | اختبر معلوماتك عن مصر القديمة |

---

## ٨. الموديلز

| الموديل | المعمارية | الدقة |
|---------|----------|-------|
| كاشف الهيروغليفي | YOLOv26s · ONNX uint8 | mAP50 = 0.75 |
| مصنف الهيروغليفي | MobileNetV3-Small · ONNX uint8 | 98.2% top-1 |
| مصنف المعالم | EfficientNet-B0 · ONNX uint8 | 93.8% top-1 |

كل الموديلز بتشتغل **على جهاز المستخدم** — مفيش صور بتتبعت لسيرفرات خارجية.

---

## ٩. الموارد الخارجية

### السكيلز:
```
D:\Personal attachements\Repos\antigravity-awesome-skills\
```
فيها سكيلز متخصصة للـ FastAPI، TailwindCSS، SEO، Security، وغيرها.

### مكتبات الأنيميشن:
```
D:\Personal attachements\Repos\21-Frontend-UI\
```
فيها: magicui، animate-ui، motion-primitives، Hover.css، Atropos.

### تمبلتس الـ Spec Kit:
```
planning/templates/
```
فيها: `spec-template.md`، `tasks-template.md`، `checklist-template.md`.

---

## ١٠. قواعد مهمة

1. **الستاك مقفول** — مفيش React أو Vue أو أي SPA framework
2. **الدزاين أسود ودهبي** — لا لايت مود، لا خلفيات بيضا، لا لينكات زرقا
3. **الفوتر**: "Built by Mr Robot" — لا يتغير أبداً
4. **ملف واحد = وظيفة واحدة** — حد أقصى ٣٠٠ سطر قبل التقسيم
5. **بعد كل تعديل CSS** — دوّر `?v=N` في `base.html`
6. **كل الخدمات فري تير** — Render فري، Gemini فري، Kaggle فري

</div>
