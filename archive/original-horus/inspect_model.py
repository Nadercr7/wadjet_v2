import os
import json

def inspect_keras_model():
    """Inspect the Keras model file to determine its requirements"""
    
    model_path = "last_model_bgd.keras"
    
    print("=== Keras Model Inspector ===\n")
    
    # Check if model file exists
    if not os.path.exists(model_path):
        print(f"❌ Model file '{model_path}' not found!")
        print("Make sure the model file is in the same directory as this script.")
        return
    
    print(f"✅ Model file found: {model_path}")
    print(f"📁 File size: {os.path.getsize(model_path) / (1024*1024):.2f} MB\n")
    
    # Try to inspect the model with different Keras versions
    print("🔍 Attempting to load model with different backends...\n")
    
    # Method 1: Try with tf.keras (TensorFlow backend)
    try:
        import tensorflow as tf
        print(f"📦 TensorFlow version: {tf.__version__}")
        
        # Load model
        model = tf.keras.models.load_model(model_path)
        print("✅ Model loaded successfully with TensorFlow backend!")
        
        # Get model info
        print(f"🏗️  Model type: {type(model).__name__}")
        print(f"📊 Input shape: {model.input_shape}")
        print(f"📊 Output shape: {model.output_shape}")
        print(f"🔢 Total parameters: {model.count_params():,}")
        print(f"🔢 Trainable parameters: {sum([tf.keras.backend.count_params(w) for w in model.trainable_weights]):,}")
        
        # Show model summary
        print("\n📋 Model Architecture:")
        model.summary()
        
        # Check what the model expects
        print(f"\n🎯 Required TensorFlow version: >= 2.x")
        print(f"🎯 Required input format: {model.input_shape}")
        print(f"🎯 Expected image size: {model.input_shape[1]}x{model.input_shape[2]} pixels")
        print(f"🎯 Number of classes: {model.output_shape[-1]}")
        
        return True
        
    except ImportError:
        print("❌ TensorFlow not available")
    except Exception as e:
        print(f"❌ Failed to load with TensorFlow: {e}")
    
    # Method 2: Try with standalone Keras
    try:
        import keras
        print(f"📦 Keras version: {keras.__version__}")
        
        model = keras.models.load_model(model_path)
        print("✅ Model loaded successfully with standalone Keras!")
        
        # Get model info
        print(f"🏗️  Model type: {type(model).__name__}")
        print(f"📊 Input shape: {model.input_shape}")
        print(f"📊 Output shape: {model.output_shape}")
        
        return True
        
    except ImportError:
        print("❌ Standalone Keras not available")
    except Exception as e:
        print(f"❌ Failed to load with standalone Keras: {e}")
    
    print("\n❌ Could not load the model with any available backend")
    return False

def check_python_environment():
    """Check current Python environment and installed packages"""
    
    print("\n=== Python Environment Check ===\n")
    
    import sys
    print(f"🐍 Python version: {sys.version}")
    print(f"📍 Python executable: {sys.executable}")
    
    # Check installed packages
    packages_to_check = [
        'tensorflow', 'keras', 'tf_keras', 'numpy', 'PIL', 'pandas', 
        'sklearn', 'sentence_transformers', 'torch'
    ]
    
    print("\n📦 Installed Packages:")
    for package in packages_to_check:
        try:
            module = __import__(package)
            version = getattr(module, '__version__', 'unknown')
            print(f"  ✅ {package}: {version}")
        except ImportError:
            print(f"  ❌ {package}: not installed")

def recommend_installation():
    """Recommend the best installation approach"""
    
    print("\n=== Recommended Installation ===\n")
    
    print("Based on your Python 3.13 environment, here are the recommended steps:")
    print()
    print("🔧 Option 1: Use TensorFlow 2.20+ (Latest)")
    print("   pip install tensorflow")
    print("   pip install keras")
    print("   pip install pillow numpy pandas scikit-learn")
    print()
    print("🔧 Option 2: Use specific compatible versions")
    print("   pip install tensorflow==2.16.1")
    print("   pip install keras==2.16.0")
    print("   pip install pillow numpy pandas scikit-learn")
    print()
    print("🔧 Option 3: For sentence-transformers without TensorFlow conflicts")
    print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
    print("   pip install sentence-transformers")
    print("   pip install tensorflow keras  # Install after PyTorch")
    print()
    print("⚠️  Note: Your model was likely trained with TensorFlow/Keras")
    print("   You'll need TensorFlow to load and use the .keras model file")

if __name__ == "__main__":
    # Run all checks
    model_loaded = inspect_keras_model()
    check_python_environment()
    
    if not model_loaded:
        recommend_installation()
    
    print("\n" + "="*50)
    print("💡 Next Steps:")
    if model_loaded:
        print("  - Your model is working! Use the same backend for your app")
    else:
        print("  - Install the recommended packages above")
        print("  - Run this script again to verify the installation")
    print("  - Check your app.py import statements match the working backend")
