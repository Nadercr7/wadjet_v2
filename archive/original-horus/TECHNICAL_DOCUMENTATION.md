# 🧠 Horus AI - Technical Documentation

## 📋 Table of Contents
1. [System Architecture](#system-architecture)
2. [Technology Stack](#technology-stack)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [AI/ML Components](#aiml-components)
6. [Database & Data Management](#database--data-management)
7. [API Documentation](#api-documentation)
8. [Security Considerations](#security-considerations)
9. [Performance Optimization](#performance-optimization)
10. [Deployment Guide](#deployment-guide)
11. [Testing Strategy](#testing-strategy)
12. [Monitoring & Logging](#monitoring--logging)

---

## 🏗️ System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   AI Services   │
│   (Flask +      │◄──►│   (Flask App)   │◄──►│   (TensorFlow   │
│   HTML/CSS/JS)  │    │                 │    │   + Gemini)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Files  │    │   File Storage  │    │   Model Files   │
│   (Images, CSS) │    │   (Uploads)     │    │   (.keras)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Interaction Flow
1. **User Upload**: Image → Frontend → Backend → AI Model
2. **Classification**: AI Model → Backend → Frontend → User
3. **Chat Interaction**: User → Frontend → Backend → Gemini API → Response
4. **Recommendations**: User Input → Backend → Recommendation Engine → Frontend

---

## 🛠️ Technology Stack

### Backend Technologies
| Technology | Version | Purpose |
|------------|---------|---------|
| **Flask** | 2.3.x | Web framework |
| **Python** | 3.8+ | Programming language |
| **TensorFlow** | 2.13+ | Deep learning framework |
| **Keras** | 2.13+ | Neural network API |
| **Pandas** | 1.5+ | Data manipulation |
| **NumPy** | 1.24+ | Numerical computing |
| **Pillow** | 9.5+ | Image processing |
| **TextBlob** | 0.17+ | Sentiment analysis |
| **Requests** | 2.31+ | HTTP client |

### Frontend Technologies
| Technology | Purpose |
|------------|---------|
| **HTML5** | Structure |
| **CSS3** | Styling & animations |
| **JavaScript (ES6+)** | Interactivity |
| **Marked.js** | Markdown rendering |
| **Web Speech API** | Voice input |

### AI/ML Technologies
| Technology | Purpose |
|------------|---------|
| **Google Gemini Pro** | Natural language processing |
| **CNN (Convolutional Neural Network)** | Image classification |
| **Transfer Learning** | Model optimization |
| **TextBlob** | Sentiment analysis |

### External APIs
| Service | Purpose |
|---------|---------|
| **Google Gemini API** | Chat responses |
| **Reddit API** | Sentiment analysis |
| **Google Maps API** | Location services |

---

## 🔧 Backend Architecture

### Core Application Structure
```
app.py
├── Flask Application Setup
├── Model Loading & Initialization
├── Route Definitions
├── Image Processing Functions
├── Recommendation Engine
├── Sentiment Analysis
└── Error Handling
```

### Key Modules

#### 1. Main Application (`app.py`)
```python
# Core Flask app with integrated AI services
- Image classification model loading
- Recommendation system initialization
- Route definitions for all endpoints
- Error handling and logging
```

#### 2. Image Classification (`model_utils.py`)
```python
# Handles image preprocessing and classification
- Image resizing and normalization
- Model prediction pipeline
- Result formatting and validation
```

#### 3. Language Processing (`llm_utils.py`)
```python
# Manages Gemini API interactions
- Chat response generation
- Multi-language support
- Context-aware responses
```

#### 4. Class Labels (`class_labels.py`)
```python
# Defines artifact classification categories
- Egyptian artifact categories
- Label mapping and validation
```

### Data Flow Architecture
```
User Input → Flask Routes → Processing Functions → AI Models → Response Generation → Frontend
```

---

## 🎨 Frontend Architecture

### Template Structure
```
templates/
├── horos1.html                 # Home page
├── page2_image_result.html     # Image results page
├── page3_recommendation_result.html # Recommendations page
├── about_us.html              # About page
├── pharaoh_quiz.html          # Quiz page
└── learn_hieroglyphs.html     # Learning page
```

### Static Assets
```
static/
├── style_phase2.css           # Main stylesheet
├── page2.css                  # Page-specific styles
├── style1.css                 # Additional styles
├── background.jpg             # Background images
├── chatbot _icon.svg          # Chatbot icon
├── eyeIcon.png               # Eye icon
├── icon.png                  # Upload icon
└── user.png                  # User avatar
```

### JavaScript Architecture
```javascript
// Modular JavaScript structure
- File upload handling
- Chat functionality
- Voice input processing
- Recommendation system
- UI interactions
- API communication
```

### Responsive Design
- **Mobile-first approach**
- **CSS Grid and Flexbox**
- **Media queries for breakpoints**
- **Progressive enhancement**

---

## 🤖 AI/ML Components

### 1. Image Classification Model

#### Model Architecture
```python
# CNN with Transfer Learning
- Base Model: Pre-trained CNN (ResNet/VGG)
- Custom Layers: Classification head
- Input: 224x224 RGB images
- Output: Multi-class probabilities
```

#### Training Details
- **Dataset**: Egyptian artifacts (curated)
- **Augmentation**: Rotation, flipping, zooming
- **Accuracy**: ~80% (target: 90%)
- **Model Format**: Keras (.keras)

#### Classification Pipeline
```python
def classify_image(image_bytes):
    1. Preprocess image (resize, normalize)
    2. Load model
    3. Make prediction
    4. Post-process results
    5. Return class + description
```

### 2. Natural Language Processing

#### Gemini Integration
```python
# Multi-language chat system
- Context-aware responses
- Artifact-specific knowledge
- Cultural sensitivity
- Multi-language support (EN, AR, FR, DE)
```

#### Chat Response Generation
```python
def generate_chat_response(user_message, artifact_name, artifact_description, language):
    1. Format context with artifact info
    2. Send to Gemini API
    3. Process response
    4. Apply language-specific formatting
    5. Return formatted response
```

### 3. Recommendation Engine

#### Keyword-Based Matching
```python
# Simple but effective recommendation system
- Interest keyword extraction
- Location-based filtering
- Popularity scoring
- Duration-based planning
```

#### Recommendation Algorithm
```python
def generate_text_recommendations(location, interests, liked_places, duration):
    1. Parse user preferences
    2. Calculate keyword similarity
    3. Apply location filters
    4. Score attractions
    5. Generate itinerary
    6. Format as markdown
```

### 4. Sentiment Analysis

#### Reddit Integration
```python
# Tourist sentiment analysis
- Reddit API integration
- TextBlob sentiment scoring
- Arabic language support
- Caching for performance
```

---

## 💾 Database & Data Management

### Data Storage Strategy
```
File-based storage:
├── Uploads/           # User uploaded images
├── last_model_bgd.keras # Trained model
├── class_labels.py    # Classification labels
└── Static data in code # Attractions database
```

### Attractions Database
```python
ATTRACTIONS_DATA = [
    {
        "name": "Egyptian Museum",
        "city": "Cairo",
        "type": "Pharaonic",
        "popularity": 9,
        "description": "...",
        "highlights": "...",
        "visiting_tips": "...",
        "maps_url": "..."
    }
    # ... 20+ attractions
]
```

### Data Validation
- **Input validation** for all user inputs
- **File type checking** for uploads
- **Size limits** for images
- **Sanitization** for text inputs

---

## 🔌 API Documentation

### Core Endpoints

#### 1. Image Classification
```http
POST /upload_image
Content-Type: multipart/form-data

Request:
- image: File (required)

Response:
{
    "class_name": "Egyptian Museum",
    "description": "This is a magnificent Egyptian Museum..."
}
```

#### 2. Chat with Horus
```http
POST /chat_with_horus
Content-Type: application/json

Request:
{
    "user_message": "Tell me about this artifact",
    "artifact_name": "Egyptian Museum",
    "artifact_description": "Description...",
    "language": "en"
}

Response:
{
    "bot_response": "As Horus AI, I can tell you..."
}
```

#### 3. Get Recommendations
```http
POST /get_recommendations
Content-Type: application/json

Request:
{
    "location": "Cairo",
    "interests": "history, culture",
    "liked_places": "Pyramids, Museum",
    "duration": "3"
}

Response:
{
    "recommendations": "# Recommended 3-Day Egyptian Itinerary..."
}
```

#### 4. Sentiment Analysis
```http
POST /get_sentiment
Content-Type: application/json

Request:
{
    "location_name": "Pyramids of Giza",
    "language": "en"
}

Response:
{
    "success": true,
    "sentiment_data": {
        "overall_score": 8.5,
        "overall_sentiment": "Very Positive",
        "total_posts": 15
    }
}
```

### Error Handling
```python
# Standardized error responses
{
    "error": "Error description",
    "status": "error"
}
```

---

## 🔒 Security Considerations

### Input Validation
- **File upload validation**: Type, size, content checking
- **SQL injection prevention**: No direct database queries
- **XSS prevention**: Input sanitization
- **CSRF protection**: Flask-WTF integration ready

### API Security
- **Rate limiting**: Implemented for external APIs
- **Error handling**: No sensitive data exposure
- **Input sanitization**: All user inputs validated

### Data Privacy
- **No personal data storage**: Temporary processing only
- **File cleanup**: Uploaded files processed then discarded
- **No logging of sensitive data**: Only technical logs

---

## ⚡ Performance Optimization

### Frontend Optimization
- **Image optimization**: Compressed static assets
- **CSS minification**: Reduced file sizes
- **JavaScript bundling**: Efficient loading
- **Lazy loading**: Images loaded on demand

### Backend Optimization
- **Model caching**: Pre-loaded AI models
- **Response caching**: Sentiment analysis results
- **Async processing**: Non-blocking operations
- **Memory management**: Efficient data structures

### API Optimization
- **Request batching**: Multiple operations in single request
- **Response compression**: Gzip compression
- **Connection pooling**: Efficient HTTP connections
- **Timeout handling**: Proper error recovery

---

## 🚀 Deployment Guide

### Local Development
```bash
# 1. Clone repository
git clone <repository-url>
cd horus-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export GEMINI_API_KEY="your_api_key"
export FLASK_ENV=development

# 5. Run application
python app.py
```

### Production Deployment

#### Option 1: Traditional Server
```bash
# Using Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Using uWSGI
pip install uwsgi
uwsgi --http :5000 --wsgi-file app.py --callable app
```

#### Option 2: Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

#### Option 3: Cloud Deployment
- **Heroku**: Easy deployment with Procfile
- **AWS**: EC2 with load balancer
- **Google Cloud**: App Engine
- **Azure**: App Service

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5000
```

---

## 🧪 Testing Strategy

### Unit Testing
```python
# Test individual components
- Image classification accuracy
- API endpoint functionality
- Data validation
- Error handling
```

### Integration Testing
```python
# Test component interactions
- End-to-end workflows
- API integration
- Frontend-backend communication
```

### Performance Testing
```python
# Load and stress testing
- Concurrent user simulation
- Response time measurement
- Memory usage monitoring
```

### Test Coverage
- **Backend**: 80%+ coverage target
- **Frontend**: Manual testing + automated UI tests
- **API**: Full endpoint testing
- **AI Models**: Accuracy validation

---

## 📊 Monitoring & Logging

### Application Logging
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('horus_ai.log'),
        logging.StreamHandler()
    ]
)
```

### Performance Monitoring
- **Response times**: Track API performance
- **Error rates**: Monitor system health
- **User interactions**: Analytics for improvement
- **Model accuracy**: Track classification performance

### Health Checks
```python
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'model_loaded': image_classification_model is not None,
        'timestamp': datetime.now().isoformat()
    })
```

---

## 🔮 Future Enhancements

### Technical Roadmap
1. **Model Improvements**
   - Advanced CNN architectures
   - Ensemble methods
   - Real-time model updates

2. **Scalability**
   - Microservices architecture
   - Database integration
   - Caching layer

3. **Advanced Features**
   - Real-time video analysis
   - AR/VR integration
   - Mobile app development

4. **AI Enhancements**
   - Multi-modal AI (text + image)
   - Personalized learning
   - Advanced recommendation algorithms

---

## 📚 Additional Resources

### Documentation
- [Flask Documentation](https://flask.palletsprojects.com/)
- [TensorFlow Guide](https://www.tensorflow.org/guide)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)

### Development Tools
- **IDE**: VS Code, PyCharm
- **Version Control**: Git
- **API Testing**: Postman, Insomnia
- **Performance**: Chrome DevTools, Lighthouse

### Community & Support
- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: Comprehensive guides and tutorials
- **Contributing**: Guidelines for contributors

---

