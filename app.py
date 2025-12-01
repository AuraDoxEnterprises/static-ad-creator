import os
import zipfile
import secrets
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import vertexai
from vertexai.preview import generative_models
from vertexai.preview.generative_models import GenerativeModel
import base64
import io
from PIL import Image as PILImage, ImageDraw, ImageFont
import random

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configuration
PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
if not PASSWORD_HASH:
    # Generate hash from plain password if not provided
    plain_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    PASSWORD_HASH = generate_password_hash(plain_password)

# Default settings
DEFAULT_AD_COUNT = int(os.environ.get('DEFAULT_AD_COUNT', 50))
MAX_AD_COUNT = int(os.environ.get('MAX_AD_COUNT', 50))

# Vertex AI Configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
LOCATION = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')

if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

# Prompt variations for unique ads
HEADLINES = [
    "Connecticut Roofing Experts",
    "Quality Roofs for Connecticut Homes",
    "Trusted Roofing in Connecticut",
    "Connecticut's Premier Roofing Service",
    "Expert Roofing Solutions",
    "Protect Your Connecticut Home",
    "Connecticut Roofing Specialists",
    "Durable Roofs Built to Last",
    "Connecticut Home Protection",
    "Professional Roofing Services"
]

SUBHEADLINES = [
    "Expert installation and repair services",
    "Quality materials, professional service",
    "Serving Connecticut homeowners",
    "Reliable roofing solutions",
    "Protection you can trust",
    "Expert craftsmanship guaranteed",
    "Your home deserves the best",
    "Quality workmanship, fair prices",
    "Connecticut's trusted roofing team",
    "Expert service, lasting results"
]

CTA_TEXTS = [
    "Get Free Estimate",
    "Request Quote",
    "Learn More",
    "Get Started",
    "Contact Us Today",
    "Schedule Consultation",
    "Free Inspection",
    "Get Your Quote",
    "Start Your Project",
    "Request Information"
]

COLOR_SCHEMES = [
    {"primary": "#1a365d", "secondary": "#2c5282", "accent": "#3182ce"},  # Blue
    {"primary": "#7c2d12", "secondary": "#9a3412", "accent": "#c2410c"},  # Red/Orange
    {"primary": "#14532d", "secondary": "#166534", "accent": "#16a34a"},  # Green
    {"primary": "#581c87", "secondary": "#6b21a8", "accent": "#9333ea"},  # Purple
    {"primary": "#78350f", "secondary": "#92400e", "accent": "#d97706"},  # Brown/Amber
    {"primary": "#1e293b", "secondary": "#334155", "accent": "#475569"},  # Slate
    {"primary": "#0c4a6e", "secondary": "#075985", "accent": "#0284c7"},  # Sky Blue
    {"primary": "#7f1d1d", "secondary": "#991b1b", "accent": "#dc2626"},  # Dark Red
]

def generate_prompt_variation(index):
    """Generate a unique prompt for each ad variation"""
    headline = random.choice(HEADLINES)
    subheadline = random.choice(SUBHEADLINES)
    cta = random.choice(CTA_TEXTS)
    colors = random.choice(COLOR_SCHEMES)
    
    # Vary the style
    styles = [
        "modern minimalist",
        "professional corporate",
        "bold and eye-catching",
        "clean and elegant",
        "vibrant and energetic"
    ]
    style = random.choice(styles)
    
    prompt = f"""Create a professional static advertisement image for roofing services in Connecticut.

Design Requirements:
- Style: {style}
- Headline text: "{headline}"
- Subheadline text: "{subheadline}"
- Call-to-action button text: "{cta}"
- Primary color: {colors['primary']}
- Secondary color: {colors['secondary']}
- Accent color: {colors['accent']}
- Include subtle roofing-related imagery (roofs, shingles, tools) but keep text prominent
- Clean, professional layout suitable for digital advertising
- No company names, phone numbers, emails, or contact information
- Text should be clearly readable
- Connecticut-focused but professional
- Image dimensions: 1200x628 pixels (standard social media ad size)

The ad should look professional and trustworthy, suitable for online advertising campaigns."""
    
    return prompt, colors

def generate_image_with_vertex_ai(prompt):
    """Generate image using Vertex AI Imagen API"""
    if not PROJECT_ID:
        print("No PROJECT_ID configured, skipping Vertex AI generation")
        return None
    
    try:
        # Try using the vision_models ImageGenerationModel (preferred method)
        from vertexai.preview.vision_models import ImageGenerationModel
        
        model = ImageGenerationModel.from_pretrained("imagegeneration@006")
        
        # Generate image with Vertex AI Imagen
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9",
            safety_filter_level="block_some",
            person_generation="allow_all",
        )
        
        if response.images and len(response.images) > 0:
            # Get image bytes
            image_bytes = response.images[0]._image_bytes
            img = PILImage.open(io.BytesIO(image_bytes))
            # Resize to 1200x628 (standard ad size)
            img = img.resize((1200, 628), PILImage.Resampling.LANCZOS)
            print(f"Successfully generated image with Vertex AI Imagen")
            return img
        else:
            print("No images returned from Vertex AI")
            return None
            
    except ImportError as e:
        print(f"ImportError: {e}. Trying alternative method...")
        # Fallback: Try using the generative models API
        try:
            from vertexai.generative_models import GenerativeModel
            
            model = GenerativeModel("imagen-3.0-generate-001")
            response = model.generate_content(prompt)
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            img = PILImage.open(io.BytesIO(part.inline_data.data))
                            img = img.resize((1200, 628), PILImage.Resampling.LANCZOS)
                            print(f"Successfully generated image with GenerativeModel")
                            return img
            return None
        except Exception as e2:
            print(f"Fallback method error: {e2}")
            return None
    except Exception as e:
        print(f"Error generating image with Vertex AI: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_placeholder_image(headline, subheadline, cta, colors):
    """Create a placeholder image if Vertex AI fails"""
    width, height = 1200, 628
    img = PILImage.new('RGB', (width, height), color=colors['primary'])
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fallback to default
    try:
        # Try macOS fonts first
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
    except:
        try:
            # Try Linux fonts
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except:
            # Fallback to default
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # Draw gradient background effect
    for y in range(height):
        r = int(int(colors['primary'][1:3], 16) * (1 - y / height * 0.3))
        g = int(int(colors['primary'][3:5], 16) * (1 - y / height * 0.3))
        b = int(int(colors['primary'][5:7], 16) * (1 - y / height * 0.3))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # Draw headline with shadow effect
    headline_y = 120
    shadow_offset = 3
    draw.text((50 + shadow_offset, headline_y + shadow_offset), headline, fill='#000000', font=font_large)
    draw.text((50, headline_y), headline, fill=colors['accent'], font=font_large)
    
    # Draw subheadline
    subheadline_y = 220
    draw.text((50 + shadow_offset, subheadline_y + shadow_offset), subheadline, fill='#000000', font=font_medium)
    draw.text((50, subheadline_y), subheadline, fill='white', font=font_medium)
    
    # Draw decorative element (roof icon representation)
    roof_x, roof_y = width - 200, 50
    roof_points = [
        (roof_x, roof_y + 80),
        (roof_x + 60, roof_y),
        (roof_x + 120, roof_y + 80)
    ]
    draw.polygon(roof_points, fill=colors['secondary'], outline=colors['accent'], width=2)
    
    # Draw CTA button with rounded corners effect
    button_width = 350
    button_height = 70
    button_x = width - button_width - 50
    button_y = height - button_height - 50
    
    # Button shadow
    draw.rectangle(
        [button_x + 4, button_y + 4, button_x + button_width + 4, button_y + button_height + 4],
        fill='#000000',
        outline=None
    )
    
    # Button
    draw.rectangle(
        [button_x, button_y, button_x + button_width, button_y + button_height],
        fill=colors['accent'],
        outline=colors['secondary'],
        width=3
    )
    
    # CTA text centered
    bbox = draw.textbbox((0, 0), cta, font=font_small)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = button_x + (button_width - text_width) // 2
    text_y = button_y + (button_height - text_height) // 2
    draw.text((text_x, text_y), cta, fill='white', font=font_small)
    
    return img

def get_user_settings():
    """Get user settings from session, with defaults"""
    return {
        'default_ad_count': session.get('default_ad_count', DEFAULT_AD_COUNT),
        'max_ad_count': session.get('max_ad_count', MAX_AD_COUNT),
    }

@app.route('/')
def index():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    settings = get_user_settings()
    return render_template('index.html', settings=settings)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password and check_password_hash(PASSWORD_HASH, password):
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            default_count = int(request.form.get('default_ad_count', DEFAULT_AD_COUNT))
            max_count = int(request.form.get('max_ad_count', MAX_AD_COUNT))
            
            # Validate
            if default_count < 1 or default_count > 100:
                return render_template('settings.html', 
                                     error='Default ad count must be between 1 and 100',
                                     settings=get_user_settings())
            if max_count < 1 or max_count > 100:
                return render_template('settings.html',
                                     error='Max ad count must be between 1 and 100',
                                     settings=get_user_settings())
            if default_count > max_count:
                return render_template('settings.html',
                                     error='Default count cannot be greater than max count',
                                     settings=get_user_settings())
            
            # Save to session
            session['default_ad_count'] = default_count
            session['max_ad_count'] = max_count
            
            return render_template('settings.html',
                                 success='Settings saved successfully!',
                                 settings=get_user_settings())
        except ValueError:
            return render_template('settings.html',
                                 error='Invalid input. Please enter numbers only.',
                                 settings=get_user_settings())
    
    return render_template('settings.html', settings=get_user_settings())

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/generate', methods=['POST'])
def generate_ads():
    if 'authenticated' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        settings = get_user_settings()
        default_count = settings['default_ad_count']
        max_count = settings['max_ad_count']
        
        num_ads = int(request.json.get('count', default_count))
        if num_ads < 1 or num_ads > max_count:
            return jsonify({'error': f'Count must be between 1 and {max_count}'}), 400
        
        # Create output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f'temp_ads_{timestamp}'
        os.makedirs(output_dir, exist_ok=True)
        
        generated_images = []
        
        for i in range(num_ads):
            prompt, colors = generate_prompt_variation(i)
            
            # Extract text elements from prompt for fallback
            headline = prompt.split('Headline text: "')[1].split('"')[0] if 'Headline text: "' in prompt else "Connecticut Roofing"
            subheadline = prompt.split('Subheadline text: "')[1].split('"')[0] if 'Subheadline text: "' in prompt else "Expert Service"
            cta = prompt.split('Call-to-action button text: "')[1].split('"')[0] if 'Call-to-action button text: "' in prompt else "Get Started"
            
            # Always try to generate with Vertex AI API first
            print(f"Generating ad {i+1}/{num_ads} with Vertex AI...")
            img = generate_image_with_vertex_ai(prompt)
            
            if not img:
                # Only create placeholder if Vertex AI API fails
                print(f"Vertex AI generation failed for ad {i+1}, creating placeholder...")
                img = create_placeholder_image(headline, subheadline, cta, colors)
            else:
                print(f"Successfully generated ad {i+1} with Vertex AI API")
            
            # Save image
            filename = f'ad_{i+1:03d}.png'
            filepath = os.path.join(output_dir, filename)
            img.save(filepath, 'PNG')
            generated_images.append(filepath)
        
        # Create zip file
        zip_filename = f'connecticut_roofing_ads_{timestamp}.zip'
        zip_path = os.path.join(output_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for img_path in generated_images:
                zipf.write(img_path, os.path.basename(img_path))
        
        # Store zip path in session for download
        session['zip_file'] = zip_path
        session['zip_filename'] = zip_filename
        
        return jsonify({
            'success': True,
            'message': f'Generated {num_ads} ads successfully',
            'zip_filename': zip_filename,
            'download_url': url_for('download_zip')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download_zip():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    
    zip_path = session.get('zip_file')
    zip_filename = session.get('zip_filename', 'ads.zip')
    
    if not zip_path or not os.path.exists(zip_path):
        return jsonify({'error': 'Zip file not found'}), 404
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=zip_filename,
        mimetype='application/zip'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

