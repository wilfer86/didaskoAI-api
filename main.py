import os
import base64
from flask import Flask, request, jsonify
import google.generativeai as genai
from urllib.parse import quote

app = Flask(__name__)

# 1. Conectar con la clave secreta de Render
api_key = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=api_key)

# 2. La personalidad de Didasko
instrucciones_didasko = """
You are Didasko, an expert, wise and patient educational tutor.
Your name comes from the Greek 'διδάσκω' which means 'to teach'.
Your mission is to help students of primary, secondary and university levels worldwide.

Your capabilities:
- Write academic essays with good structure.
- Guide research with sources and methodology.
- Solve school problems step by step (math, science, history, etc.).
- Write personalized speeches (ask who will deliver it and what they want to convey).
- Analyze homework photos and solve them step by step.
- Read and explain text from images.

IMPORTANT LANGUAGE RULE:
- ALWAYS detect the language of the user's input.
- ALWAYS respond in the SAME language the user wrote to you.
- If the user writes in Spanish, respond in Spanish.
- If the user writes in English, respond in English.

Other rules:
- Be clear, didactic and encourage the student.
- Adapt your level: simple words for kids, academic tone for university.
- Always be respectful and motivating.
"""

# 3. Modelo de Gemini (texto + visión)
modelo = genai.GenerativeModel('gemini-2.5-flash-lite', system_instruction=instrucciones_didasko)

# RUTA 1: Bienvenida
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to DidaskoAI",
        "mensaje": "Bienvenido a DidaskoAI",
        "status": "running",
        "endpoints": ["/chat", "/vision", "/image"]
    })

# RUTA 2: Chat de texto
@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje_usuario = datos.get('message', '')

    if not mensaje_usuario:
        return jsonify({"error": "No message received"}), 400

    try:
        respuesta = modelo.generate_content(mensaje_usuario)
        return jsonify({"respuesta": respuesta.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RUTA 3: Analizar imagen (Gemini Vision)
@app.route('/vision', methods=['POST'])
def vision():
    datos = request.get_json()
    imagen_base64 = datos.get('image', '')
    pregunta = datos.get('message', 'Analiza esta imagen y ayúdame con lo que veas')

    if not imagen_base64:
        return jsonify({"error": "No image received"}), 400

    try:
        imagen_bytes = base64.b64decode(imagen_base64)
        imagen_parte = {
            "mime_type": "image/jpeg",
            "data": imagen_bytes
        }
        
        respuesta = modelo.generate_content([pregunta, imagen_parte])
        return jsonify({"respuesta": respuesta.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RUTA 4: Generar imagen (Pollinations) - CON FORMATOS
@app.route('/image', methods=['POST'])
def generate_image():
    datos = request.get_json()
    prompt = datos.get('prompt', '')
    formato = datos.get('format', '1:1')

    if not prompt:
        return jsonify({"error": "No prompt received"}), 400

    formatos = {
        "1:1": (1024, 1024),
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "4:3": (1024, 768),
        "3:4": (768, 1024),
        "2:3": (768, 1152),
        "3:2": (1152, 768),
        "21:9": (1536, 640),
        "banner": (1920, 480),
        "poster": (1024, 1536)
    }

    if formato not in formatos:
        return jsonify({
            "error": f"Formato no válido. Usa uno de: {list(formatos.keys())}"
        }), 400

    width, height = formatos[formato]

    try:
        prompt_codificado = quote(prompt)
        url_imagen = f"https://image.pollinations.ai/prompt/{prompt_codificado}?width={width}&height={height}&nologo=true"
        
        return jsonify({
            "url": url_imagen,
            "prompt": prompt,
            "formato": formato,
            "dimensiones": f"{width}x{height}",
            "mensaje": "Imagen generada exitosamente"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
