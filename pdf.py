
'''
Generate a Python function called `create_pdf_pages` that takes a list of a class that has 2 properties, image (as a PIL image) and prompt (as a string).
The function returns the pdf as a buffer of bytes 
The function should generate a multi-page PDF with one page for each image and caption. 
Each page should display the image and the corresponding caption. 
The font color should be a light grey.
The font should be Roboto, centered under the image, and the font size should be 18pt.
The image should fill the page and the caption should be centered below the image.
The PDF should be saved to a file called "output.pdf". 
Use the ReportLab library to generate the PDF.
Add debug logging for each line.
'''

'''
# Example usage
image1 = Image.open("image1.jpg")
caption1 = "This is the first image"
generated_image1 = GeneratedImage(image1, caption1)

image2 = Image.open("image2.jpg")
caption2 = "This is the second image"
generated_image2 = GeneratedImage(image2, caption2)

pages = [generated_image1, generated_image2]
pdf_bytes = create_pdf_pages(pages)
'''




from io import BytesIO
import textwrap
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader
from PIL import Image
def create_pdf_pages(title, pages):
    # Define the font and font size
    font = 'Roboto'
    pdfmetrics.registerFont(TTFont(font, 'Roboto-Regular.ttf'))

    # Define the light grey color
    grey = Color(0.7, 0.7, 0.7)

    # Define the page size and margin
    page_width, page_height = letter
    margin = inch / 4

    # Create a new PDF document
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)

    # Add the title page
    pdf.setFont(font, 36)
    pdf.setFillColor(grey)

    lines = textwrap.wrap(title, width=25)
    y = (page_height / 2) + 36
    for line in lines:
        pdf.drawCentredString(page_width / 2, y, line)
        y -= 40

    pdf.showPage()

    # Loop through each page and add the image and caption
    for i, page in enumerate(pages):
        # Calculate the position of the image and caption
        image_width, image_height = page.image.size
        image_aspect_ratio = image_width / image_height
        page_aspect_ratio = page_width / page_height
        if image_aspect_ratio > page_aspect_ratio:
            # Image is wider than page, so scale to fill width
            image_width = page_width - margin * 2
            image_height = image_width / image_aspect_ratio
        else:
            # Image is taller than page, so scale to fill height
            image_height = page_height - margin * 2
            image_width = image_height * image_aspect_ratio
        image_x = (page_width - image_width) / 2
        image_y = (page_height - image_height) / 2

        caption_y = image_y - (margin * 2)
        optimized_image = optimize_image(page.image)
        # Add the image and caption to the PDF
        pdf.drawImage(ImageReader(optimized_image), image_x,
                      image_y, image_width, image_height)
        pdf.setFillColor(grey)
        pdf.setFont(font, 18)
        # Word wrap the caption
        lines = textwrap.wrap(page.prompt, width=50)
        y = caption_y
        for line in lines:
            pdf.drawCentredString(page_width / 2, y, line)
            y -= 20

        # Add a new page if this is not the last page
        if i < len(pages) - 1:
            pdf.showPage()

    # Save the PDF document to a buffer
    pdf.save()
    pdf_buffer.seek(0)

    # Return the PDF buffer as bytes
    return pdf_buffer.read()


def optimize_image(image):
    # Convert the image to RGB mode if it is not already in that mode
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Resize the image to a reasonable size for use in a PDF
    max_size = (600, 600)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Apply JPEG compression to the image to reduce file size
    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=80)
    buffer.seek(0)
    optimized_image = Image.open(buffer)

    # Return the optimized image
    return optimized_image
