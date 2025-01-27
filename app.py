import os
import pickle
import logging
import threading
import base64
import requests
import schedule
import time
import datetime
from flask import Flask, render_template_string, send_file, abort, redirect
from openai import OpenAI, BadRequestError
from PIL import Image
from io import BytesIO
from pydantic import BaseModel
from flask_basicauth import BasicAuth
from utils import make_title_clean, make_url_safe
from pdf import create_pdf_pages

# Set the OpenAI API key
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# Create a Flask app instance
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Basic Auth configuration
app.config['BASIC_AUTH_USERNAME'] = os.environ.get('BASIC_AUTH_USERNAME', 'username')
app.config['BASIC_AUTH_PASSWORD'] = os.environ.get('BASIC_AUTH_PASSWORD', 'password')
basic_auth = BasicAuth(app)

# Create necessary directories
os.makedirs("./pdfs", exist_ok=True)
os.makedirs("./pdfs2", exist_ok=True)
os.makedirs('./raws', exist_ok=True)

class Prompts(BaseModel):
    prompts: list[str]

class GeneratedImage:
    def __init__(self, image, prompt):
        self.image = image
        self.prompt = prompt

@app.route('/')
def index():
    pdf_files = [f for f in os.listdir('pdfs') if f.endswith('.pdf')]
    pdf_files_2 = [f for f in os.listdir('pdfs2') if f.endswith('.pdf')]
# Sort the files by creation date
    pdf_files_sorted = sorted(pdf_files, key=lambda f: os.path.getctime(os.path.join('pdfs', f)), reverse=True)
    pdf_files_2_sorted = sorted(pdf_files_2, key=lambda f: os.path.getctime(os.path.join('pdfs2', f)), reverse=True)
    anchors = ''.join([f'<li><a href="/pdf/{f}">{f}</a></li>' for f in pdf_files_sorted])
    anchors_2 = ''.join([f'<li><a href="/pdf/{f}">{f}</a></li>' for f in pdf_files_2_sorted])

    style = """
    <style>
    body { font-family: Arial, sans-serif; font-size: 16px; line-height: 1.5; margin: 0; padding: 0; background-color: #f5f5f5; }
    a { color: #007bff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    hr { border: none; border-top: 1px solid #ccc; margin: 1em 0; }
    .container { max-width: 800px; margin: 0 auto; padding: 1em; background-color: #fff; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }
    h1, h2 { margin-top: 0; }
    ul { list-style: none; margin: 0; padding: 0; }
    li { margin-bottom: 0.5em; }
    </style>
    """

    return f"""
    <html>
    <head>
    <title>coloring-py</title>
    {style}
    </head>
    <body>
    <div class="container">
        <h1>coloring-py</h1>
        <ul>
            <li><a href='/generate'>Generate One Page</a></li>
            <li><a href='/pdfgen'>Generate a PDF</a></li>
        </ul>
        <hr>
        <h2>PDF Files (Dall-E 3):</h2>
        <ul>{anchors}</ul>
        <h2>PDF Files (Dall-E 2):</h2>
        <ul>{anchors_2}</ul>
    </div>
    </body>
    </html>
    """

@app.route('/pdf/<path:filename>')
def get_pdf(filename):
    filepath = os.path.join('pdfs', filename)
    if not os.path.isfile(filepath) or not filepath.endswith('.pdf'):
        abort(404)
    return send_file(filepath, mimetype='application/pdf')

@app.route('/pdfgen')
@basic_auth.required
def generate_pdf_route():
    threading.Thread(target=generate_pdf_background).start()
    return redirect('/')

@app.route('/generate', methods=['GET'])
@basic_auth.required
def generate():
    generated_images = load_generated_images(generate_image())
    if not generated_images:
        return "No images generated"
    generated_image = generated_images[0]
    generated_image.image.save("high.jpg")
    buffered = BytesIO()
    generated_image.image.save(buffered, format="JPEG")
    image_data = base64.b64encode(buffered.getvalue()).decode('utf-8')
    html = render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Coloring Page</title>
        </head>
        <body>
            <div><img src="data:image/jpeg;base64,{{ image_data }}" alt="Coloring Page"></div>
            <h3>{{ caption }}</h3>
        </body>
        </html>
    ''', image_data=image_data, caption=generated_image.prompt)
    return html

def load_image_cache():
    directory_path = './raws'
    filenames = os.listdir(directory_path)
    return [os.path.join(directory_path, f) for f in filenames if f.endswith('.pickle')]

def generate_image(num_images=1, additional_prompts=None):
    image_cache = load_image_cache()
    while len(image_cache) < num_images:
        needed_images = num_images - len(image_cache)
        logging.info(f"generating {needed_images} prompts...")
        messages = [
            {"role": "user", "content": "You will only output valid raw JSON."},
            {"role": "user", "content": "Output an array of strings. Each element is a specific and descriptive prompt for DALL-E to generate a coloring book page. The array should have a length of {needed_images}."},
            {"role": "user", "content": "Choose random, safe, and positive topics/scenes, such as nature, animals, geometry, science (e.g., chemistry, physics, space, planets), and fantasy creatures."},
            {"role": "user", "content": "Ensure that each prompt maintains a positive tone and is suitable for all ages. Do not ask Dall-e to render humans."},
            {"role": "user", "content": "For each prompt, choose a unique and identifiable artistic style from history (e.g Art Nouveau, Renaissance, Ancient Egyptian, etc...) while keeping the design appropriate for a coloring book (clear outlines, simple shapes)."},
            {"role": "user", "content": "Include a specific detail in each prompt (e.g., 'a cat playing with a ball of yarn under a tree')."},
            {"role": "user", "content": "The output should be an array of strings in the following format: ['prompt #1', 'prompt #2', 'prompt #3', ...]"}
        ] + additional_prompts if additional_prompts else []

        prompt_response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=150*needed_images,
            response_format=Prompts
        )
        prompts = prompt_response.choices[0].message.parsed
        logging.debug("Generated prompts: %s", prompts)
        for prompt in prompts.prompts:
            try:
                logging.info("Generating image with prompt '%s'", prompt)
                response = client.images.generate(
                    model="dall-e-3",
                    prompt = f'Directions: Create a black-and-white line drawing with clear outlines and ample white space, suitable for a coloring book. Do not draw human figures. Do not add text or letters. Do not fill any areas. Leave plenty of unfilled spaces for coloring. Prompt: {prompt}',
                    n=1,
                    size='1024x1024',
                )
                image_response = requests.get(response.data[0].url).content
                low_res_img = Image.open(BytesIO(image_response))
                image = GeneratedImage(low_res_img, prompt)
                filename = f'{make_url_safe(image.prompt)}.pickle'
                filepath = os.path.join('./raws', filename)
                with open(filepath, 'wb') as f:
                    pickle.dump(image, f)
                logging.debug("Generated image with prompt '%s'", prompt)
            except BadRequestError as e:
                logging.debug("Error generating image: %s", e)
        image_cache = load_image_cache()
    return image_cache[:num_images]

def generate_pdf(num_pages=10,additional_prompts=[]) -> str:
    logging.info("Generating PDF with %d pages", num_pages)
    generated_images = load_generated_images(generate_image(num_pages, additional_prompts))
    if not generated_images:
        return "No images generated", []
    the_title = generate_a_title(generated_images)
    if not the_title:
        return None
    logging.info("Generated images: %d", len(generated_images))
    pdf_bytes = create_pdf_pages(the_title, generated_images)
    logging.info("Generated PDF with %d bytes", len(pdf_bytes))
    file_name = make_url_safe(the_title)
    with open(f'./pdfs/{file_name}.pdf', 'wb') as f:
        f.write(pdf_bytes)
    return the_title

def load_generated_images(filepaths):
    return [load_generated_image(filepath) for filepath in filepaths]

def load_generated_image(filepath):
    with open(filepath, 'rb') as f:
        image = pickle.load(f)
    os.remove(filepath)
    return image

def generate_pdf_background():
    # Get the current date
    current_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    # Define the additional prompts
    additional_prompts = [
        {"role": "user", "content": f"Today is the date {current_date}. Please make the images seasonally relevant."}
    ]

    the_title = generate_pdf(additional_prompts=additional_prompts)
    if not the_title:
        logging.warn("No PDF generated")
        return
    logging.info(f'PDF "{the_title}.pdf" is ready')

def generate_a_title(images):
    img_prompts = [image.prompt for image in images]
    if img_prompts:
        title_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"Given the following JSON array of captions: {img_prompts}"},
                {"role": "user", "content": "Generate a short, no more than 6 word, uplifting title of the book that contains these pictures."},
                {"role": "user", "content": "The title should be exciting and not use the words: nature or nature's."},
            ],
            max_tokens=150
        )
        the_title = make_title_clean(title_response.choices[0].message.content)
        logging.info(f"Generated title: {the_title}")
        return the_title
    logging.debug("Only one image generated, no title generated")
    return None

def schedule_pdf_generation():
    schedule.every().friday.at("00:00").do(generate_pdf_background)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # Start the background scheduler
    threading.Thread(target=schedule_pdf_generation, daemon=True).start()
    
    certfile = os.environ.get('CERTFILE', '/certs/server.pem')
    keyfile = os.environ.get('KEYFILE', '/certs/server.key')
    ssl_context = (certfile, keyfile) if os.path.exists(certfile) and os.path.exists(keyfile) else None
    the_port = int(os.environ.get('PORT', 8443))
    app.run(debug=False, host='0.0.0.0', port=the_port, ssl_context=ssl_context)