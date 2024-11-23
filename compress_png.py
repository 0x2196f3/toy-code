from PIL import Image
import os
import subprocess

def average_color(image_path):
    img = Image.open(image_path)
    img = img.convert('RGB')  # Ensure the image is in RGB mode
    width, height = img.size
    pixels = img.getdata()
    r, g, b = 0, 0, 0
    for pixel in pixels:
        r += pixel[0]
        g += pixel[1]
        b += pixel[2]
    r //= len(pixels)
    g //= len(pixels)
    b //= len(pixels)
    return (r, g, b)

def replace_with_average_color(image_path):
    avg_color = average_color(image_path)
    img = Image.open(image_path)
    img = img.convert('RGB')  # Ensure the image is in RGB mode
    width, height = img.size
    for x in range(width):
        for y in range(height):
            img.putpixel((x, y), avg_color)
    img.save(image_path)

def compress_png(image_path):
    subprocess.run(['pngquant', '--ext=.png', '--force', '--speed=1', image_path])

# Replace all images in the ./img directory
for filename in os.listdir('./'):
    if filename.endswith(".png"):
        image_path = os.path.join('./', filename)
        replace_with_average_color(image_path)
        compress_png(image_path)
        print(f"Processed {filename}")
