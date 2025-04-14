# Import error logging packages
import logging
import traceback
import sys

# Set up logging to stderr
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Log startup info
logger.info("Starting application...")

# Basic imports
import base64
import os
import mimetypes
import uuid
import requests
import json
import io
import tempfile
import subprocess
import time
import random
import re
from pathlib import Path

# Import Flask and extensions - do this early
from flask import Flask, request, jsonify, send_from_directory, send_file, current_app, g
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import Unauthorized

# Create Flask app early to avoid circular imports
app = Flask(__name__, static_folder='public', static_url_path='')
logger.info("Flask app created")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
logger.info("Environment variables loaded")

# Import config after env vars are loaded
from config import config

# Get configuration mode
config_name = os.environ.get('FLASK_CONFIG', 'default')
# Clean up config_name if it's corrupted with other env vars
if ' ' in config_name:
    logger.warning(f"FLASK_CONFIG appears to be corrupted: {config_name}")
    # Extract the actual config name (first word)
    config_name = config_name.split(' ')[0]
    logger.info(f"Using extracted config name: {config_name}")

logger.info(f"Using configuration: {config_name}")

# Apply configuration with error handling
try:
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    logger.info("Configuration applied")
except KeyError:
    logger.error(f"Invalid config name: {config_name}, using default instead")
    app.config.from_object(config['default'])
    config['default'].init_app(app)
except Exception as e:
    logger.error(f"Error applying configuration: {str(e)}")
    logger.error(traceback.format_exc())
    # Use default configuration as fallback
    app.config.from_object(config['default'])
    config['default'].init_app(app)

# Import db and models
from models import db, User, Redesign
logger.info("Models imported")

# Initialize database with app
db.init_app(app)
logger.info("SQLAlchemy initialized")

# Create database tables within app context if needed
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        logger.error(traceback.format_exc())

# Initialize other extensions
from flask_migrate import Migrate
migrate = Migrate(app, db)
logger.info("Flask-Migrate initialized")

from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
jwt = JWTManager(app)
logger.info("JWTManager initialized")

# Set constants for anonymous usage
MAX_ANONYMOUS_USAGE = 3
ANONYMOUS_COOKIE_NAME = 'redesign_anonymous_id'

# Import auth after extensions and models
from auth import auth_bp, auth_required, track_redesign
app.register_blueprint(auth_bp, url_prefix='/auth')
logger.info("Auth blueprint registered")

# Configure proxy headers for cloud run
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
logger.info("ProxyFix applied")

# Ensure required directories exist
try:
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('generated', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    logger.info("Created required directories")
except Exception as e:
    logger.error(f"Error creating directories: {str(e)}")
    logger.error(traceback.format_exc())

# Make generated directory accessible to static file server
app.config['GENERATED_FOLDER'] = os.path.abspath('generated')
logger.info(f"GENERATED_FOLDER set to: {app.config['GENERATED_FOLDER']}")

# Initialize AI clients
# Load API keys from environment
API_KEY = os.environ.get("GEMINI_API_KEY")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-sonnet-20240229")
logger.info(f"Using CLAUDE_MODEL: {CLAUDE_MODEL}")

# Initialize the Gemini client
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=API_KEY)
    logger.info("Gemini client initialized")
except Exception as e:
    logger.error(f"Error initializing Gemini client: {str(e)}")
    logger.error(traceback.format_exc())
    client = None

# Import PIL last to avoid potential conflicts
try:
    from PIL import Image
    logger.info("PIL imported successfully")
except Exception as e:
    logger.error(f"Error importing PIL: {str(e)}")
    logger.error(traceback.format_exc())

# Define routes and other functions below this line
# ===================================================

# Minimal route for health check
@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"})

# Root route
@app.route('/')
def index():
    try:
        return send_from_directory('public', 'index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Error serving index page", "details": str(e)}), 500

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

# Add a more robust Claude API function with retries and detailed logging
def call_claude_api(payload, max_retries=2, timeout=90):
    """
    Call the Claude API with retries and comprehensive error handling
    Returns: (success, result, error_details)
    """
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    if not CLAUDE_API_KEY:
        logger.error("Claude API key is not set")
        return False, None, "API key not configured"
    
    # Log the API key length (without revealing the key)
    logger.info(f"Using Claude API key (length: {len(CLAUDE_API_KEY)})")
    logger.info(f"Using Claude model: {CLAUDE_MODEL}")
    
    # Retry logic
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"API attempt {attempt+1}/{max_retries+1} with timeout {timeout}s")
            
            # Make the request
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            # Log response details
            logger.info(f"Claude API response status: {response.status_code}")
            logger.info(f"Claude API response headers: {dict(response.headers)}")
            
            # Check for common error status codes
            if response.status_code == 429:
                logger.error("Claude API rate limit exceeded")
                error_msg = "Rate limit exceeded. Please try again later."
                # For rate limits, retry after a delay if not the last attempt
                if attempt < max_retries:
                    retry_after = int(response.headers.get('retry-after', 5))
                    logger.info(f"Retrying after {retry_after} seconds")
                    time.sleep(retry_after + 1)  # Add 1 second buffer
                    continue
                return False, None, error_msg
                
            elif response.status_code == 401:
                logger.error("Claude API authentication failed")
                return False, None, "API authentication failed"
                
            elif response.status_code == 413:
                logger.error("Claude API payload too large")
                return False, None, "Images are too large for Claude API"
                
            elif response.status_code != 200:
                # Try to parse error message from response
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", f"API Error: {response.status_code}")
                    logger.error(f"Claude API error: {error_msg}")
                except:
                    error_msg = f"Error from Claude API: {response.status_code}"
                    logger.error(f"Claude API error: {response.status_code} - {response.text[:200]}")
                
                # For server errors (5xx), retry if not the last attempt
                if 500 <= response.status_code < 600 and attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.info(f"Server error, retrying after {retry_delay} seconds")
                    time.sleep(retry_delay)
                    continue
                
                return False, None, error_msg
            
            # Try to parse the successful response
            try:
                result = response.json()
                logger.info("Successfully parsed Claude API response")
                return True, result, None
            except Exception as e:
                logger.error(f"Error parsing Claude API response: {str(e)}")
                logger.error(f"Response text: {response.text[:200]}")
                return False, None, f"Error parsing response: {str(e)}"
                
        except requests.exceptions.Timeout:
            logger.error(f"Claude API request timed out after {timeout} seconds")
            # For timeouts, retry with longer timeout if not the last attempt
            if attempt < max_retries:
                new_timeout = timeout * 1.5  # Increase timeout by 50%
                logger.info(f"Retrying with longer timeout: {new_timeout} seconds")
                timeout = new_timeout
                continue
            return False, None, f"The Claude API request timed out after {timeout}s. Please try again later."
            
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when calling Claude API")
            # For connection errors, retry if not the last attempt
            if attempt < max_retries:
                retry_delay = 2 ** attempt  # Exponential backoff
                logger.info(f"Connection error, retrying after {retry_delay} seconds")
                time.sleep(retry_delay)
                continue
            return False, None, "Network connection error. Please check your internet connection."
            
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {str(e)}")
            logger.error(traceback.format_exc())
            return False, None, f"Error: {str(e)}"

@app.route('/api/test-claude', methods=['GET'])
def test_claude():
    """Test the Claude API connection with a simple prompt"""
    try:
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello, can you confirm this is working? Just say 'Claude API is working!' and nothing else."}
                    ]
                }
            ]
        }
        
        logger.info("Making test request to Claude API")
        success, result, error = call_claude_api(payload, max_retries=1, timeout=30)
        
        if success:
            # Extract text from response
            if "content" in result and len(result["content"]) > 0 and "text" in result["content"][0]:
                response_text = result["content"][0]["text"]
                logger.info(f"Claude API response text: {response_text}")
                return jsonify({
                    "status": "success",
                    "message": "Claude API is working",
                    "response": response_text
                })
            else:
                logger.error("Unexpected response format")
                return jsonify({
                    "status": "error",
                    "message": "Unexpected response format",
                    "raw_response": result
                }), 500
        else:
            logger.error(f"Test failed: {error}")
            return jsonify({
                "status": "error", 
                "message": error
            }), 500
            
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/claude-suggestions', methods=['POST'])
@auth_required
@track_redesign
def generate_suggestions():
    try:
        if 'file' not in request.files and 'imageData' not in request.form and 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        # Get the image file or data
        if 'file' in request.files:
            file = request.files['file']
        elif 'image' in request.files:
            file = request.files['image']
        else:
            file = None
            
        # Process file upload if present
        if file:
            # Check if the file has a valid extension
            if not file.filename or '.' not in file.filename:
                return jsonify({'error': 'Invalid file'}), 400
                
            allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
            extension = file.filename.rsplit('.', 1)[1].lower()
            if extension not in allowed_extensions:
                return jsonify({'error': f'File type not allowed. Supported formats: {", ".join(allowed_extensions)}'}), 400
                
            # Read the file
            img_data = file.read()
            
            # Check file size
            if len(img_data) > 10 * 1024 * 1024:  # 10MB limit
                return jsonify({'error': 'File size too large (max 10MB)'}), 400
                
            # Save to temp file for resizing
            temp_input = Path(tempfile.mkdtemp()) / f"input.{extension}"
            with open(temp_input, 'wb') as f:
                f.write(img_data)
            
            # Log file size and type for debugging
            current_app.logger.info(f"Uploaded file: {file.filename}, size: {len(img_data) / 1024:.1f}KB, type: {extension}")
            
        else:  # imageData provided in form
            image_data = request.form.get('imageData', '')
            if not image_data.startswith('data:image/'):
                return jsonify({'error': 'Invalid image data format'}), 400
                
            # Extract the image format and data
            format_info, data = image_data.split(',', 1)
            mime_type = format_info.split(';')[0].split(':')[1]
            extension = mime_type.split('/')[1]
            if extension not in ['jpeg', 'png', 'webp']:
                return jsonify({'error': f'Image format not supported: {extension}'}), 400
                
            # Decode base64 data
            try:
                img_data = base64.b64decode(data)
                
                # Check file size
                if len(img_data) > 10 * 1024 * 1024:  # 10MB limit
                    return jsonify({'error': 'Image data too large (max 10MB)'}), 400
                    
                # Save to temp file for resizing
                temp_input = Path(tempfile.mkdtemp()) / f"input.{extension}"
                with open(temp_input, 'wb') as f:
                    f.write(img_data)
                
                # Log data size and type for debugging
                current_app.logger.info(f"Uploaded image data: size: {len(img_data) / 1024:.1f}KB, type: {extension}")
                
            except Exception as e:
                current_app.logger.error(f"Error decoding base64 image: {str(e)}")
                return jsonify({'error': 'Invalid image data encoding'}), 400
        
        # Get suggestion prompt from form - if absent, default to room redesign
        prompt = request.form.get('prompt', '')
        
        # If no custom prompt, build one from room type and style
        if not prompt:
            # Process room type and style from form data
            room_type = request.form.get('roomType', '').strip()
            style = request.form.get('style', '').strip()
            
            # Validate room type and style
            if not room_type:
                return jsonify({'error': 'Room type is required'}), 400
            if not style:
                return jsonify({'error': 'Style is required'}), 400
                
            # Log the request parameters
            current_app.logger.info(f"Redesign request - Room type: {room_type}, Style: {style}")
            
            # Prepare the prompt text
            prompt = f"""You are a professional interior designer. I need you to redesign a {room_type} in {style} style. 
        
Based on the uploaded image, suggest 5 specific redesign recommendations. For each suggestion:
1. Focus on specific, actionable changes
2. Include details about colors, materials, and furniture layout
3. Explain why the change works well with the space and style

Number each suggestion (1-5) and keep each to about 2-3 sentences.
                """
        
        # Resize the image to maximum dimensions while maintaining aspect ratio
        try:
            img = Image.open(temp_input)
            
            # Log original dimensions
            current_app.logger.info(f"Original image dimensions: {img.width}x{img.height}")
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                current_app.logger.info(f"Converting image from {img.mode} to RGB")
                # Create a new white background image
                bg = Image.new('RGB', img.size, (255, 255, 255))
                # Paste the image on the background using the alpha channel as mask
                if img.mode == 'RGBA':
                    bg.paste(img, mask=img.split()[3])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != 'RGB':
                current_app.logger.info(f"Converting image from {img.mode} to RGB")
                img = img.convert('RGB')
            
            # Maximum dimensions
            max_width = 2000
            max_height = 2000
            
            # Resize if needed
            if img.width > max_width or img.height > max_height:
                # Calculate new dimensions
                width_ratio = max_width / img.width
                height_ratio = max_height / img.height
                ratio = min(width_ratio, height_ratio)
                
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                
                current_app.logger.info(f"Resizing image to {new_width}x{new_height}")
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Save the processed image
            temp_processed = Path(tempfile.mkdtemp()) / "processed.jpg"
            img.save(temp_processed, format="JPEG", quality=85)
            
            # Log the processed file size
            processed_size = os.path.getsize(temp_processed)
            current_app.logger.info(f"Processed image size: {processed_size / 1024:.1f}KB, dimensions: {img.width}x{img.height}")
            
            # For API calls, use the processed image
            with open(temp_processed, "rb") as f:
                image_bytes = f.read()
                
        except Exception as e:
            current_app.logger.error(f"Image processing error: {str(e)}")
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500
            
        # Make the API call to Claude with retries
        max_retries = 3
        initial_delay = 2  # seconds
        current_app.logger.info(f"Calling Claude API with max_retries={max_retries}")
        
        for attempt in range(max_retries):
            try:
                # If this is a retry, log it
                if attempt > 0:
                    current_app.logger.info(f"Retry attempt {attempt} for Claude API call")
                
                current_app.logger.info("Initializing Claude API request...")
                
                # Configure API call settings based on retry attempt
                # For retries, we'll use longer timeouts and potentially reduce image quality
                timeout = 60 * (1 + attempt)  # Increase timeout on each retry
                
                # Call Claude API
                try:
                    # Configure the genai client
                    genai.configure(api_key=os.environ.get("ANTHROPIC_API_KEY"))
                    
                    current_app.logger.info(f"Sending request to Claude API with timeout {timeout}s")
                    
                    # Create a message with the image
                    response = genai.chat(
                        model="claude-3-5-sonnet-20240620",
                        messages=[
                            {
                                "role": "user", 
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "bytes",
                                            "media_type": "image/jpeg",
                                            "data": image_bytes
                                        }
                                    },
                                    {
                                        "type": "text", 
                                        "text": prompt
                                    }
                                ]
                            }
                        ],
                        max_tokens=1024,
                        timeout=timeout
                    )
                    
                    # Extract the response text
                    suggestions_text = response.content or ""
                    current_app.logger.info(f"Claude API response received: {len(suggestions_text)} characters")
                    
                    # If we got here, the API call succeeded, so break the retry loop
                    break
                    
                except Exception as api_error:
                    error_str = str(api_error)
                    current_app.logger.error(f"Claude API error: {error_str}")
                    
                    # Check specific error types and determine if we should retry
                    should_retry = False
                    
                    # Check for retryable errors (502, 503, 504, timeout, connection errors)
                    if any(code in error_str for code in ["502", "503", "504"]):
                        current_app.logger.info(f"Gateway error from Claude API, will retry: {error_str}")
                        should_retry = True
                    elif "timeout" in error_str.lower():
                        current_app.logger.info(f"Timeout error from Claude API, will retry: {error_str}")
                        should_retry = True
                    elif "connection" in error_str.lower():
                        current_app.logger.info(f"Connection error with Claude API, will retry: {error_str}")
                        should_retry = True
                    
                    # If this is the last attempt or not a retryable error, raise it
                    if not should_retry or attempt == max_retries - 1:
                        raise
                    
                    # Calculate backoff delay with jitter (random variance to prevent thundering herd)
                    delay = initial_delay * (2 ** attempt) * (0.75 + (random.random() * 0.5))
                    current_app.logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                
            except Exception as e:
                # This catches errors outside the API call itself
                current_app.logger.error(f"Error during Claude API processing: {str(e)}")
                
                # Check if this is the last attempt
                if attempt == max_retries - 1:
                    # Format user-friendly error message
                    error_message = str(e)
                    if "429" in error_message:
                        return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
                    elif "403" in error_message:
                        return jsonify({'error': 'API access forbidden. Please check your API key.'}), 403
                    elif "413" in error_message:
                        return jsonify({'error': 'Image too large for processing. Please use a smaller image.'}), 413
                    elif any(code in error_message for code in ["502", "503", "504"]):
                        return jsonify({'error': 'Gateway error from AI service. Please try again in a few moments.'}), 502
                    else:
                        return jsonify({'error': f'Error generating suggestions: {str(e)}'}), 500
                
                # If not the last attempt, calculate backoff delay with jitter
                delay = initial_delay * (2 ** attempt) * (0.75 + (random.random() * 0.5))
                current_app.logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
        
        # Process the response
        if not suggestions_text:
            current_app.logger.error("Empty response from Claude API")
            return jsonify({'error': 'No suggestions received from AI. Please try again.'}), 500
        
        # Split the text into individual suggestions
        suggestions = []
        current_suggestion = ""
        
        # Process multiline response
        for line in suggestions_text.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check if this is a new suggestion (starts with a number)
            if re.match(r'^\d+[\.\)]', line):
                # If we have a current suggestion, add it to the list
                if current_suggestion:
                    suggestions.append(current_suggestion.strip())
                
                # Start a new suggestion
                current_suggestion = line
            else:
                # Continue the current suggestion
                current_suggestion += " " + line
        
        # Add the last suggestion
        if current_suggestion:
            suggestions.append(current_suggestion.strip())
        
        # Clean up suggestions
        clean_suggestions = []
        for i, suggestion in enumerate(suggestions):
            # Remove the number prefix
            suggestion = re.sub(r'^\d+[\.\)]\s*', '', suggestion)
            clean_suggestions.append(suggestion)
        
        # Ensure we have exactly 5 suggestions
        if len(clean_suggestions) < 5:
            current_app.logger.warning(f"Only received {len(clean_suggestions)} suggestions, expected 5")
            # Fill in missing suggestions if needed
            room_type_fallback = request.form.get('roomType', 'room')
            style_fallback = request.form.get('style', 'modern')
            while len(clean_suggestions) < 5:
                clean_suggestions.append(f"Consider updating the {room_type_fallback} with elements that match the {style_fallback} style.")
        elif len(clean_suggestions) > 5:
            current_app.logger.warning(f"Received {len(clean_suggestions)} suggestions, trimming to 5")
            clean_suggestions = clean_suggestions[:5]
        
        # Log the extracted suggestions
        current_app.logger.info(f"Extracted {len(clean_suggestions)} suggestions")
        for i, s in enumerate(clean_suggestions):
            current_app.logger.info(f"Suggestion {i+1}: {s[:50]}...")
        
        return jsonify({
            'suggestions': clean_suggestions
        })
            
    except Exception as e:
        # Catch-all for other errors
        current_app.logger.error(f"Unexpected error in generate_suggestions: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

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