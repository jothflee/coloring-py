import io
import json
import pickle
from flask import Flask, render_template_string, send_file, send_file, abort, redirect
import openai
import base64
import os
import requests
from PIL import Image
from io import BytesIO
from pdf import create_pdf_pages
import logging
import threading
from flask_basicauth import BasicAuth
from flask_ipban import IpBan

from utils import make_title_clean, make_url_safe

# Create a Flask app instance
app = Flask(__name__)
ip_ban = IpBan(persist=True, ban_count=5,
               ban_seconds=3600*24*7, ipc=True)

ip_ban.init_app(app)

# Set the OpenAI API key
openai.api_key = os.environ['OPENAI_API_KEY']

# Configure the logging module to log debug messages
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

app.config['BASIC_AUTH_USERNAME'] = 'username'
app.config['BASIC_AUTH_PASSWORD'] = 'password'

username = os.environ.get('BASIC_AUTH_USERNAME')
password = os.environ.get('BASIC_AUTH_PASSWORD')

# Set the BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD values in the Flask app config
if username and password:
    app.config['BASIC_AUTH_USERNAME'] = username
    app.config['BASIC_AUTH_PASSWORD'] = password

basic_auth = BasicAuth(app)

os.makedirs("./pdfs", exist_ok=True)
os.makedirs("./pdfs2", exist_ok=True)
os.makedirs('./raws', exist_ok=True)

# Define a Flask route for the root URL


@app.route('/')
def index():
    # Get a list of PDF files in the pdfs directory
    pdf_files = [f for f in os.listdir('pdfs') if f.endswith('.pdf')]

    # Get a list of PDF files made with dall-e-2 in the pdfs directory
    pdf_files_2 = [f for f in os.listdir('pdfs2') if f.endswith('.pdf')]

    # Generate a list of anchors linking to the PDF files
    anchors = ''.join(
        [f'<li><a href="/pdf/{f}">{f}</a></li>' for f in pdf_files])

    # Generate a list of anchors linking to the PDF files
    anchors_2 = ''.join(
        [f'<li><a href="/pdf/{f}">{f}</a></li>' for f in pdf_files_2])

    # Add some basic styles
    style = """
    <style>
    body {
        font-family: Arial, sans-serif;
        font-size: 16px;
        line-height: 1.5;
        margin: 0;
        padding: 0;
        background-color: #f5f5f5;
    }
    a {
        color: #007bff;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    hr {
        border: none;
        border-top: 1px solid #ccc;
        margin: 1em 0;
    }
    .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 1em;
        background-color: #fff;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    }
    h1, h2 {
        margin-top: 0;
    }
    ul {
        list-style: none;
        margin: 0;
        padding: 0;
    }
    li {
        margin-bottom: 0.5em;
    }
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
        <ul>
            {anchors}
        </ul>
        <h2>PDF Files (Dall-E 2):</h2>
        <ul>
            {anchors_2}
        </ul>
    </div>
    </body>
    </html>
    """
# Define a Flask route for the /pdf URL with a filename parameter


@app.route('/pdf/<path:filename>')
def get_pdf(filename):
    # Get the full path to the PDF file
    filepath = os.path.join('pdfs', filename)

    # Check if the file exists and is a PDF
    if not os.path.isfile(filepath) or not filepath.endswith('.pdf'):
        abort(404)

    # Return the PDF file to the client
    return send_file(filepath, mimetype='application/pdf')

# Define a Flask route for the /pdfgen URL


@app.route('/pdfgen')
@basic_auth.required
def generate_pdf_route():
    # Generate the PDF using the generate_pdf function
    # Start a new thread to generate the PDF
    thread = threading.Thread(target=generate_pdf_background)
    thread.start()
    # Return the PDF as a download to the user
    return redirect('/')


# Define a Flask route for the /generate URL
@app.route('/generate', methods=['GET'])
@basic_auth.required
def generate():
    # Generate an image using the generate_image function
    generated_images = load_generated_images(generate_image())

    if len(generated_images) == 0:
        return "No images generated"
    generated_image = generated_images[0]

    # Save the generated image to a file for debugging purposes
    generated_image.image.save("high.jpg")

    # Encode the generated image as a base64 string
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

    # Return the HTML response
    return html


'''
Create a Python script that generates an image using DALL-E and OpenAI's GPT-3. 
The script should define a function called `generate_image` that takes no arguments. 
The function should use GPT-3 to generate a prompt that describes a nature scene featuring an animal or some other natural thing. 
The prompt should be used to generate an image using DALL-E. The function should then use GPT-3 to generate a caption for the image. 
The caption should summarize the image description provided in the prompt. 
The function should return the low-resolution image, the prompt, and the caption as a tuple. 
The DALL-E image should be generated using the OpenAI Image API with the prompt as input and a size of 1024x1024. 
The GPT-3 prompts should be generated using the OpenAI Chat API with the "gpt-3.5-turbo" model and a maximum of 100 tokens.
'''


# Define a class called GeneratedImage that represents an image generated by DALL-E
class GeneratedImage:
    def __init__(self, image, prompt):
        self.image = image
        self.prompt = prompt


def load_image_cache():
    # Get a list of all the pickled files in the raws directory
    directory_path = './raws'
    filenames = os.listdir(directory_path)
    return [os.path.join(directory_path, f) for f in filenames if f.endswith('.pickle')]


# Define a function called generate_image that generates a list of GeneratedImage objects using DALL-E
def generate_image(num_images=1):
    image_cache = load_image_cache()
    print("image_cache:", len(image_cache))

    if len(image_cache) < num_images:
        needed_images = num_images - len(image_cache)
        # Define a list of messages to send to OpenAI's chat API to generate prompts
        messages = [
            {"role": "user", "content": "You only output valid raw JSON."},
            {"role": "user", "content": f"Output an array of strings. Each element is a prompt for dall-e to generate a coloring book page. The array should have a length of {needed_images}."},
            {"role": "user", "content": "Each prompt will be concise. Do not mention specific colors."},
            {"role": "user", "content": "Chose random, safe topics, for example: nature, animals, math, geometry, science, checmistry, physics, space, planets, comets, stars and the earth."},
            {"role": "user", "content": "Keep a positive tone for each prompt."},
            {"role": "user", "content": "Chose a unique artistic style for each prompt."},
            {"role": "user", "content": "Choose a random detail and be sepcific in each prompt."},
            {"role": "user", "content": 'Example output: ["prompt #1", "prompt #2"]'},
        ]

        # Send the messages to OpenAI's chat API to generate prompts
        prompt_response = openai.ChatCompletion.create(
            # You may need to update the engine depending on the latest available version
            model="gpt-4o",
            messages=messages,
            max_tokens=150*needed_images,
        )

        # Parse the generated prompts from the response
        prompts_response = prompt_response.choices[0].message.content
        logging.debug("Generated prompts: %s", prompts_response)

        try:
            prompts = json.loads(prompts_response)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            prompts = []
        # Generate an image for each prompt using DALL-E

        for prompt in prompts:
            # Generate the image using DALL-E
            response = openai.Image.create(
                model = "dall-e-3",
                prompt=f'{prompt} Do not add text or letters. Only use colors in the outline. Do not fill any portion of the image. Do not generate humans. Create a complex, coloring book page.',
                n=1,
                size='1024x1024',
            )

            # Get the image data and encode it as base64
            image_response = requests.get(response['data'][0]['url']).content
            low_res_img = Image.open(BytesIO(image_response))

            # Create a new GeneratedImage object with the low-res image and prompt
            image = GeneratedImage(low_res_img, prompt)

            # Save the GeneratedImage object as a pickled file
            filename = f'{make_url_safe(image.prompt)}.pickle'
            filepath = os.path.join('./raws', filename)
            with open(filepath, 'wb') as f:
                pickle.dump(image, f)

            # Log a debug message to indicate that the image was generated
            logging.debug("Generated image with prompt '%s'", prompt)

        image_cache = load_image_cache()

    imgs = image_cache[:num_images]

    # Return the the_title and the list of generated images
    return imgs


'''
Create a function called 'generate_pdf' that generates a multi-page PDF with one page for each image and caption.
It uses the function 'create_pdf_pages' from the pdf.py file to create the pdf.
create_pdf_pages returns a buffer of bytes, generate_pdf will return a buffer of bytes.
It uses the function 'generate_image' to generate the images and captions using the GeneratedImage class (image, caption, prompt).
It has 1 input num_pages which defaults to 5
Add debug logging for each line.
Add comments to explain each line.
'''

# Define a function called generate_pdf that takes an optional argument num_pages and returns a buffer of bytes


def generate_pdf(num_pages=20) -> (str):
    logging.debug("Generating PDF with %d pages", num_pages)

    # Generate a list of GeneratedImage objects
    pages = []
    generated_images = load_generated_images(generate_image(num_pages))

    if len(generated_images) == 0:
        return "No images generated", []

    the_title = generate_a_title(generated_images)

    if the_title == None:
        return None
    # Loop over the generated images and add them to the pages list
    for i in range(len(generated_images)):
        generated_image = generated_images[i]

        # Add the generated image to the pages list and log a message
        pages.append(generated_image)
        logging.debug("Generated image %d with prompt '%s'",
                      i+1, generated_image.prompt)

    # Generate the PDF using the create_pdf_pages function
    pdf_bytes = create_pdf_pages(the_title, pages)
    logging.debug("Generated PDF with %d bytes", len(pdf_bytes))
    file_name = make_url_safe(the_title)

    with open(f'./pdfs/{file_name}.pdf', 'wb') as f:
        f.write(pdf_bytes)

    # Return the PDF as a buffer of bytes
    return the_title


def load_generated_images(filepaths):
    return [load_generated_image(filepath) for filepath in filepaths]


def load_generated_image(filepath):
    with open(filepath, 'rb') as f:
        image = pickle.load(f)
    os.remove(filepath)
    return image


def generate_pdf_background():
    # Generate the PDF using the generate_pdf function
    the_title = generate_pdf()

    # Save the PDF to disk or upload to a cloud storage service
    # ...

    # Optionally send an email notification when the PDF is ready
    # ...
    if the_title == None:
        print("No PDF generated")
        return
    # Log a message to indicate that the PDF is ready
    print(f'PDF "{the_title}.pdf" is ready')


def generate_a_title(images):
    the_title = None
    img_prompts = [image.prompt for image in images]
    if len(img_prompts) > 0:
        title_response = openai.ChatCompletion.create(
            # You may need to update the engine depending on the latest available version
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Given the following JSON array of captions: {img_prompts}"},
                {"role": "user", "content": "Generate a short, no more than 6 word, uplifting title of the book that contains these pictures."},
                {"role": "user", "content": "The title should be exciting and not use the words: nature or nature's."},
            ],
            max_tokens=150
        )

        # Parse the generated prompts from the response
        the_title = make_title_clean(title_response.choices[0].message.content)
        logging.debug(f"Generated title: {the_title}")
    else:
        logging.debug("Only one image generated, no title generated")
    return the_title


# If this script is run directly, start the Flask app
if __name__ == '__main__':

    certfile = '/certs/server.pem'
    keyfile = '/certs/server.key'

    ssl_context = None
    if os.path.exists(certfile) and os.path.exists(keyfile):
        ssl_context = (certfile, keyfile)
    the_port = int(os.environ.get('PORT', 8443))
    app.run(debug=False, host='0.0.0.0',
            port=the_port, ssl_context=ssl_context)
