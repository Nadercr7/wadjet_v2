# 🧠 Horus AI: Guardian of Ancient Egyptian Civilization

![Horus AI Logo](https://github.com/user-attachments/assets/f07eb3ad-9123-4b16-9e63-f11cbd3405ea)

> *"Let the wisdom of the ancients meet the power of artificial intelligence."*

---

## 📽️ Project Overview

**Horus AI** is an innovative web application that combines artificial intelligence with ancient Egyptian archaeology to provide an immersive educational experience. The system uses advanced computer vision to identify Egyptian artifacts and provides contextual information through an intelligent chatbot powered by Google's Gemini AI.

### 🎯 Key Features

- **🔍 AI-Powered Image Classification**: Identify ancient Egyptian artifacts with 80%+ accuracy
- **💬 Intelligent Chatbot**: Interactive conversations with Horus AI about artifacts and history
- **🗺️ Personalized Recommendations**: Get customized travel itineraries for Egypt
- **🌍 Multi-Language Support**: Available in English, Arabic, French, and German
- **📊 Sentiment Analysis**: Real-time tourist sentiment from Reddit data
- **🎨 Modern UI/UX**: Beautiful, responsive design with Egyptian aesthetics

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Modern web browser

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/horus-ai.git
   cd horus-ai
   ```

2. **Create virtual environment**
   ```bash
   python -m venv horus_env
   source horus_env/bin/activate  # On Windows: horus_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Create .env file
   echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

---

## 🏗️ System Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Flask 2.3.x | Web framework |
| **AI/ML** | TensorFlow 2.13+, Keras | Image classification |
| **NLP** | Google Gemini Pro | Chat responses |
| **Frontend** | HTML5, CSS3, JavaScript ES6+ | User interface |
| **Data Processing** | Pandas, NumPy | Data manipulation |
| **Image Processing** | Pillow | Image handling |
| **Sentiment Analysis** | TextBlob, Reddit API | Tourist sentiment |

### Project Structure

```
horus-ai/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── last_model_bgd.keras           # Trained CNN model
├── class_labels.py                # Classification labels
├── model_utils.py                 # Image processing utilities
├── llm_utils.py                   # Language processing utilities
├── uploads/                       # Temporary file storage
├── static/                        # Static assets
│   ├── style_phase2.css          # Main stylesheet
│   ├── page2.css                 # Page-specific styles
│   ├── background.jpg            # Background images
│   ├── chatbot _icon.svg         # Chatbot icon
│   └── user.png                  # User avatar
├── templates/                     # HTML templates
│   ├── horos1.html              # Home page
│   ├── page2_image_result.html  # Image results page
│   ├── page3_recommendation_result.html # Recommendations page
│   ├── about_us.html            # About page
│   ├── pharaoh_quiz.html        # Quiz page
│   └── learn_hieroglyphs.html   # Learning page
└── model_test/                   # Test images
```

---

## 🤖 AI/ML Components

### 1. Image Classification Model

**Model Architecture**: Convolutional Neural Network (CNN) with Transfer Learning
- **Input**: 224x224 RGB images
- **Output**: Multi-class probabilities for Egyptian artifacts
- **Accuracy**: ~80% (targeting 90%)
- **Training Data**: Curated dataset of Egyptian artifacts
- **Augmentation**: Rotation, flipping, zooming, brightness/contrast shifts

**Classification Pipeline**:
```python
def classify_image(image_bytes):
    1. Preprocess image (resize to 224x224, normalize)
    2. Load trained CNN model
    3. Make prediction
    4. Post-process results
    5. Return class name and description
```

### 2. Natural Language Processing

**Gemini Integration**:
- **Context-aware responses** based on artifact information
- **Multi-language support** (EN, AR, FR, DE)
- **Cultural sensitivity** in responses
- **Historical accuracy** validation

**Chat Response Generation**:
```python
def generate_chat_response(user_message, artifact_name, artifact_description, language):
    1. Format context with artifact details
    2. Send to Gemini API with cultural context
    3. Process and validate response
    4. Apply language-specific formatting
    5. Return formatted response
```

### 3. Recommendation Engine

**Algorithm**: Keyword-based matching with location filtering
- **Interest matching**: Keyword similarity scoring
- **Location filtering**: City-based recommendations
- **Duration planning**: Multi-day itinerary generation
- **Popularity scoring**: Attraction popularity weighting

**Features**:
- 20+ Egyptian attractions with detailed information
- Google Maps integration
- Visiting tips and historical context
- Duration-based planning (1-7 days)

### 4. Sentiment Analysis

**Reddit Integration**:
- **Real-time sentiment** from tourist posts
- **Multi-language support** (English and Arabic)
- **Caching system** for performance
- **Fallback data** for reliability

---

## 🌐 Web Interface

### Pages Overview

1. **Home Page (`horos1.html`)**
   - Hero section with Egyptian aesthetics
   - Image upload functionality
   - Chat interface
   - Travel recommendations form

2. **Image Results Page (`page2_image_result.html`)**
   - Classification results display
   - Detailed artifact information
   - Interactive chat with Horus AI
   - Download and sharing options

3. **Recommendations Page (`page3_recommendation_result.html`)**
   - Personalized travel itineraries
   - Sentiment analysis results
   - Interactive planning tools
   - Print and export functionality

4. **Additional Pages**
   - About Us: Project information
   - Pharaoh Quiz: Interactive learning
   - Learn Hieroglyphs: Educational content

### UI/UX Features

- **Responsive Design**: Mobile-first approach
- **Egyptian Theme**: Gold and dark color scheme
- **Smooth Animations**: CSS transitions and keyframes
- **Accessibility**: ARIA labels and keyboard navigation
- **Voice Input**: Web Speech API integration
- **Markdown Support**: Rich text formatting

---

## 🔌 API Documentation

### Core Endpoints

#### 1. Image Classification
```http
POST /upload_image
Content-Type: multipart/form-data

Request:
- image: File (required, max 10MB)

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

---

## 🛠️ Development Guide

### Setting Up Development Environment

1. **Install Development Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov black flake8
   ```

2. **Configure Environment Variables**
   ```bash
   export FLASK_ENV=development
   export FLASK_DEBUG=True
   export GEMINI_API_KEY=your_api_key
   ```

3. **Run Development Server**
   ```bash
   python app.py
   ```

### Code Structure

#### Backend Architecture
```python
# Main application flow
app.py
├── Flask app initialization
├── Model loading
├── Route definitions
├── Error handling
└── Development server

# Core modules
model_utils.py      # Image processing
llm_utils.py        # Language processing
class_labels.py     # Classification labels
```

#### Frontend Architecture
```javascript
// Main JavaScript modules
- File upload handling
- Chat functionality
- Voice input processing
- Recommendation system
- UI interactions
- API communication
```

### Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Run linting
flake8 app.py
black app.py
```

---

## 🚀 Deployment

### Local Production Setup

```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Cloud Deployment Options

1. **Heroku**
   ```bash
   # Create Procfile
   echo "web: gunicorn app:app" > Procfile
   
   # Deploy
   heroku create horus-ai-app
   git push heroku main
   ```

2. **AWS EC2**
   ```bash
   # Install dependencies
   sudo apt-get update
   sudo apt-get install python3-pip nginx
   
   # Configure Nginx
   sudo nano /etc/nginx/sites-available/horus-ai
   ```

3. **Google Cloud Run**
   ```bash
   # Build and deploy
   gcloud builds submit --tag gcr.io/PROJECT_ID/horus-ai
   gcloud run deploy --image gcr.io/PROJECT_ID/horus-ai
   ```

---

## 📊 Performance & Monitoring

### Performance Metrics

| Component | Target | Current |
|-----------|--------|---------|
| **Image Classification** | < 2s | ~1.5s |
| **Chat Response** | < 3s | ~2.5s |
| **Recommendations** | < 1s | ~0.8s |
| **Page Load** | < 2s | ~1.8s |

### Monitoring Setup

```python
# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'model_loaded': image_classification_model is not None,
        'timestamp': datetime.now().isoformat()
    })
```

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('horus_ai.log'),
        logging.StreamHandler()
    ]
)
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

## 🔮 Future Enhancements

### Technical Roadmap

1. **Model Improvements**
   - Advanced CNN architectures (ResNet, EfficientNet)
   - Ensemble methods for better accuracy
   - Real-time model updates

2. **Scalability**
   - Microservices architecture
   - Database integration (PostgreSQL/MongoDB)
   - Redis caching layer

3. **Advanced Features**
   - Real-time video analysis
   - AR/VR integration
   - Mobile app development

4. **AI Enhancements**
   - Multi-modal AI (text + image)
   - Personalized learning paths
   - Advanced recommendation algorithms

### Feature Wishlist

- **3D Artifact Visualization**
- **Virtual Museum Tours**
- **Interactive Timeline**
- **Social Features**
- **Gamification Elements**
- **Offline Mode**

---

## 🤝 Contributing

### Development Guidelines

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests for new functionality**
5. **Ensure all tests pass**
   ```bash
   pytest tests/
   ```
6. **Submit a pull request**

### Code Style

- **Python**: PEP 8 compliance
- **JavaScript**: ESLint configuration
- **CSS**: BEM methodology
- **Git**: Conventional commits

### Testing Strategy

- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **End-to-End Tests**: Complete workflow testing
- **Performance Tests**: Load and stress testing

---

## 📚 Additional Resources

### Documentation
- [Technical Documentation](TECHNICAL_DOCUMENTATION.md)
- [Project Diagrams](PROJECT_DIAGRAMS.md)
- [API Reference](API_DOCUMENTATION.md)

### External Links
- [Flask Documentation](https://flask.palletsprojects.com/)
- [TensorFlow Guide](https://www.tensorflow.org/guide)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Egyptian Archaeology Resources](https://www.britannica.com/topic/ancient-Egypt)

### Community
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community forum for questions
- **Wiki**: Additional documentation and guides

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Gemini Team** for providing the AI capabilities
- **Egyptian Ministry of Tourism** for historical data
- **Open Source Community** for various libraries and tools
- **Academic Researchers** in Egyptian archaeology
- **Beta Testers** for valuable feedback

---

## 📞 Support

For support, please contact:
- **Email**: support@horus-ai.com
- **GitHub Issues**: [Create an issue](https://github.com/your-username/horus-ai/issues)
- **Documentation**: [Project Wiki](https://github.com/your-username/horus-ai/wiki)

---

*Built with ❤️ for preserving and sharing the wonders of ancient Egyptian civilization through modern technology.* 