import base64
import os
import mimetypes
import uuid
import requests
import json
import io
import tempfile
import subprocess
import sys
import time
import random
from pathlib import Path
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory, send_file, current_app, g
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import Unauthorized

# Import models and authentication
from models import db
from auth import auth_bp, auth_required, track_redesign, ANONYMOUS_COOKIE_NAME, MAX_ANONYMOUS_USAGE
from config import config

# Load environment variables from .env file
load_dotenv()

# Get environment configuration
config_name = os.environ.get('FLASK_CONFIG') or 'default'

# Create Flask app
app = Flask(__name__, static_folder='public', static_url_path='')

# Apply configuration
app.config.from_object(config[config_name])
config[config_name].init_app(app)

# Configure proxy headers for cloud run
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize extensions
jwt = JWTManager(app)
db.init_app(app)
migrate = Migrate(app, db)

# Verify database connection on startup
with app.app_context():
    try:
        # Try to connect to the database
        db.engine.connect()
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        # Don't crash, let the migration tool handle this
        pass

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')

# Ensure uploads and generated directories exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('generated', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Make generated directory accessible to static file server
app.config['GENERATED_FOLDER'] = os.path.abspath('generated')

# Load API keys from environment
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set. Please set it in your .env file.")

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY environment variable not set. Please set it in your .env file.")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-sonnet-20240229")

# Initialize the Gemini client
client = genai.Client(api_key=API_KEY)

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        # Text-only request
        model = "gemini-1.5-flash"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=message),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="text/plain",
        )
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        return jsonify({"text": response.text, "images": []})
    
    except Exception as e:
        print(f"Error in text chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat-with-image', methods=['POST'])
def chat_with_image():
    try:
        message = request.form.get('message', '')
        is_preview_processing = message == 'Processing HEIC preview'
        
        # Check for uploaded image
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({"error": "No image provided"}), 400
        
        # Process the uploaded image (handles HEIC conversion)
        try:
            image_path = process_uploaded_image(image_file)
            print(f"Processed image saved to {image_path}")
        except Exception as e:
            return jsonify({"error": f"Error processing image: {str(e)}"}), 400
        
        # For preview processing, just return the processed image path
        if is_preview_processing:
            # Generate a unique filename for the preview image
            preview_name = f"image_preview_{uuid.uuid4()}.jpg"
            preview_path = f"generated/{preview_name}"
            
            # Copy the processed image to a preview location
            import shutil
            shutil.copy(image_path, preview_path)
            
            # Clean up the uploaded file
            os.remove(image_path)
            
            # Return the preview image URL
            preview_url = f"/generated/{preview_name}"
            return jsonify({
                "text": "Preview processed",
                "images": [preview_url]
            })
        
        # Regular image generation flow continues below
        # Get mime type
        mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        
        # Upload file to Gemini
        uploaded_file = client.files.upload(file=image_path)
        
        # Initialize the model
        model = "gemini-2.0-flash-exp-image-generation"
        
        # Create content with image and text
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=uploaded_file.mime_type,
                    ),
                    types.Part.from_text(text=message),
                ],
            ),
        ]
        
        # Configure generation
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_modalities=["image", "text"],
            response_mime_type="text/plain",
        )
        
        # List to store generated image names
        generated_images = []
        response_text = ""
        
        # Stream response to capture both text and images
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue
                
            part = chunk.candidates[0].content.parts[0]
            
            # If chunk contains image data
            if hasattr(part, 'inline_data') and part.inline_data:
                file_name = f"generated/image_{uuid.uuid4()}"
                inline_data = part.inline_data
                file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
                full_path = f"{file_name}{file_extension}"
                
                # Save the image
                with open(full_path, "wb") as f:
                    f.write(inline_data.data)
                
                # Get the filename without the full path
                filename = os.path.basename(full_path)
                
                # Add to list of generated images (web path)
                # Use a relative URL that can be served by Flask
                image_web_path = f"/generated/{filename}"
                generated_images.append(image_web_path)
                
                print(f"Generated image saved to: {full_path}")
                print(f"Image will be served at: {image_web_path}")
                
                # Double check file exists
                if os.path.exists(full_path):
                    print(f"Confirmed file exists at: {full_path}")
                else:
                    print(f"WARNING: File does not exist at: {full_path}")
            else:
                # Accumulate text response
                if hasattr(chunk, 'text'):
                    response_text += chunk.text
        
        # Clean up the uploaded file
        os.remove(image_path)
        
        return jsonify({
            "text": response_text,
            "images": generated_images
        })
    
    except Exception as e:
        print(f"Error in image generation: {str(e)}")
        return jsonify({"error": str(e)}), 500

def process_uploaded_image(file, prefix=""):
    """Process an uploaded image file, handling various formats including HEIC/HEIF."""
    # Generate a unique filename with optional prefix
    original_filename = file.filename
    extension = os.path.splitext(original_filename)[1].lower()
    
    # Check if this is a HEIC/HEIF image
    is_heic = extension in ['.heic', '.heif'] or (file.content_type and ('heic' in file.content_type.lower() or 'heif' in file.content_type.lower()))
    
    if is_heic:
        print(f"Detected HEIC image: {original_filename}")
        print("Attempting to convert HEIC to JPEG...")
        
    # Save the original file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
        file.save(temp.name)
        temp_path = temp.name
    
    # Generate output path with standard extension and prefix
    output_path = f"uploads/{prefix}{uuid.uuid4()}.jpg"
    
    # Ensure the uploads directory exists
    os.makedirs("uploads", exist_ok=True)
    
    try:
        # Try opening the image with PIL first
        try:
            with Image.open(temp_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA'):
                    print(f"Converting image from {img.mode} to RGB")
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.split()[1])
                    img = background
                elif img.mode != 'RGB':
                    print(f"Converting image from {img.mode} to RGB")
                    img = img.convert('RGB')
                
                # Save as JPEG
                img.save(output_path, format='JPEG', quality=95)
                print(f"Image processed and saved to {output_path}")
                
                # Clean up temp file
                os.remove(temp_path)
                return output_path
                
        except Exception as img_error:
            print(f"Error opening image with PIL: {str(img_error)}")
            
            # If this is a HEIC image, try external conversion tools
            if is_heic:
                print("Trying external tools for HEIC conversion...")
                
                # Try different conversion methods depending on platform
                conversion_success = False
                
                # Try method 1: Use sips (macOS)
                if not conversion_success and sys.platform == 'darwin':
                    try:
                        print("Trying sips for conversion (macOS)...")
                        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', 'best', 
                                        temp_path, '--out', output_path], 
                                       check=True, capture_output=True)
                        conversion_success = os.path.exists(output_path)
                        if conversion_success:
                            print("HEIC conversion with sips succeeded")
                    except Exception as e:
                        print(f"sips conversion failed: {str(e)}")
                
                # Try method 2: Use ImageMagick if available
                if not conversion_success:
                    try:
                        print("Trying ImageMagick for conversion...")
                        subprocess.run(['convert', temp_path, output_path], 
                                      check=True, capture_output=True)
                        conversion_success = os.path.exists(output_path)
                        if conversion_success:
                            print("HEIC conversion with ImageMagick succeeded")
                    except Exception as e:
                        print(f"ImageMagick conversion failed: {str(e)}")
                
                # Try method 3: Use heif-convert if available
                if not conversion_success:
                    try:
                        print("Trying heif-convert for conversion...")
                        subprocess.run(['heif-convert', temp_path, output_path], 
                                      check=True, capture_output=True)
                        conversion_success = os.path.exists(output_path)
                        if conversion_success:
                            print("HEIC conversion with heif-convert succeeded")
                    except Exception as e:
                        print(f"heif-convert conversion failed: {str(e)}")
                
                # If any conversion method worked, return the output path
                if conversion_success:
                    # Clean up temp file
                    os.remove(temp_path)
                    return output_path
                else:
                    # If all conversions failed, notify the user but don't hard error
                    print("All HEIC conversion methods failed")
                    os.remove(temp_path)
                    raise ValueError("Unable to convert HEIC image. Please convert it to JPEG before uploading.")
            
            # For non-HEIC images that PIL couldn't open, try a generic approach
            print("Trying to handle as a generic image format...")
            
            # For non-HEIC images, we can try using a different approach or format
            if not is_heic:
                # Copy the file with a more common extension
                with open(temp_path, 'rb') as src_file:
                    with open(output_path, 'wb') as dest_file:
                        dest_file.write(src_file.read())
                print(f"File copied to {output_path} - will attempt to process")
                
                # Clean up temp file
                os.remove(temp_path)
                return output_path
            else:
                raise ValueError("Unsupported image format. Please upload JPEG, PNG, or GIF images.")
                
    except Exception as e:
        # Clean up temp file if still exists
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Error processing uploaded image: {str(e)}")
        raise

def make_claude_request(url, headers, payload, max_retries=3, initial_delay=1):
    for attempt in range(max_retries):
        try:
            claude_response = requests.post(url, headers=headers, json=payload)
            
            # If successful, return the response
            if claude_response.status_code == 200:
                return claude_response
                
            # If overloaded, wait and retry
            if claude_response.status_code == 529:
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.1)  # exponential backoff with jitter
                    print(f"Claude API overloaded, retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                    
            # For other errors, raise immediately
            claude_response.raise_for_status()
            
        except Exception as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.1)
                print(f"Error making Claude API request: {str(e)}, retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                continue
            raise
    
    # If we get here, all retries failed
    raise Exception(f"Claude API still overloaded after {max_retries} retries")

@app.route('/api/claude-suggestions', methods=['POST'])
@auth_required
def claude_suggestions():
    try:
        print("Received request for Claude suggestions")
        print(f"USING CLAUDE MODEL: {CLAUDE_MODEL}")
        
        # Check if we have two images
        if 'original' not in request.files or 'inspiration' not in request.files:
            return jsonify({"error": "Both original and inspiration images are required"}), 400
        
        original_file = request.files['original']
        inspiration_file = request.files['inspiration']
        
        # Process and save the uploaded images
        try:
            # Save original image with a prefix to identify it later
            original_temp = process_uploaded_image(original_file, prefix="original_")
            inspiration_temp = process_uploaded_image(inspiration_file, prefix="inspiration_")
            
            print(f"Saved original image to {original_temp}")
            print(f"Saved inspiration image to {inspiration_temp}")
        except Exception as e:
            return jsonify({"error": f"Error processing images: {str(e)}"}), 400
        
        # Resize images to ensure they're under 1MB for Claude API
        def resize_image(image_path):
            print(f"Original image size: {os.path.getsize(image_path) / (1024 * 1024):.2f} MB")
            
            # Open the image
            img = Image.open(image_path)
            
            # Convert to RGB if image has an alpha channel (RGBA)
            if img.mode in ('RGBA', 'LA'):
                print(f"Converting image from {img.mode} to RGB")
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.split()[1])
                img = background
            elif img.mode != 'RGB':
                print(f"Converting image from {img.mode} to RGB")
                img = img.convert('RGB')
            
            # Initialize quality and max_size
            quality = 90
            max_size = (1024, 1024)  # Initial max dimensions
            
            # Create a BytesIO object to store the compressed image
            img_byte_arr = io.BytesIO()
            
            # Resize and compress until under 1MB
            while True:
                # Resize image, maintaining aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Clear the BytesIO object
                img_byte_arr.seek(0)
                img_byte_arr.truncate(0)
                
                # Save to BytesIO with compression
                img.save(img_byte_arr, format='JPEG', quality=quality)
                
                # Check size
                size_mb = len(img_byte_arr.getvalue()) / (1024 * 1024)
                print(f"Resized image size: {size_mb:.2f} MB, Dimensions: {img.size}, Quality: {quality}")
                
                # If under 1MB, we're done
                if size_mb < 0.95:  # Giving a small buffer
                    break
                
                # If still too large, reduce quality or size further
                if quality > 50:
                    quality -= 10
                else:
                    # Reduce dimensions
                    max_size = (int(max_size[0] * 0.9), int(max_size[1] * 0.9))
                
                # Safety check to prevent infinite loop
                if max_size[0] < 300 or quality < 20:
                    print("Warning: Image quality significantly reduced to meet size requirements")
                    break
            
            # Return the compressed image data
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()
        
        # Resize both images
        print("Resizing original image...")
        original_data = resize_image(original_temp)
        print("Resizing inspiration image...")
        inspiration_data = resize_image(inspiration_temp)
        
        # Encode images to base64
        original_base64 = base64.b64encode(original_data).decode('utf-8')
        inspiration_base64 = base64.b64encode(inspiration_data).decode('utf-8')
        
        # Define our prompt for Claude
        prompt = """I'm sharing two images: the first is my current room, and the second is an inspiration room design I like. I want you to respond with design suggestions for the current room, inspired by the inspiration image to transform the current room to match the STYLE of the inspiration image, while preserving the FUNCTION and LAYOUT of the current room. Do not change the purpose of any area in the current room - only suggest style updates. I am  going to be giving your suggestions directly to an AI image editing tool to edit the image of the current room. That tool will have access to the current room but NOT the inspirational image. 
Return ONLY a JSON array with your suggestions, with no additional text before or after. Each suggestion should have a "title" and "description" property. Example format:
 [ { "title": "sample title", 
"description": "Sample description. The rest of the room should remain unchanged." }, 
{ "title": "sample title", 
"description": "Sample description. The rest of the room should remain unchanged." } ] 
Please format your suggestions in a numbered list (1, 2, 3) where each suggestion is very specific. Each suggestion should be a standalone edit that I can implement one at a time without professional help or major construction. For each suggestion:
Focus on one simple design element at a time (like bedding, wall decor, small furniture)
Keep it budget-friendly and easy to execute as a DIY project
Be specific about what to change and what to add
End each suggestion with the phrase "The rest of the room should remain unchanged."
Remember that I want to make these changes sequentially, so organize them in a logical order where each change complements the previous ones. Order suggestions from most structural to most decorative (for example, wall treatments should come before furniture style changes, which should come before accessories). Follow a "big to small" and "background to foreground" approach for the most efficient transformation sequence.
IMPORTANT: Do not suggest changing the function of any area (e.g., don't turn a TV wall into a bed wall). Keep each area's primary purpose exactly as shown in my current room image, while only updating the style elements to match the aesthetic of the inspiration image.
Don't suggest changes that would require professional installation or major renovations.
I'll be using these suggestions with an AI image editing tool, so make them clear, specific, and easy to implement.
Return ONLY the JSON array with exactly 3 suggestions, with no additional text before or after."""
        
        # Prepare the API request to Claude
        claude_url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        print(f"Preparing request with Claude model: {CLAUDE_MODEL}")
        
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": original_base64
                            }
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": inspiration_base64
                            }
                        }
                    ]
                }
            ]
        }
        
        # Make the request to Claude API with retries
        print("Sending request to Claude API")
        claude_response = make_claude_request(claude_url, headers, payload)
        
        response_data = claude_response.json()
        content = response_data.get("content", [])
        
        # Extract the text response
        suggestion_text = ""
        for item in content:
            if item.get("type") == "text":
                suggestion_text += item.get("text", "")
        
        print(f"Claude response: {suggestion_text}")
        
        # Parse the JSON response from Claude
        try:
            import json
            suggestions_data = json.loads(suggestion_text)
            
            # Validate response format
            if not isinstance(suggestions_data, list) or len(suggestions_data) != 3:
                print("Warning: Claude didn't return properly formatted JSON array with 3 items")
                return jsonify({"error": "Invalid response format from Claude"}), 500
                
            # Extract titles and descriptions
            suggestions = []
            for item in suggestions_data:
                title = item.get("title", "")
                description = item.get("description", "")
                
                if not title or not description:
                    print("Warning: Missing title or description in Claude response")
                    continue
                    
                suggestions.append({
                    "title": title,
                    "description": description
                })
            
            # Ensure we have exactly 3 suggestions
            if len(suggestions) != 3:
                print(f"Warning: Expected 3 suggestions, got {len(suggestions)}")
                return jsonify({"error": "Couldn't generate 3 valid suggestions"}), 500
                
            print(f"Parsed suggestions: {suggestions}")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from Claude: {e}")
            print(f"Raw response: {suggestion_text}")
            return jsonify({"error": "Failed to parse Claude response as JSON"}), 500
        except Exception as e:
            print(f"Error processing Claude response: {e}")
            return jsonify({"error": f"Error processing Claude response: {str(e)}"}), 500
        
        # Get user info for tracking
        # Get user_id from JWT or anonymous_id from cookie
        user_id = None
        anonymous_id = None
        
        # Try to get user ID from token
        try:
            # Check for JWT Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                from flask_jwt_extended import decode_token
                token = auth_header.split(' ')[1]
                # Extract user ID from token
                decoded = decode_token(token)
                user_id = decoded.get('sub')
        except:
            pass
        
        # If no user ID, get anonymous ID from cookie
        if not user_id:
            anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
        
        # Track this redesign
        track_redesign(
            user_id=user_id,
            anonymous_id=anonymous_id,
            original_path=original_temp,
            inspiration_path=inspiration_temp,
            suggestions_data=suggestions_data
        )
        
        # Clean up temp files
        try:
            os.remove(original_temp)
            os.remove(inspiration_temp)
        except Exception as e:
            print(f"Error cleaning up temp files: {str(e)}")
        
        return jsonify({"suggestions": suggestions})
        
    except Exception as e:
        print(f"Error in claude_suggestions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-results', methods=['POST'])
def save_results():
    try:
        data = request.json
        result_image_url = data.get('result_image')
        suggestions = data.get('suggestions', [])
        
        # Remove the leading path as we'll be reading from the filesystem
        result_file = result_image_url.replace('/generated/', 'generated/')
        
        # Check if the result file exists
        if not os.path.exists(result_file):
            print(f"Result file not found: {result_file}")
            return jsonify({"error": "Result image not found"}), 404
        
        # Format suggestions for clipboard
        suggestion_text = ""
        for i, suggestion in enumerate(suggestions):
            suggestion_text += f"{i+1}. {suggestion.get('title')}\n"
            suggestion_text += f"{suggestion.get('description')}\n\n"
        
        # Instead of saving to downloads folder, create a download URL
        # Generate a unique filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"room_redesign_{timestamp}.jpg"
        
        # Store the original path and generate a download URL
        # We'll use a temporary mapping to handle the download
        app.config.setdefault('DOWNLOAD_MAPPING', {})
        download_id = str(uuid.uuid4())
        app.config['DOWNLOAD_MAPPING'][download_id] = {
            'file_path': result_file,
            'filename': download_filename,
            'timestamp': datetime.datetime.now()
        }
        
        # Create download URL
        download_url = f"/api/download/{download_id}"
        
        # Get user info for tracking the result
        user_id = None
        anonymous_id = None
        
        # Try to get user ID from token
        try:
            # Check for JWT Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                from flask_jwt_extended import decode_token
                token = auth_header.split(' ')[1]
                # Extract user ID from token
                decoded = decode_token(token)
                user_id = decoded.get('sub')
        except:
            pass
        
        # If no user ID, get anonymous ID from cookie
        if not user_id:
            anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
            
        # Update redesign record with result image
        if user_id or anonymous_id:
            from models import Redesign
            
            # Find the most recent redesign by this user
            if user_id:
                redesign = Redesign.query.filter_by(user_id=user_id).order_by(Redesign.created_at.desc()).first()
            else:
                redesign = Redesign.query.filter_by(anonymous_id=anonymous_id).order_by(Redesign.created_at.desc()).first()
                
            # If found, update with result image
            if redesign:
                redesign.result_image_path = result_file
                db.session.commit()
        
        # Return success with download URL and clipboard content
        return jsonify({
            "success": True,
            "message": "Image ready for download",
            "clipboard_content": suggestion_text,
            "download_url": download_url
        })
    
    except Exception as e:
        print(f"Error preparing download: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<download_id>', methods=['GET'])
def download_file(download_id):
    try:
        # Get the file information from our mapping
        download_mapping = app.config.get('DOWNLOAD_MAPPING', {})
        if download_id not in download_mapping:
            return "Download expired or not found", 404
        
        file_info = download_mapping[download_id]
        file_path = file_info['file_path']
        filename = file_info['filename']
        
        # Check if the file exists
        if not os.path.exists(file_path):
            return "File not found", 404
            
        # Create a high-quality JPEG version of the image
        try:
            img = Image.open(file_path)
            
            # Convert to RGB if needed (required for JPEG)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.split()[1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Create a BytesIO object to hold the image data
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG', quality=95)
            img_io.seek(0)
            
            # Remove the download mapping after use (cleanup)
            download_mapping.pop(download_id, None)
            
            # Set headers to force download
            response = send_file(
                img_io,
                as_attachment=True,
                download_name=filename,
                mimetype='image/jpeg'
            )
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            return response
        except Exception as e:
            print(f"Error processing image for download: {str(e)}")
            return str(e), 500
            
    except Exception as e:
        print(f"Error in download: {str(e)}")
        return str(e), 500

# Serve static files from public directory
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('public', path)

# Serve generated images
@app.route('/generated/<path:filename>')
def serve_generated_image(filename):
    print(f"Attempting to serve image: {filename}")
    print(f"From directory: {app.config['GENERATED_FOLDER']}")
    
    file_path = os.path.join(app.config['GENERATED_FOLDER'], filename)
    
    if os.path.exists(file_path):
        print(f"Image file exists at: {file_path}")
        return send_file(file_path)
    else:
        print(f"Image file does not exist at: {file_path}")
        return "Image not found", 404

@app.route('/api/usage/count', methods=['GET'])
def get_usage_count():
    """Get the remaining anonymous usage count"""
    anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
    
    if not anonymous_id:
        # No anonymous ID yet, so full remaining usage
        response = jsonify({
            "usage_count": 0,
            "remaining": MAX_ANONYMOUS_USAGE,
            "authenticated": False
        })
        
        # Create a new anonymous ID
        new_anonymous_id = str(uuid.uuid4())
        response.set_cookie(ANONYMOUS_COOKIE_NAME, new_anonymous_id, max_age=60*60*24*365, httponly=True, samesite='Strict')
        return response
    
    # Check for JWT Authorization to see if user is logged in
    is_authenticated = False
    try:
        # Check for JWT Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # User has a token, they're authenticated
            is_authenticated = True
    except:
        pass
    
    if is_authenticated:
        # Authenticated users have unlimited usage
        return jsonify({
            "usage_count": 0,
            "remaining": "unlimited",
            "authenticated": True
        })
    
    # Get usage count for anonymous ID
    from models import Redesign
    usage_count = Redesign.query.filter_by(anonymous_id=anonymous_id).count()
    
    return jsonify({
        "usage_count": usage_count,
        "remaining": max(0, MAX_ANONYMOUS_USAGE - usage_count),
        "authenticated": False
    })

# Ensure the application listens on the port provided by Cloud Run
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 