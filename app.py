from flask import Flask, request, send_file, render_template, jsonify
from PIL import Image
import io
import os
from withoutbg import WithoutBG
from dotenv import load_dotenv
import requests

load_dotenv()

# Environment variables
turnstile_secret = os.getenv("TURNSTILE_SECRET_KEY")
turnstile_site_key = os.getenv("TURNSTILE_SITE_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

model = WithoutBG.opensource()

# Configure max upload size (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


# Configuring CF
def get_client_ip():
    """Get real client IP (works with Cloudflare)"""
    # Cloudflare sends real IP in CF-Connecting-IP header
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip
    
    # Fallback to X-Forwarded-For
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    
    # Final fallback
    return request.remote_addr

def verify_turnstile(token):
    """Verify Cloudflare Turnstile token"""
    if not token:
        app.logger.error("No Turnstile token provided")
        return False
    
    if not turnstile_secret:
        app.logger.error("TURNSTILE_SECRET_KEY not set in environment")
        return False
    
    try:
        client_ip = get_client_ip()
        
        app.logger.info(f"Verifying Turnstile token from IP: {client_ip}")
        
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': turnstile_secret,
                'response': token,
                'remoteip': client_ip  # THIS WAS MISSING!
            },
            timeout=10
        )
        
        result = response.json()
        
        app.logger.info(f"Turnstile verification result: {result}")
        
        if not result.get('success', False):
            app.logger.error(f"Turnstile verification failed: {result.get('error-codes', [])}")
        
        return result.get('success', False)
    
    except requests.exceptions.Timeout:
        app.logger.error("Turnstile verification timeout")
        return False
    except Exception as e:
        app.logger.error(f"Turnstile verification error: {str(e)}")
        return False


@app.route("/", methods=['GET'])
def index():
    """Landing page for SanoURL"""
    return render_template('index.html', turnstile_site_key=turnstile_site_key)

@app.route('/api/remove-background', methods=['POST'])
def remove_background():
    """
    API endpoint to remove background from uploaded image
    Returns the processed image with transparent background
    """
    try:
        # Verify Turnstile token
        turnstile_token = request.form.get('turnstile_token')
        
        if not verify_turnstile(turnstile_token):
            return jsonify({'error': 'Verification failed. Please try again.'}), 403
        
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read the image file
        input_image = file.read()
        
        # Remove background using WithoutBG (returns PIL Image)
        output_image = model.remove_background(input_image)
        
        # Save to bytes buffer
        img_io = io.BytesIO()
        output_image.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Return the processed image
        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name='clearcut_output.png'
        )
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500
        
@app.route('/health')
def health():
    """Health check endpoint"""

    return jsonify({'status': 'healthy', 'service': 'ClearCut Background Remover'})

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0')
