import os
from flask import Flask, render_template, request, redirect, url_for, flash # Removed send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv # If using .env method

# --- Cloudinary Imports ---
import cloudinary
import cloudinary.uploader
import cloudinary.api # Optional: for managing assets later

# --- Load Environment Variables (if using .env) ---
load_dotenv() # Load variables from .env file

# --- Initialize Flask App ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_default_secret_key_for_dev') # Use env var for secret key too!

# --- Cloudinary Configuration ---
try:
    cloudinary.config(
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key = os.environ.get("CLOUDINARY_API_KEY"),
        api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
        secure=True
    )
    app.logger.info("Cloudinary configured successfully.")
except Exception as e:
    app.logger.error(f"Error configuring Cloudinary: {e}")
    # Depending on your needs, you might want to exit or handle this differently
    # For now, we'll let it continue but uploads will fail.

# --- Allowed Extensions (Define Image vs Video) ---
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'wmv', 'mkv', 'webm'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # 500 MB limit

# --- Helper Function ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_resource_type(filename):
    """Determine if the file is an image or video based on extension."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else None
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    else:
        return 'auto' # Let Cloudinary try to detect

# --- Event Data (No changes needed here) ---
event_details = {
    "haldi": {
        "title": "Haldi Ceremony",
        "description": "Join us for the vibrant and joyful Haldi ceremony...",
        "date": "Friday, October 25, 2024",
        "time": "11:00 AM onwards",
        "venue": "The Grand Hall - Garden Area",
        "venue_maps_link": "https://maps.google.com/?q=...",
        "bg_image_path": "img/haldi_bg.jpg",        # Used in event.html
        "card_image_path": "img/haldi_card.jpg",
        "details": "The engagement ceremony marks the formal agreement to wed. Historically, it involved the exchange of rings or gifts as a promise of marriage. Our ceremony will blend traditional customs with modern celebration."
    },
    "sangeet": {
        "title": "Sangeet Night",
        "description": "Get ready to dance the night away...",
        "date": "Saturday, October 26, 2024",
        "time": "7:00 PM onwards",
        "venue": "The Crystal Ballroom",
        "venue_maps_link": "https://maps.google.com/?q=...",
        "bg_image_path": "img/sangeet_bg.jpg",
        "card_image_path": "img/sangeet_card.jpg",
        "details": "The engagement ceremony marks the formal agreement to wed. Historically, it involved the exchange of rings or gifts as a promise of marriage. Our ceremony will blend traditional customs with modern celebration."
    },
    "wedding": {
        "title": "Wedding Ceremony & Reception",
        "description": "Witness our union as we exchange vows...",
        "date": "Sunday, October 27, 2024",
        "time": "5:00 PM (Ceremony), 7:30 PM (Reception)",
        "venue": "Oceanview Banquet Center",
        "venue_maps_link": "https://maps.google.com/?q=...",
        "bg_image_path": "img/wedding_bg.jpg",
        "card_image_path": "img/wedding_card.jpg",
        "details": "The engagement ceremony marks the formal agreement to wed. Historically, it involved the exchange of rings or gifts as a promise of marriage. Our ceremony will blend traditional customs with modern celebration."
    }
}

# --- Routes ---
@app.route('/')
def index():
    # Pass the event_details dictionary to the template with the key 'events'
    # The 'welcome_bg_url' variable seems unused in your index.html template,
    # but we can leave it for now or remove it if definitely not needed.
    welcome_bg = url_for('static', filename='img/welcome_bg.jpg') # Or relevant image
    return render_template('index.html',
                           welcome_bg_url=welcome_bg,
                           events=event_details)
@app.route('/main')
def main_page():
    return render_template('main.html', events=event_details)

@app.route('/event/<event_name>')
def show_event(event_name):
    details = event_details.get(event_name)
    if not details:
        return "Event not found", 404
    allowed_extensions_str = ', '.join(sorted(list(ALLOWED_EXTENSIONS)))
    return render_template('event.html',
                           event_name=event_name,
                           details=details,
                           ALLOWED_EXTENSIONS_STR=allowed_extensions_str)

# --- MODIFIED UPLOAD ROUTE ---
@app.route('/upload/<event_name>', methods=['POST'])
def upload_file(event_name):
    if event_name not in event_details:
        flash('Invalid event specified.', 'danger')
        return redirect(url_for('main_page'))

    if 'file' not in request.files:
        flash('No file part in the request.', 'warning')
        return redirect(url_for('show_event', event_name=event_name))

    file = request.files['file'] # This is a FileStorage object

    if file.filename == '':
        flash('No selected file.', 'warning')
        return redirect(url_for('show_event', event_name=event_name))

    # Check allowed extensions FIRST
    if not allowed_file(file.filename):
        disallowed_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
        flash(f'File type ".{disallowed_type}" not allowed.', 'danger')
        return redirect(url_for('show_event', event_name=event_name))

    # If file is allowed, proceed to upload to Cloudinary
    try:
        # Determine resource type (image/video)
        resource_type = get_resource_type(file.filename)
        # Use secure_filename for the public_id base, or let Cloudinary generate one
        # Using a folder is good practice for organization
        sanitized_filename = secure_filename(file.filename)

        app.logger.info(f"Attempting to upload '{sanitized_filename}' to Cloudinary folder '{event_name}' as type '{resource_type}'")

        # The 'file' object (FileStorage) can be directly passed to upload
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"wedding_uploads/{event_name}", # Organizes in Cloudinary console
            public_id=sanitized_filename.rsplit('.', 1)[0], # Use filename without extension as public_id (optional)
            resource_type=resource_type,
            overwrite=True # Or False if you don't want to replace files with the same name
        )

        app.logger.info(f"Cloudinary upload successful: {upload_result.get('secure_url')}")
        flash(f'Successfully uploaded: {sanitized_filename}', 'success')
        # You could potentially store upload_result['secure_url'] in a database here if needed later

    except Exception as e:
        app.logger.error(f"Cloudinary upload failed: {e}")
        flash(f'An error occurred during upload to cloud: {e}', 'danger')

    # Redirect back to the event page regardless of success/failure
    return redirect(url_for('show_event', event_name=event_name))


# --- Run the App ---
if __name__ == '__main__':
    # No need to create local upload folders anymore
    port = int(os.environ.get('PORT', 5000)) # Use PORT environment variable if available (for deployment)
    # Set debug=False for production/deployment
    app.run(debug=True, host='0.0.0.0', port=port)