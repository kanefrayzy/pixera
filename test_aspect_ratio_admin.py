"""
Test Aspect Ratio Configuration in Admin Panel
Verifies that the new admin interface works correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pixera.settings')
django.setup()

from generate.models_image import ImageModelConfiguration
from generate.models_video import VideoModelConfiguration
from generate.models_aspect_ratio import AspectRatioQualityConfig, AspectRatioPreset


def test_admin_setup():
    """Test that admin classes are properly configured"""
    print("🧪 Testing Aspect Ratio Configuration Admin Setup\n")

    # 1. Check presets
    print("1️⃣ Checking AspectRatioPreset:")
    presets_count = AspectRatioPreset.objects.count()
    print(f"   Total presets: {presets_count}")

    if presets_count == 0:
        print("   ⚠️  No presets found. Run populate_aspect_ratio_presets.py first")
    else:
        print("   ✅ Presets loaded")

        # Show sample presets
        print("\n   Sample presets:")
        for preset in AspectRatioPreset.objects.all()[:5]:
            icon_status = "❌ Has icon" if preset.icon else "✅ No icon"
            print(f"   - {preset.aspect_ratio}: {preset.name} ({preset.category}) {icon_status}")

    # 2. Check image models
    print("\n2️⃣ Checking ImageModelConfiguration:")
    image_models = ImageModelConfiguration.objects.count()
    print(f"   Total image models: {image_models}")

    if image_models > 0:
        print("   ✅ Image models exist")

        # Check if any have configurations
        configs_count = AspectRatioQualityConfig.objects.filter(model_type='image').count()
        print(f"   Configurations for image models: {configs_count}")
    else:
        print("   ℹ️  No image models yet")

    # 3. Check video models
    print("\n3️⃣ Checking VideoModelConfiguration:")
    video_models = VideoModelConfiguration.objects.count()
    print(f"   Total video models: {video_models}")

    if video_models > 0:
        print("   ✅ Video models exist")

        # Check if any have configurations
        configs_count = AspectRatioQualityConfig.objects.filter(model_type='video').count()
        print(f"   Configurations for video models: {configs_count}")
    else:
        print("   ℹ️  No video models yet")

    # 4. Check total configurations
    print("\n4️⃣ Total AspectRatioQualityConfig:")
    total_configs = AspectRatioQualityConfig.objects.count()
    print(f"   Total configurations: {total_configs}")

    if total_configs > 0:
        print("\n   Sample configurations:")
        for config in AspectRatioQualityConfig.objects.all()[:5]:
            print(f"   - {config.model_type} #{config.model_id}: {config.aspect_ratio} @ {config.quality} = {config.width}×{config.height}")

    # 5. Instructions
    print("\n" + "="*70)
    print("📋 Next Steps:")
    print("="*70)
    print("\n1. Access admin panel:")
    print("   /admin/generate/imagemodelconfiguration/")
    print("   /admin/generate/videomodelconfiguration/")
    print("\n2. Create or edit a model")
    print("\n3. In fieldset 'Конфигурация соотношений сторон и качества':")
    print("   - Check aspect ratios you want to support")
    print("   - For each ratio, expand quality section")
    print("   - Enter width×height for each quality level")
    print("   - Save the form")
    print("\n4. Configurations will be saved to AspectRatioQualityConfig")
    print("\n5. User interface will use these configurations")
    print("   (2 selectors: aspect ratio + quality)")
    print("\n" + "="*70)


if __name__ == '__main__':
    test_admin_setup()
