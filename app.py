# app.py
import os
from flask import Flask, request, render_template, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads' # Not strictly needed if processing in memory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) # Create folder if it doesn't exist

@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/process_image', methods=['POST'])
def process_image():
    """
    Receives an image and text parameters, processes the image by adding text
    behind the detected person, and returns the modified image.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    image_file = request.files['image']
    text_input = request.form.get('text', 'Your Text Here')
    font_size = int(request.form.get('fontSize', 60))
    font_color = request.form.get('fontColor', '#000000')
    font_family = request.form.get('fontFamily', 'arial.ttf') # Default to a common font

    try:
        # 1. Open the original image
        img_bytes = image_file.read()
        original_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

        # Ensure image is large enough for font size, or scale font
        # For simplicity, let's assume images are reasonably sized.
        # If font size is too large for small images, it might look bad.

        # 2. Get the foreground (person) using rembg
        # rembg.remove returns an RGBA image with background removed
        # We need the mask or the foreground part.
        # Let's use the 'alpha_matting' method for better edges if available,
        # otherwise default to basic removal.
        try:
            foreground_img = remove(original_img, alpha_matting=True)
        except Exception:
            # Fallback if alpha_matting causes issues or is not supported in some environments
            foreground_img = remove(original_img)

        # Create a mask from the alpha channel of the foreground_img
        # Where alpha is > 0, it's part of the foreground.
        person_mask = foreground_img.split()[-1] # Get the alpha channel as a grayscale image

        # 3. Create a new image to draw the text on
        # This image will initially contain the original background + text
        # Then the foreground person will be pasted on top
        composite_img = original_img.copy()
        draw = ImageDraw.Draw(composite_img)

        # Load font
        try:
            # Try to load a specific font file if it exists (e.g., in a 'fonts' folder)
            # Or use a system font. This is tricky as system fonts vary.
            # For demonstration, we'll try a common font name or a default.
            # In a real app, you'd bundle fonts or use web fonts.
            font_path = os.path.join(os.path.dirname(__file__), 'fonts', font_family)
            if not os.path.exists(font_path):
                # Fallback to a generic font or Pillow's default
                font = ImageFont.truetype("arial.ttf", font_size) # Assumes arial.ttf is available on the system
            else:
                font = ImageFont.truetype(font_path, font_size)
        except IOError:
            # Fallback if the specified font is not found
            font = ImageFont.load_default()
            font_size = 20 # Default font is small, adjust size
            print(f"Warning: Could not load font '{font_family}'. Using default font.")

        # Calculate text position (center for simplicity, can be made dynamic)
        img_width, img_height = original_img.size
        text_bbox = draw.textbbox((0,0), text_input, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = (img_width - text_width) / 2
        text_y = (img_height - text_height) / 2

        # Draw text onto the composite image
        draw.text((text_x, text_y), text_input, font=font, fill=font_color)

        # 4. Paste the foreground (person) on top of the text
        # Use the person_mask as the mask for pasting, so only the person part is pasted
        composite_img.paste(foreground_img, (0, 0), person_mask)

        # 5. Save the result to a BytesIO object and send it
        byte_arr = io.BytesIO()
        composite_img.save(byte_arr, format='PNG')
        byte_arr.seek(0) # Rewind to the beginning of the stream

        return send_file(byte_arr, mimetype='image/png')

    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({'error': f'Image processing failed: {str(e)}'}), 500

if __name__ == '__main__':
    # For development, run with debug=True
    # For production, use a production-ready WSGI server like Gunicorn
    app.run(debug=True, port=5000)