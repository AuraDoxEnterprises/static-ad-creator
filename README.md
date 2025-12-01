# Connecticut Roofing Ad Creator

An automated tool for generating unique static advertising images for Connecticut roofing services using Vertex AI/Gemini.

## Features

- 🔐 Password-protected web interface
- 🎨 Generates unique ad variations with different:
  - Headlines and subheadlines
  - Call-to-action buttons
  - Color schemes
  - Design styles
- 🏘️ Connecticut-focused content
- 🚫 No company names, phone numbers, or contact information
- 📦 Batch generation (1-100 ads at once)
- 💾 Automatic ZIP file packaging for easy download

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and set:
- `ADMIN_PASSWORD`: Your login password
- `GOOGLE_CLOUD_PROJECT_ID`: Your Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION`: Your Vertex AI location (default: us-central1)

3. **Set up Google Cloud authentication:**
```bash
gcloud auth application-default login
```

Or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file.

4. **Run the application:**
```bash
python app.py
```

5. **Access the web interface:**
Open your browser to `http://localhost:5000`

## Usage

1. Login with your password
2. Enter the number of ads to generate (1-100)
3. Click "Generate Ads"
4. Wait for generation to complete
5. Download the ZIP file containing all generated ads

## Technical Details

- **Framework**: Flask
- **Image Generation**: Vertex AI Imagen/Gemini
- **Image Format**: PNG (1200x628 pixels)
- **Output**: ZIP file containing all generated ads

## Notes

- Each ad is uniquely generated with variations in text, colors, and styling
- If Vertex AI image generation fails, placeholder images are created
- Generated files are stored temporarily and cleaned up after download
- All ads are Connecticut-focused but contain no contact information

