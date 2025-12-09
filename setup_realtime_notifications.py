#!/usr/bin/env python3
"""
Setup script for real-time notification system with WebSocket support
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and print status"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║   Real-Time Notification System Setup                        ║
║   With WebSocket Support & Lunar Sound Alerts                ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the project root.")
        sys.exit(1)

    steps = [
        ("pip install channels daphne", "Installing Django Channels and Daphne"),
        ("python manage.py collectstatic --noinput", "Collecting static files"),
    ]

    failed_steps = []

    for cmd, description in steps:
        if not run_command(cmd, description):
            failed_steps.append(description)

    print(f"\n{'='*60}")
    print("📋 SETUP SUMMARY")
    print(f"{'='*60}")

    if failed_steps:
        print(f"\n⚠️  Some steps failed:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\nPlease fix the errors and run the script again.")
    else:
        print("\n✅ All setup steps completed successfully!")

    print(f"\n{'='*60}")
    print("🚀 NEXT STEPS")
    print(f"{'='*60}")
    print("""
1. Start the development server:
   python manage.py runserver

2. Or use Daphne for ASGI support:
   daphne -b 127.0.0.1 -p 8000 ai_gallery.asgi:application

3. Visit http://127.0.0.1:8000/dashboard/notifications

4. The system will:
   ✓ Connect via WebSocket for real-time updates
   ✓ Play lunar sound on new notifications
   ✓ Show browser push notifications (if permitted)
   ✓ Display notifications in mobile notification tray
   ✓ Auto-reconnect if connection is lost

5. For production deployment:
   - Use Daphne or Uvicorn as ASGI server
   - Consider using Redis for channel layer:
     pip install channels-redis
     Update CHANNEL_LAYERS in settings.py

6. Test the system:
   - Create a notification (like, comment, etc.)
   - Watch for real-time updates
   - Check browser console for WebSocket status
   - Verify sound plays on new notifications
    """)

if __name__ == "__main__":
    main()
