import os
import requests
import json
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

IMAGES_DIR = 'images'
if not os.path.exists(IMAGES_DIR):
    os.mkdir(IMAGES_DIR)
MAPPINGS_FILE = IMAGES_DIR + '/image_url_mappings.json'

if os.path.exists(MAPPINGS_FILE):
    with open(MAPPINGS_FILE, 'r') as f:
        image_url_mapping = json.load(f)
else:
    image_url_mapping = {}

def save_mappings():
    with open(MAPPINGS_FILE, 'w') as f:
        json.dump(image_url_mapping, f)

def stream_image(image_url):
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        return Response(response.iter_content(chunk_size=8192), content_type=response.headers['Content-Type'])
    else:
        return None

def generate_random_filename():
    return str(int.from_bytes(os.urandom(16), byteorder='big'))

def gen_photo(text, num, seed=-1, steps=50, guidance_scale=10, sampler='Euler a'):
    url = 'https://cognise.art/api/mobile/txt2img/generate/v4'
    head = {
        'Authorization': 'token 7bb91a6699cc3794750101ce0354d80195f07c04'
    }

    unique_user_uuid = generate_random_filename()

    js = {
        "batch_size": num,
        "generation_id": 7,
        "generation_prompt": text,
        "generation_seed": seed,
        "generation_steps": steps,
        "guidance_scale": guidance_scale,
        "hit_point": "mobile",
        "img_ratio": "square",
        "negative_prompt": "",
        "sampler_index": sampler,
        "sampler_name": sampler,
        "sid": 19,
        "tz": "Africa/Cairo",
        "user_uuid": unique_user_uuid
    }

    try:
        response = requests.post(url, headers=head, json=js)
        response.raise_for_status()
        results = response.json()
    except requests.exceptions.RequestException as e:
        return {"error": "Request failed"}

    image_urls = []
    if results and 'data' in results and 'images' in results['data']:
        images = results['data']['images']
        for img in images:
            remote_image_url = 'https://storage.cognise.art' + img['image']
            unique_filename = generate_random_filename() + '.jpg'
            local_image_url = request.host_url + 'images/' + unique_filename
            image_urls.append(local_image_url)
            image_url_mapping[unique_filename] = remote_image_url
        save_mappings()
    else:
        return {"error": "No images found"}

    return {"image_urls": image_urls, "TG": "@SI_Sl"}

@app.route('/')
def welcome():
    return {"Welcome": "to API to generate images use(e.x. : /generate?text=dog&amount=1)", "TG": "@SI_Sl"}

@app.route('/generate')
def try_to_gen():
    num = request.args.get('amount')
    text = request.args.get('text')

    if not num or not text:
        return {"error": "Please use: {}generate?amount=number-of-images&text=your-prompt".format(request.host_url)}

    try:
        num = int(num)
    except ValueError:
        return {"error": "Amount should be an integer (only numbers)!"}

    if num > 4:
        return {"error": "You can't generate more than 4 images in one request"}
    
    try:
        results = gen_photo(text, num)
        return jsonify(results)
    except Exception as e:
        return {"error": str(e)}

@app.route('/images/<filename>')
def serve_image(filename):
    if filename in image_url_mapping:
        image_url = image_url_mapping[filename]
        return stream_image(image_url)
    else:
        return {"error": "Image not found"}, 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
