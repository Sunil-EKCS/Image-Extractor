import os
import time
import io
import imagehash
from PIL import Image
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['GIF_FOLDER'] = 'static/gifs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max file size: 16MB
app.config['ALLOWED_EXTENSIONS'] = {'gif'}

# Ensure the upload folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GIF_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def capture_animation_frames(url, output_dir, browser='chrome', num_frames=20, interval=1):
    if browser == 'chrome':
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
    elif browser == 'firefox':
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service)
    else:
        raise ValueError("Unsupported browser! Use 'chrome' or 'firefox'.")

    try:
        driver.get(url)
        time.sleep(3)  # Wait for the page to load and animation to start

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        previous_hash = None
        for i in range(num_frames):
            screenshot = driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot))

            current_hash = imagehash.phash(image)

            if previous_hash is None or current_hash != previous_hash:
                output_path = os.path.join(output_dir, f"frame_{i + 1}.png")
                image.save(output_path)
                print(f"Saved frame {i + 1} to {output_path}")

                previous_hash = current_hash
            else:
                print(f"Skipped duplicate frame {i + 1}")

            time.sleep(interval)

    finally:
        driver.quit()

def extract_frames(gif_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    if gif_path.startswith('file:///'):
        gif_path = gif_path[8:]

    with Image.open(gif_path) as img:
        for frame in range(img.n_frames):
            img.seek(frame)
            frame_path = os.path.join(output_folder, f"frame_{frame}.png")
            img.save(frame_path, "PNG")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'url' in request.form:
            url = request.form['url']
            try:
                output_dir = app.config['UPLOAD_FOLDER']
                capture_animation_frames(url, output_dir)

                saved_images = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]

                return render_template('index.html', images=saved_images)

            except Exception as e:
                return f"An error occurred: {e}", 400

        elif 'gif' in request.form:
            gif_path = request.form['gif']
            if not gif_path.startswith('file:///'):
                gif_path = 'file:///' + gif_path

            try:
                output_dir = app.config['UPLOAD_FOLDER']
                extract_frames(gif_path, output_dir)

                saved_images = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]

                return render_template('index.html', images=saved_images)

            except Exception as e:
                return f"An error occurred: {e}", 400

        elif 'clear' in request.form:
            # Clear images from UPLOAD_FOLDER
            for folder in [app.config['UPLOAD_FOLDER'], app.config['GIF_FOLDER']]:
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
            return redirect(url_for('index'))

        elif 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['GIF_FOLDER'], filename)
                file.save(file_path)
                
                output_dir = app.config['UPLOAD_FOLDER']
                extract_frames(file_path, output_dir)
                
                saved_images = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]

                return render_template('index.html', images=saved_images)

    return render_template('index.html')

@app.route('/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
