#!/usr/bin/env python3
"""
Demo runner script for the AI Recommendation System
"""
import os
import sys
import subprocess
import webbrowser
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import flask
        import flask_cors
        print("✅ Flask dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Installing requirements...")
        
        # Install requirements
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install requirements")
            return False

def check_environment():
    """Check if environment variables are set"""
    env_file = Path("../env.txt")
    if env_file.exists():
        print("📄 Found env.txt file")
        # Load environment variables from env.txt
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Environment variables loaded")
    else:
        print("⚠️  No env.txt file found - running in demo mode")
    
    # Check critical variables
    required_vars = ['COSMOS_ENDPOINT', 'COSMOS_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("   Demo will run with limited functionality")
    else:
        print("✅ All required environment variables found")

def main():
    """Main demo runner"""
    print("🚀 AI Recommendation System Demo")
    print("=" * 50)
    
    # Check for --force flag
    force_mode = '--force' in sys.argv
    if force_mode:
        print("⚡ FORCE UPDATE MODE enabled - Will bypass recent recommendations check")
        print("   Perfect for testing and demonstrations!")
    
    # Change to demo directory
    demo_dir = Path(__file__).parent
    os.chdir(demo_dir)
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Check environment (skip if force mode)
    if not force_mode:
        check_environment()
    else:
        print("✅ Skipping environment check in force mode")
    
    print("\n🌐 Starting demo server...")
    print("📱 Demo will be available at: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(2)
        webbrowser.open('http://localhost:5000')
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Force mode is handled via command line args, no environment variable needed
    
    # Run the Flask app
    try:
        from app import app
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
