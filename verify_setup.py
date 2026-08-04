#!/usr/bin/env python
"""
Django Chat App - Setup Verification Script
Run this script to verify your installation is correct
Usage: python verify_setup.py
"""

import sys
import subprocess
import os

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def check_python_version():
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ ERROR: Python 3.8 or higher required!")
        return False
    return True

def check_module(module_name):
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
        return True
    except ImportError:
        print(f"✗ {module_name} - NOT INSTALLED")
        return False

def check_redis():
    print_header("Checking Redis Connection")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✓ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("   Please start Redis server: redis-server")
        return False

def check_django_setup():
    print_header("Checking Django Configuration")
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatproj.settings')
        django.setup()
        print("✓ Django setup successful")
        return True
    except Exception as e:
        print(f"✗ Django setup failed: {e}")
        return False

def check_models():
    print_header("Checking Models")
    try:
        from chat.models import UserProfile, ChatRoom, Message
        print("✓ All models imported successfully")
        return True
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        return False

def check_migrations():
    print_header("Checking Migrations")
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'showmigrations', 'chat'],
            capture_output=True,
            text=True
        )
        if '[X]' in result.stdout or '(no migrations)' not in result.stdout:
            print("✓ Migrations found")
            if '[X]' in result.stdout:
                print("✓ Migrations applied")
            else:
                print("⚠️  Migrations not applied yet. Run: python manage.py migrate")
            return True
        else:
            print("✗ No migrations found. Run: python manage.py makemigrations")
            return False
    except Exception as e:
        print(f"✗ Could not check migrations: {e}")
        return False

def check_templates():
    print_header("Checking Templates")
    # FIXED: Correct template paths
    templates = [
        'chat/templates/chat/base.html',
        'chat/templates/chat/register.html',
        'chat/templates/chat/login.html',
        'chat/templates/chat/chat_list.html',
        'chat/templates/chat/chat_room.html',
    ]
    
    all_exist = True
    for template in templates:
        if os.path.exists(template):
            print(f"✓ {template}")
        else:
            print(f"✗ {template} - NOT FOUND")
            all_exist = False
    
    return all_exist

def check_files():
    print_header("Checking Required Files")
    files = [
        'manage.py',
        'chatproj/settings.py',
        'chatproj/asgi.py',
        'chatproj/urls.py',
        'chat/models.py',
        'chat/views.py',
        'chat/urls.py',
        'chat/consumers.py',
        'chat/routing.py',
        'chat/forms.py',
        'chat/admin.py',
        'chat/ddos_protection.py',  # Added DDoS protection check
        'chat/middleware.py',
        'chat/signals.py',
    ]
    
    all_exist = True
    for file in files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - NOT FOUND")
            all_exist = False
    
    return all_exist

def check_env_file():
    print_header("Checking Environment Configuration")
    if os.path.exists('.env'):
        print("✓ .env file found")
        return True
    else:
        print("⚠️  .env file not found")
        print("   Consider creating .env file from .env.example")
        print("   The app will use default settings")
        return True  # Not critical, just a warning

def main():
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   Django Chat App - Setup Verification                 ║
    ║                                                        ║
    ║   This script checks if your environment is ready     ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    checks = []
    
    # Check Python version
    checks.append(("Python Version", check_python_version()))
    
    # Check required modules
    print_header("Checking Required Python Packages")
    required_modules = [
        'django',
        'channels',
        'channels_redis',
        'daphne',
        'PIL',  # Pillow
        'crispy_forms',
        'crispy_bootstrap4',
        'redis',
        'dotenv',  # python-dotenv
    ]
    
    modules_ok = True
    for module in required_modules:
        if not check_module(module):
            modules_ok = False
    checks.append(("Python Packages", modules_ok))
    
    # Check Redis
    checks.append(("Redis Connection", check_redis()))
    
    # Check environment file
    checks.append(("Environment Config", check_env_file()))
    
    # Check files
    checks.append(("Required Files", check_files()))
    
    # Check templates
    checks.append(("Templates", check_templates()))
    
    # Check Django setup
    checks.append(("Django Configuration", check_django_setup()))
    
    # Check models (if Django setup succeeded)
    if checks[-1][1]:
        checks.append(("Models", check_models()))
        checks.append(("Migrations", check_migrations()))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    passed = sum(1 for _, status in checks if status)
    total = len(checks)
    
    for check_name, status in checks:
        symbol = "✓" if status else "✗"
        print(f"{symbol} {check_name}")
    
    print(f"\n{'='*60}")
    print(f"  Passed: {passed}/{total}")
    print(f"{'='*60}")
    
    if passed == total:
        print("\n✅ ALL CHECKS PASSED! Your setup is ready!")
        print("\nNext steps:")
        print("1. Start Redis: redis-server")
        print("2. Run migrations: python manage.py migrate")
        print("3. Run server: python manage.py runserver")
        print("4. Open browser: http://localhost:8000")
        print("5. Register a new user and start chatting!")
        print("\n📝 Note: DDoS protection is enabled by default")
    else:
        print("\n⚠️  SOME CHECKS FAILED!")
        print("\nPlease fix the issues above before running the server.")
        print("\nCommon fixes:")
        print("- Install missing packages: pip install -r requirements.txt")
        print("- Start Redis: redis-server")
        print("- Run migrations: python manage.py migrate")
        print("- Create .env file: cp .env.example .env")
        print("- Create missing template files in chat/templates/chat/")

if __name__ == "__main__":
    main()