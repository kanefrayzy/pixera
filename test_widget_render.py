import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pixera.settings')
django.setup()

from generate.forms_image_model import ImageModelConfigurationForm
from generate.models_image import ImageModelConfiguration

model = ImageModelConfiguration.objects.first()
form = ImageModelConfigurationForm(instance=model)

print("=== FORM FIELD CHECK ===")
print(f"Total fields: {len(form.fields)}")
print(f"Has aspect_ratio_configurations: {'aspect_ratio_configurations' in form.fields}")

if 'aspect_ratio_configurations' in form.fields:
    field = form.fields['aspect_ratio_configurations']
    print(f"Widget type: {type(field.widget).__name__}")
    print(f"Widget: {field.widget}")

    # Попробуем отрендерить виджет
    try:
        html = field.widget.render('aspect_ratio_configurations', field.initial, {})
        print(f"HTML length: {len(html)}")
        print(f"HTML preview: {html[:200]}...")
    except Exception as e:
        print(f"Error rendering widget: {e}")
