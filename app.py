import io
import json
import pickle
from flask import Flask, render_template_string, send_file, send_file, abort, url_for
import openai
import base64
import os
import requests
from PIL import Image
from io import BytesIO
from pdf import create_pdf_pages
import logging
from flask_basicauth import BasicAuth

from utils import make_url_safe

# Set the DEBUG_GENERATE and DEBUG_PDF flags to False
DEBUG_GENERATE = False
DEBUG_PDF = False

# Create a Flask app instance
app = Flask(__name__)

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

# Define a Flask route for the root URL


@app.route('/')
def index():
    # Get a list of PDF files in the pdfs directory
    pdf_files = [f for f in os.listdir('pdfs') if f.endswith('.pdf')]

    # Generate a list of anchors linking to the PDF files
    anchors = ''.join(
        [f'<li><a href="/pdf/{f}">{f}</a></li>' for f in pdf_files])

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
        <h2>PDF Files:</h2>
        <ul>
            {anchors}
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
    the_title, pdf_bytes = generate_pdf()

    # Return the PDF as a download to the user
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{the_title}.pdf'
    )


# Define a Flask route for the /debug URL
@app.route('/debug', methods=['GET'])
@basic_auth.required
def debug():
    # Generate an image using the generate_image function
    _, generated_image = generate_image()

    # Return the generated image as a response
    return generated_image


# Define a Flask route for the /generate URL
@app.route('/generate', methods=['GET'])
@basic_auth.required
def generate():
    # Generate an image using the generate_image function
    _, generated_images = generate_image()

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


image_cache = []

# Define a function called generate_image that generates a list of GeneratedImage objects using DALL-E


def generate_image(num_images=1):
    if len(image_cache) < num_images:
        needed_images = num_images - len(image_cache)
        # Define a list of messages to send to OpenAI's chat API to generate prompts
        messages = [
            {"role": "user", "content": f"Generate a JSON array of {needed_images} dalle prompts describing images of life's beauty, things like: nature, animals, math, geometry, science, checmistry, physics, space, planets, comets, stars and the earth, anything that is safe, real, and beautiful."},
            {"role": "user", "content": "Each prompt will be 15 words or less. Do not mention specific colors, these are coloring pages."},
            {"role": "user", "content": f"Output only one JSON array of strings with a length of {needed_images}."},
            {"role": "user",
                "content": '["prompt #1", "prompt #2"]'},

        ]

        # Send the messages to OpenAI's chat API to generate prompts
        prompt_response = openai.ChatCompletion.create(
            # You may need to update the engine depending on the latest available version
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150*needed_images
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
                prompt=f'{prompt} Do not add text or letters. Only use colors in the outline. Do not fill. As a complex, new coloring book page.',
                n=1,
                size='512x512',
            )

            # Get the image data and encode it as base64
            image_response = requests.get(response['data'][0]['url']).content
            low_res_img = Image.open(BytesIO(image_response))

            # Create a new GeneratedImage object and add it to the list of images
            image_cache.append(GeneratedImage(low_res_img, prompt))
            logging.debug("Generated image with prompt '%s'", prompt)
    imgs = image_cache[:num_images]
    del image_cache[:num_images]
    print("image_cache:", len(image_cache))
    the_title = None
    img_prompts = [image.prompt for image in imgs]
    if len(img_prompts) > 1:
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
        the_title = title_response.choices[0].message.content
        the_title = make_url_safe(the_title)
        logging.debug(f"Generated title: {the_title}")

    # Return the the_title and the list of generated images
    return the_title, imgs


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


def generate_pdf(num_pages=20) -> (str, bytes):
    logging.debug("Generating PDF with %d pages", num_pages)

    # Generate a list of GeneratedImage objects
    pages = []
    the_title, generated_images = generate_image(num_pages)

    # Loop over the generated images and add them to the pages list
    for i in range(len(generated_images)):
        generated_image = generated_images[i]

        # If DEBUG_GENERATE is True, save the generated image to a pickle file for debugging purposes
        if DEBUG_GENERATE:
            f = open(f"generated_image_{i}.pickle", "wb")
            pickle.dump(generated_image, f)
            f.close()

        # If DEBUG_PDF is True, load the generated image from a pickle file for debugging purposes
        if DEBUG_PDF:
            f = open(f"generated_image_{i}.pickle", "rb")
            generated_image = pickle.load(f)
            f.close()

        # Add the generated image to the pages list and log a message
        pages.append(generated_image)
        logging.debug("Generated image %d with prompt '%s'",
                      i+1, generated_image.prompt)

    # Generate the PDF using the create_pdf_pages function
    pdf_bytes = create_pdf_pages(pages)
    logging.debug("Generated PDF with %d bytes", len(pdf_bytes))
    with open(f'./pdfs/{the_title}.pdf', 'wb') as f:
        f.write(pdf_bytes)

    # Return the PDF as a buffer of bytes
    return the_title, pdf_bytes


# If this script is run directly, start the Flask app
if __name__ == '__main__':
    ssl_context = ('/certs/server.pem', '/certs/server.key')
    the_port = int(os.environ.get('PORT', 8443))
    app.run(debug=False, host='0.0.0.0',
            port=the_port, ssl_context=ssl_context)
