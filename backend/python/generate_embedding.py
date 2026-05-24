import sys
import json
import numpy as np
import requests
from PIL import Image
from io import BytesIO
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch

# init model (sekali load)
mtcnn = MTCNN(image_size=160)
model = InceptionResnetV1(pretrained='vggface2').eval()

def get_embedding(image_url):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content)).convert('RGB')

    face = mtcnn(img)

    if face is None:
        return None

    face = face.unsqueeze(0)
    embedding = model(face).detach().numpy()[0]

    return embedding.tolist()

if __name__ == "__main__":
    image_url = sys.argv[1]

    emb = get_embedding(image_url)

    if emb is None:
        print(json.dumps({"error": "no face detected"}))
    else:
        print(json.dumps(emb))