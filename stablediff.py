'''
Create a Python script that uses the StableDiffusionLatentUpscalePipeline from the Hugging Face Transformers library to upscale a low-resolution image using a provided prompt. 
The script should define a function called `upscale_image` that takes two arguments: a prompt (as a string) and a low-resolution image (as a PIL image). 
The function should use the StableDiffusionLatentUpscalePipeline to upscale the image and return the result as a PIL image. 
The function should call the pipeline with the provided prompt, the low-resolution image, `num_inference_steps=4`, `guidance_scale=0`, and `output_type='pil'`. 
The pipeline should be loaded from the "stabilityai/sd-x2-latent-upscaler" checkpoint.
'''

from PIL import Image
from transformers import StableDiffusionLatentUpscalePipeline


pipeline = StableDiffusionLatentUpscalePipeline.from_pretrained(
    "stabilityai/sd-x2-latent-upscaler"
)


def upscale_image(prompt, low_res_img):
    # Upscale the image using Diffusion Models
    high_res_img = pipeline(
        prompt=prompt,
        image=low_res_img,
        num_inference_steps=4,
        guidance_scale=0,
        output_type='pil'
    )
    return high_res_img
