# ChatGPT+DALL-E Coloring Pages (coloring-py)

This is a Python script that generates coloring pages using DALL-E and OpenAI's GPT-3. The script generates a prompt using GPT-3 that describes a nature scene featuring an animal or some other natural thing. The prompt is used to generate an image using DALL-E. The script then uses GPT-3 to generate a caption for the image that summarizes the image description provided in the prompt. The script can generate a single image or a multi-page PDF with one page for each image and caption.

## Requirements

- Python 3.7 or higher
- OpenAI API key

## Installation

1. Clone the repository:

```
git clone https://github.com/openai/dall-e-coloring-pages.git

```

2. Install the required packages:

```
pip install -r requirements.txt

```

3. Set your OpenAI API key as an environment variable:

```
export OPENAI_API_KEY=

```

## Usage

To start the Flask app, run the following command in your terminal from the root directory of the project:

```
python app.py

```

This will start the Flask app and make it available at `http://localhost:5000`.

## Generate 1 image

`http://localhost:5000/generate`

![coloring-py](https://github.com/jothflee/coloring-py/raw/main/docs/coloring_py.png)

## Generate a [PDF](https://github.com/jothflee/coloring-py/raw/main/docs/coloring_pages.pdf)

`http://localhost:5000/pdf`
