# 🏛️ Horus AI — خطة الـ Upgrade الواقعية (أدوات مجانية بالكامل)

> **مهم:** كل حاجة في الملف ده **مجانية 100%** وتقدر تعملها بنفسك.  
> عندك Gemini API Key — ده أقوى سلاح عندك وهنستخدمه في كل حاجة.

---

## 📊 تحليل الوضع الحالي (الحقيقة بدون مجاملة)

### ✅ إيه اللي شغال فعلاً

| الجزء | الحالة |
|-------|--------|
| Keras Model (`last_model_bgd.keras`) | **شغال فعلاً** — بيتلود صح في app.py السطر 530-542 |
| Image Classification | **شغال** — بتستخدم الموديل الحقيقي في `classify_image()` |
| Gemini Chat | **شغال** — Gemini 2.5 Flash connected |
| Recommendation System | **شغال** — keyword-based |
| Sentiment Analysis | **شغال جزئياً** — بيتوقف لما Reddit يحجب (fallback يشتغل) |
| UI | **كويس جداً** — page2_image_result.html 1286 سطر CSS احترافي |

### ❌ المشاكل الحقيقية (مش رأي — كود بالفعل)

```
المشكلة 1 — llm_utils.py السطر 6:
   GEMINI_API_KEY = "AIzaSy..."   ← Key مكشوفة = خطر أمني فعلي

المشكلة 2 — app.py السطر 565:
   description = f"This is a magnificent {predicted_class_name}..."
   ← نفس الجملة لكل الـ 179 مكان! مش مفيدة

المشكلة 3 — مفيش Confidence Threshold:
   ← لو الموديل شايف صورة مش مصرية بيقول "هرم" بثقة 8% بدون تحذير

المشكلة 4 — Reddit بدون OAuth:
   ← بيتحجب بعد شوية requests — الـ fallback data بيشتغل دايماً

المشكلة 5 — مفيش كاميرا مباشرة:
   ← بس Upload صورة — مفيش Live Detection
```

---

## 🚀 خطة الـ Upgrade (4 مراحل — كلها مجانية)

---

## ⚡ المرحلة 1: إصلاحات فورية (يومان)

> بدون لمس الموديل خالص — التطبيق هيبقى أحسن بكتير.

---

### 1.1 — Security: نقل الـ API Key (ساعة) 🔴 عاجل

**إنشاء ملف `.env` في جذر المشروع:**
```
GEMINI_API_KEY=AIzaSyAKFSwrM7uXWTTW1qraZl74wuDcXj_lWZQ
FLASK_SECRET_KEY=horus_egypt_2026_secret
```

**إنشاء `.gitignore`:**
```
.env
__pycache__/
uploads/
horus_env/
*.pyc
```

**تعديل `llm_utils.py` السطر 6:**
```python
# ❌ قديم
GEMINI_API_KEY = "AIzaSy..."

# ✅ جديد
import os
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
```

```bash
pip install python-dotenv
```

**التكلفة: مجاني 100%**

---

### 1.2 — Gemini يكتب وصف حقيقي (3 ساعات) 🟡 أكبر تأثير

**المشكلة الحالية في `app.py` السطر 565:**
```python
# ❌ نفس الجملة لكل الـ 179 مكان
description = f"This is a magnificent {predicted_class_name}, a true masterpiece..."
```

**الحل — إضافة دالة في `llm_utils.py`:**
```python
def generate_location_description(class_name, language='en'):
    """
    Gemini يولّد وصف غني حقيقي عن المكان
    مجاني: 1500 request/day مع Free Tier
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.0-flash')

        prompts = {
            'en': (
                f'You are an expert Egyptian tourism guide.\n'
                f'Write a rich, engaging 3-paragraph description of "{class_name}" for tourists.\n'
                f'Include: what it is, its historical significance, and why visitors love it.\n'
                f'Keep it under 180 words. Be specific and factual. No generic phrases.'
            ),
            'ar': (
                f'أنت مرشد سياحي مصري خبير.\n'
                f'اكتب وصفاً غنياً من 3 فقرات عن "{class_name}" للسياح.\n'
                f'اشمل: ما هو، أهميته التاريخية، ولماذا يحبه الزوار.\n'
                f'أقل من 180 كلمة. كن دقيقاً وتجنب العبارات العامة.'
            ),
            'fr': (
                f'Vous êtes un guide touristique égyptien expert.\n'
                f'Écrivez une description riche de "{class_name}" pour les touristes.\n'
                f'180 mots maximum. Soyez précis et factuel.'
            ),
            'de': (
                f'Sie sind ein ägyptischer Reiseführer-Experte.\n'
                f'Schreiben Sie eine detaillierte Beschreibung von "{class_name}" für Touristen.\n'
                f'Maximal 180 Wörter. Präzise und faktisch.'
            ),
        }

        prompt = prompts.get(language, prompts['en'])
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Gemini description error: {e}")
        return f"{class_name} is a remarkable Egyptian landmark with rich historical significance."
```

**تعديل `app.py` في `classify_image()`:**
```python
def classify_image(image_bytes, language='en'):
    # ... باقي الكود كما هو ...

    # ❌ احذف هذا السطر
    # description = f"This is a magnificent {predicted_class_name}..."

    # ✅ أضف هذا
    from llm_utils import generate_location_description
    description = generate_location_description(predicted_class_name, language)

    return predicted_class_name, description
```

**تعديل route الـ upload ليقبل اللغة:**
```python
@app.route("/upload_image", methods=["POST"])
def upload_image_route():
    language = request.form.get('language', 'en')   # ← إضافة
    # ...
    class_name, description = classify_image(image_bytes, language)
```

**التكلفة: مجاني — Gemini 2.0 Flash = 1500 req/day مجاناً**

---

### 1.3 — Confidence Threshold (ساعتان) 🟡

```python
# في app.py — تعديل classify_image()
CONFIDENCE_THRESHOLD = 0.55  # 55%

def classify_image(image_bytes, language='en'):
    if image_classification_model is None:
        return "uncertain", "الموديل مش محمل حالياً"

    preprocessed = preprocess_image(image_bytes)
    predictions = image_classification_model.predict(preprocessed, verbose=0)

    top_idx = int(np.argmax(predictions[0]))
    confidence = float(predictions[0][top_idx])

    # Top 3 alternatives
    top3_idx = np.argsort(predictions[0])[-3:][::-1]
    top3 = [
        {"name": class_names[i], "pct": round(float(predictions[0][i]) * 100, 1)}
        for i in top3_idx
    ]

    if confidence < CONFIDENCE_THRESHOLD:
        alts = " | ".join([f"{t['name']} ({t['pct']}%)" for t in top3])
        return "uncertain", f"الصورة مش واضحة كفاية. أقرب احتمالات: {alts}"

    from llm_utils import generate_location_description
    description = generate_location_description(class_names[top_idx], language)
    return class_names[top_idx], description
```

---

## 🌟 المرحلة 2: Gemini Vision يراجع الـ Keras (أسبوع)

> **الفكرة الذهبية:** Gemini 2.0 Flash يقدر يشوف الصورة مباشرة!  
> استخدمه يـ validate تصنيف الـ Keras model.  
> ده بيرفع الـ accuracy الفعلي بدون أي training جديد.

### 2.1 — Pipeline: Keras + Gemini Vision

```
الصورة
  ↓
Keras (سريع — 0.1 ثانية)
  ↓
confidence > 80%؟
  │ نعم → نثق في Keras مباشرة (لا نستهلك Gemini)
  │ لا  → Gemini Vision يشوف الصورة ويصحح
  ↓
Gemini يكتب الوصف (مرة واحدة)
  ↓
النتيجة للمستخدم
```

**إضافة في `llm_utils.py`:**
```python
import PIL.Image
import io
import json
import re

def gemini_vision_validate(image_bytes, keras_prediction, language='en'):
    """
    Gemini يشوف الصورة ويقرر لو Keras صح أو غلط.
    بيشتغل بس لما confidence < 80% — علشان منهدرش الـ quota.
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        image = PIL.Image.open(io.BytesIO(image_bytes))

        prompt = (
            f'This image was classified by a model as: "{keras_prediction}"\n\n'
            f'Is this an Egyptian tourist landmark or artifact?\n'
            f'If yes, what is the most accurate name for it?\n\n'
            f'Reply in JSON only:\n'
            f'{{"confirmed": true/false, "best_name": "accurate English name", '
            f'"confidence": "high/medium/low"}}'
        )

        response = model.generate_content([image, prompt])
        match = re.search(r'\{.*?\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())

    except Exception as e:
        print(f"Gemini Vision error: {e}")

    return {"confirmed": True, "best_name": keras_prediction, "confidence": "medium"}


def classify_with_validation(image_bytes, language='en'):
    """
    Pipeline كامل: Keras أولاً، Gemini لو محتاج
    """
    from app import image_classification_model, class_names, preprocess_image
    import numpy as np

    # Step 1: Keras
    preprocessed = preprocess_image(image_bytes)
    predictions = image_classification_model.predict(preprocessed, verbose=0)
    top_idx = int(np.argmax(predictions[0]))
    confidence = float(predictions[0][top_idx])
    keras_class = class_names[top_idx]

    # Step 2: لو واثق > 80% — نثق في Keras
    if confidence >= 0.80:
        description = generate_location_description(keras_class, language)
        return {
            "class_name": keras_class,
            "confidence_pct": round(confidence * 100, 1),
            "source": "keras_confident",
            "description": description
        }

    # Step 3: Keras مش واثق — Gemini يراجع
    if confidence >= 0.45:  # بس لو في احتمال معقول
        validation = gemini_vision_validate(image_bytes, keras_class, language)
        final_name = validation.get("best_name", keras_class)
        description = generate_location_description(final_name, language)
        return {
            "class_name": final_name,
            "confidence_pct": round(confidence * 100, 1),
            "source": "keras+gemini_validated",
            "description": description
        }

    # Step 4: Confidence منخفض جداً
    return {
        "class_name": "uncertain",
        "confidence_pct": round(confidence * 100, 1),
        "source": "low_confidence",
        "description": "الصورة مش واضحة كفاية. جرب صورة أوضح."
    }
```

**تعديل route الـ upload:**
```python
@app.route("/upload_image", methods=["POST"])
def upload_image_route():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    language = request.form.get('language', 'en')
    image_bytes = request.files["image"].read()

    try:
        from llm_utils import classify_with_validation
        result = classify_with_validation(image_bytes, language)
        return jsonify({
            "class_name": result["class_name"],
            "description": result["description"],
            "confidence": result["confidence_pct"],
            "source": result["source"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

**التكلفة: مجاني — Gemini Vision يشتغل بس لما Keras مش واثق**

---

## 📷 المرحلة 3: Live Camera بـ TensorFlow.js (أسبوعان)

> **100% مجاني** — يشتغل في المتصفح، مفيش server bills خالص.

### 3.1 — تحويل الموديل لـ TF.js (ساعتان)

```bash
# تثبيت مرة واحدة
pip install tensorflowjs

# تحويل مع ضغط الـ weights (هيصغّر الحجم ~50%)
tensorflowjs_converter \
    --input_format=keras \
    --output_format=tfjs_layers_model \
    --quantize_float16 \
    last_model_bgd.keras \
    static/models/horus_web/
```

**المتوقع:**
```
static/models/horus_web/
├── model.json         (~20KB)
└── group1-shard*.bin  (~15-25MB total)
```

---

### 3.2 — Camera UI في horos1.html

**إضافة Tabs قبل الـ upload box:**
```html
<!-- Tabs للاختيار بين Upload والكاميرا -->
<div class="mode-tabs" style="display:flex; gap:8px; margin-bottom:16px;">
  <button class="tab-btn active" id="tab-upload" onclick="switchMode('upload')"
    style="flex:1; padding:10px; background:#ffd700; color:#000; border:none;
           border-radius:8px; font-weight:bold; cursor:pointer;">
    📁 رفع صورة
  </button>
  <button class="tab-btn" id="tab-camera" onclick="switchMode('camera')"
    style="flex:1; padding:10px; background:#333; color:#ffd700; border:2px solid #ffd700;
           border-radius:8px; font-weight:bold; cursor:pointer;">
    📷 كاميرا مباشرة
  </button>
</div>

<!-- Camera Section -->
<div id="camera-section" style="display:none; width:100%;">
  <video id="live-video" autoplay playsinline muted
    style="width:100%; border-radius:12px; border:2px solid #ffd700; max-height:320px; object-fit:cover;">
  </video>

  <!-- نتيجة الـ detection -->
  <div id="live-result"
    style="background:rgba(0,0,0,0.85); color:#ffd700; padding:14px;
           border-radius:8px; margin-top:10px; font-size:1.05em; min-height:56px;
           border:1px solid #333; text-align:center;">
    📡 وجّه الكاميرا على أي معلم مصري...
  </div>

  <!-- Confidence Bar -->
  <div style="margin-top:8px;">
    <small style="color:#aaa;">مستوى اليقين:</small>
    <div style="background:#222; border-radius:4px; height:6px; margin-top:4px;">
      <div id="conf-bar"
        style="background:#ffd700; height:6px; border-radius:4px; width:0%; transition:width 0.4s;">
      </div>
    </div>
  </div>

  <button onclick="captureFrame()"
    style="width:100%; margin-top:14px; padding:12px; background:#ffd700; color:#000;
           border:none; border-radius:8px; font-weight:bold; font-size:1em; cursor:pointer;">
    📸 التقط وابدأ المحادثة مع Horus
  </button>
</div>
```

---

### 3.3 — JavaScript الخاص بالكاميرا

**إضافة قبل `</body>` في horos1.html:**
```html
<!-- TF.js من CDN — مجاني -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.20.0/dist/tf.min.js"></script>

<script>
// ============ Horus Live Camera ============
let tfModel = null;
let camStream = null;
let detectionTimer = null;
const CONF_THRESHOLD = 0.55;

// نفس ترتيب class_labels.py بالضبط
const HORUS_CLASSES = [
  "Qaitbay Castle","Muizz Street","Mosque_of_al-Mahmudiya",
  // ... (انسخ كل الـ 179 class من class_labels.py هنا)
];

async function loadModel() {
  document.getElementById('live-result').innerHTML = '⏳ جاري تحميل الموديل (~20MB)...';
  try {
    tfModel = await tf.loadLayersModel('/static/models/horus_web/model.json');
    document.getElementById('live-result').innerHTML = '✅ جاهز! وجّه الكاميرا على معلم مصري.';
  } catch(e) {
    document.getElementById('live-result').innerHTML = '❌ تعذر تحميل الموديل. جرب رفع صورة بدلاً منه.';
    console.error(e);
  }
}

async function startCamera() {
  try {
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } }
    });
    document.getElementById('live-video').srcObject = camStream;
    await loadModel();
    detectionTimer = setInterval(runDetection, 2000); // كل 2 ثانية
  } catch(e) {
    document.getElementById('live-result').innerHTML =
      '❌ تعذر فتح الكاميرا. تأكد من إذن الكاميرا في المتصفح.';
  }
}

async function runDetection() {
  if (!tfModel) return;
  const video = document.getElementById('live-video');
  if (!video.readyState || video.readyState < 2) return;

  // رسم frame بحجم 224x224 (نفس حجم الـ training)
  const canvas = document.createElement('canvas');
  canvas.width = 224; canvas.height = 224;
  canvas.getContext('2d').drawImage(video, 0, 0, 224, 224);

  const tensor = tf.browser.fromPixels(canvas)
    .toFloat().div(255.0).expandDims(0);

  const preds = await tfModel.predict(tensor).data();
  tensor.dispose();

  // أعلى نتيجة
  const maxIdx = preds.indexOf(Math.max(...preds));
  const confidence = preds[maxIdx];

  // Top 3
  const top3 = [...preds]
    .map((s, i) => ({ name: HORUS_CLASSES[i] || `Class ${i}`, score: s }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  // تحديث UI
  const pct = Math.round(confidence * 100);
  document.getElementById('conf-bar').style.width = pct + '%';
  document.getElementById('conf-bar').style.background = confidence >= CONF_THRESHOLD ? '#00cc44' : '#ff4444';

  const resultDiv = document.getElementById('live-result');
  if (confidence >= CONF_THRESHOLD) {
    resultDiv.innerHTML =
      `<strong style="color:#ffd700;font-size:1.1em;">🏛️ ${top3[0].name}</strong>
       <br><small style="color:#aaa;">يقين: ${pct}%</small>`;
    window._lastDetected = top3[0].name; // نحتفظ به لـ captureFrame
  } else {
    const alts = top3.map(t => `${t.name} (${Math.round(t.score*100)}%)`).join('<br>');
    resultDiv.innerHTML =
      `<span style="color:#ff9900;">🔍 غير مؤكد</span><br>
       <small style="color:#888;">${alts}</small>`;
  }
}

async function captureFrame() {
  // التقط الـ frame الحالي وأرسله للـ server للحصول على وصف Gemini
  const video = document.getElementById('live-video');
  const canvas = document.createElement('canvas');
  canvas.width = 640; canvas.height = 480;
  canvas.getContext('2d').drawImage(video, 0, 0);

  canvas.toBlob(async (blob) => {
    const lang = document.getElementById('chat-language')?.value || 'en';
    const fd = new FormData();
    fd.append('image', blob, 'capture.jpg');
    fd.append('language', lang);

    document.getElementById('live-result').innerHTML = '⏳ جاري التحليل...';

    try {
      const resp = await fetch('/upload_image', { method: 'POST', body: fd });
      const data = await resp.json();
      localStorage.setItem('imageResultArtifact', data.class_name);
      localStorage.setItem('imageResultDescription', data.description);
      localStorage.setItem('imageResultConfidence', data.confidence + '%');
      window.location.href = '/page2_image_result';
    } catch(e) {
      document.getElementById('live-result').innerHTML = '❌ حدث خطأ. جرب مرة أخرى.';
    }
  }, 'image/jpeg', 0.88);
}

function stopCamera() {
  if (detectionTimer) { clearInterval(detectionTimer); detectionTimer = null; }
  if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null; }
}

function switchMode(mode) {
  const uploadForm = document.getElementById('upload-form');
  const camSection = document.getElementById('camera-section');
  const tabUp = document.getElementById('tab-upload');
  const tabCam = document.getElementById('tab-camera');

  if (mode === 'camera') {
    uploadForm.style.display = 'none';
    camSection.style.display = 'block';
    tabCam.style.background = '#ffd700';
    tabCam.style.color = '#000';
    tabUp.style.background = '#333';
    tabUp.style.color = '#ffd700';
    startCamera();
  } else {
    camSection.style.display = 'none';
    uploadForm.style.display = 'block';
    tabUp.style.background = '#ffd700';
    tabUp.style.color = '#000';
    tabCam.style.background = '#333';
    tabCam.style.color = '#ffd700';
    stopCamera();
  }
}
</script>
```

---

## 🧠 المرحلة 4: موديل جديد بـ Kaggle (مجاني)

> **GPU مجاني:** Kaggle بيدي NVIDIA P100 — 30 ساعة/أسبوع.  
> وقت التدريب المتوقع: ~2.5 ساعة في run واحد.

### 4.1 — جمع داتا من Wikimedia (مجاني تماماً)

```python
# data_collector.py — سكريبت لتحميل صور مجانية
import requests, os, time

def download_from_wikimedia(landmark, save_dir, max_images=200):
    """
    Wikimedia Commons API — مجاني بالكامل، لا يحتاج API key
    """
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{landmark} Egypt",
        "gsrnamespace": 6,
        "gsrlimit": max_images,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }

    os.makedirs(save_dir, exist_ok=True)
    r = requests.get(url, params=params, timeout=15)
    pages = r.json().get("query", {}).get("pages", {})

    count = 0
    for page in pages.values():
        info = page.get("imageinfo", [{}])[0]
        img_url = info.get("url", "")
        if img_url.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                img = requests.get(img_url, timeout=10)
                with open(f"{save_dir}/{count}.jpg", 'wb') as f:
                    f.write(img.content)
                count += 1
                time.sleep(0.3)  # احترام لـ rate limit
            except: continue

    return count

# تشغيل على أهم الـ classes
from class_labels import class_names
for name in class_names:
    clean_name = name.replace('_', ' ')
    n = download_from_wikimedia(clean_name, f"dataset/{name}")
    print(f"✅ {name}: {n} صورة")
```

---

### 4.2 — كود التدريب على Kaggle

```python
# kaggle_train.py — ارفعه على Kaggle Notebook وشغّله
import tensorflow as tf
from tensorflow.keras.applications import EfficientNetB3
from tensorflow.keras import layers, Model

NUM_CLASSES = 179
IMG_SIZE = 224  # نفس حجم الموديل الحالي — مش هنغيره

def build_model():
    base = EfficientNetB3(include_top=False, weights='imagenet',
                          input_shape=(IMG_SIZE, IMG_SIZE, 3))
    base.trainable = False  # Phase 1

    inputs = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = base(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(512, activation='relu')(x)
    x = layers.Dropout(0.4)(x)
    outputs = layers.Dense(NUM_CLASSES, activation='softmax')(x)

    return Model(inputs, outputs)

# Augmentation
aug = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.1),
    layers.RandomZoom(0.1),
    layers.RandomBrightness(0.15),
])

model = build_model()

# ── Phase 1: Frozen backbone (20 epochs) ──
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-3),
    loss='categorical_crossentropy',
    metrics=['accuracy', tf.keras.metrics.TopKCategoricalAccuracy(k=5, name='top5')]
)
model.fit(train_ds, validation_data=val_ds, epochs=20,
          callbacks=[tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
                     tf.keras.callbacks.ModelCheckpoint('horus_v2_p1.keras', save_best_only=True)])

# ── Phase 2: Fine-tune last 30 layers (30 epochs) ──
base = model.layers[1]
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False

model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
              loss='categorical_crossentropy',
              metrics=['accuracy', 'top5'])
model.fit(train_ds, validation_data=val_ds, epochs=30,
          callbacks=[tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True),
                     tf.keras.callbacks.ModelCheckpoint('horus_v2_final.keras', save_best_only=True)])

model.save('horus_v2_final.keras')
print("✅ Training complete!")
```

**وقت التدريب على Kaggle P100:**
- Phase 1 (20 epochs): ~40 دقيقة
- Phase 2 (30 epochs): ~90 دقيقة
- **المجموع: أقل من 2.5 ساعة في run واحد — مجاناً**

---

## 📋 خطة التنفيذ خطوة بخطوة

```
═══ اليوم الأول (3 ساعات) ═══════════════════════════════
[ ] إنشاء .env ونقل GEMINI_API_KEY
[ ] إنشاء .gitignore
[ ] pip install python-dotenv
[ ] تعديل llm_utils.py يقرأ من .env
[ ] اختبار: التطبيق لسه شغال؟

═══ اليوم الثاني (4 ساعات) ══════════════════════════════
[ ] إضافة generate_location_description() في llm_utils.py
[ ] تعديل classify_image() — بدل الجملة الـ hardcoded
[ ] إضافة language parameter في route الـ upload
[ ] إضافة confidence threshold (55%)
[ ] اختبار: الوصف بقى حقيقي؟

═══ الأسبوع الأول (باقيه) ════════════════════════════════
[ ] إضافة gemini_vision_validate() في llm_utils.py
[ ] تعديل upload route يستخدم classify_with_validation()
[ ] اختبار بصور مختلفة — الـ accuracy تحسن؟

═══ الأسبوع الثاني ═══════════════════════════════════════
[ ] tensorflowjs_converter على الموديل الحالي
[ ] copy HORUS_CLASSES من class_labels.py للـ JavaScript
[ ] إضافة Camera tabs في horos1.html
[ ] إضافة JavaScript الكاميرا
[ ] اختبار على Chrome موبايل

═══ الشهر الأول ══════════════════════════════════════════
[ ] تشغيل data_collector.py لجمع صور Wikimedia
[ ] رفع dataset على Kaggle
[ ] تشغيل kaggle_train.py
[ ] استبدال الموديل القديم بالجديد
```

---

## 🛠️ جدول الأدوات المجانية الكاملة

| الأداة | الاستخدام | التكلفة |
|--------|-----------|---------|
| **Gemini 2.0 Flash** | وصف الأماكن + Chat + Vision | مجاني (1500 req/day) |
| **Gemini Vision** | مراجعة وتصحيح Keras results | مجاني (ضمن الـ quota) |
| **TensorFlow.js** | Live camera في المتصفح | مجاني 100% |
| **python-dotenv** | إخفاء الـ secrets | مجاني |
| **tensorflowjs_converter** | تحويل الموديل للويب | مجاني |
| **Kaggle Notebooks** | تدريب الموديل (P100 GPU) | مجاني 30h/أسبوع |
| **Wikimedia API** | تحميل صور Dataset | مجاني بالكامل |
| **Render.com** | نشر التطبيق للإنترنت | مجاني (512MB RAM) |

---

## ⚠️ تجنب هذه الأخطاء

```
❌ لا تدفع GPU — Kaggle P100 مجاناً أحسن من AWS
❌ لا تستدعي Gemini لكل request — استخدمه بس لما Keras مش واثق
❌ لا توصل Reddit API — الـ fallback كافي، Reddit بيحجب بسرعة
❌ لا تغير حجم الصورة من 224 للموديل الجديد — خليه نفس بدون ما تعيد اختبار كل حاجة
❌ sentence-transformers (~420MB) — الـ keyword matching الحالي كافي لحد ما تكبر
```

---

## 🎯 النتيجة المتوقعة بعد كل مرحلة

| بعد | التطبيق هيبقى إيه |
|-----|-------------------|
| **المرحلة 1** | آمن + أوصاف حقيقية من Gemini بدل الجملة المتكررة |
| **المرحلة 2** | Gemini يراجع Keras ويصحح أخطاءه — accuracy أعلى بدون training |
| **المرحلة 3** | المستخدم يفتح كاميرته يشوف اسم المعلم real-time على موبايله |
| **المرحلة 4** | موديل جديد أكثر دقة مدرب على داتا حقيقية ومنوعة |

---

*آخر تحديث: فبراير 2026 — كل الأدوات مجانية ومتاحة الآن*
