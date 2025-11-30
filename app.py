from flask import Flask, request, send_file, render_template, jsonify
from rembg import remove
from PIL import Image
import io
import os

app = Flask(__name__)

# Configure max upload size (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/')
def index():
    """Serve the landing page"""
    return render_template('index.html')

@app.route('/api/remove-background', methods=['POST'])
def remove_background():
    """
    API endpoint to remove background from uploaded image
    Returns the processed image with transparent background
    """
    try:
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read the image file
        input_image = Image.open(file.stream)
        
        # Remove background using rembg (returns PIL Image with transparent background)
        output_image = remove(input_image)
        
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
    app.run(debug=True, host='0.0.0.0', port=5000)
