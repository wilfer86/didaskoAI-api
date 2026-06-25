import os
import base64
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai
from urllib.parse import quote

app = Flask(__name__)

# 1. Conectar con las claves secretas de Render
gemini_api_key = os.environ.get('GEMINI_API_KEY')
siliconflow_api_key = os.environ.get('SILICONFLOW_API_KEY')

genai.configure(api_key=gemini_api_key)

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

Other rules:
- Be clear, didactic and encourage the student.
- Adapt your level: simple words for kids, academic tone for university.
- Always be respectful and motivating.
"""

# 3. Modelo de Gemini (texto + visión)
modelo = genai.GenerativeModel('gemini-2.5-flash-lite', system_instruction=instrucciones_didasko)

# Función para mejorar el prompt con Gemini
def mejorar_prompt(prompt_original):
    """Convierte el prompt en uno más profesional en inglés"""
    try:
        instruccion = f"""
        Convert this prompt into a detailed, professional image generation prompt.
        Add: lighting, style, quality, composition details.
        Keep the original idea but enhance it.
        Respond ONLY with the enhanced prompt in ENGLISH, no explanations.
        
        Original: {prompt_original}
        """
        respuesta = modelo.generate_content(instruccion)
        return respuesta.text.strip()
    except:
        return prompt_original

# RUTA 1: Bienvenida
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to DidaskoAI",
        "mensaje": "Bienvenido a DidaskoAI",
        "status": "running",
        "endpoints": ["/chat", "/vision", "/image", "/image-flux"]
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

# RUTA 4: Generar imagen con Pollinations (RESPALDO)
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
        "3:2": (1152, 768)
    }

    width, height = formatos.get(formato, (1024, 1024))

    try:
        prompt_mejorado = mejorar_prompt(prompt)
        prompt_codificado = quote(prompt_mejorado)
        url_imagen = f"https://image.pollinations.ai/prompt/{prompt_codificado}?width={width}&height={height}&model=flux&nologo=true&enhance=true"
        
        return jsonify({
            "url": url_imagen,
            "prompt_original": prompt,
            "prompt_mejorado": prompt_mejorado,
            "modelo": "pollinations-flux",
            "mensaje": "Imagen generada exitosamente"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RUTA 5: Generar imagen con SiliconFlow Flux (PRINCIPAL - ALTA CALIDAD)
@app.route('/image-flux', methods=['POST'])
def generate_image_flux():
    datos = request.get_json()
    prompt = datos.get('prompt', '')
    formato = datos.get('format', '1:1')

    if not prompt:
        return jsonify({"error": "No prompt received"}), 400

    formatos = {
        "1:1": "1024x1024",
        "16:9": "1280x720",
        "9:16": "720x1280",
        "4:3": "1024x768",
        "3:4": "768x1024"
    }

    image_size = formatos.get(formato, "1024x1024")

    try:
        # Mejorar prompt con Gemini
        prompt_mejorado = mejorar_prompt(prompt)
        
        # Llamar a SiliconFlow
        url = "https://api.siliconflow.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {siliconflow_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": prompt_mejorado,
            "image_size": image_size,
            "num_inference_steps": 4,
            "guidance_scale": 1
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            url_imagen = data['images'][0]['url']
            
            return jsonify({
                "url": url_imagen,
                "prompt_original": prompt,
                "prompt_mejorado": prompt_mejorado,
                "modelo": "siliconflow-flux-schnell",
                "mensaje": "Imagen generada con alta calidad"
            })
        else:
            return jsonify({
                "error": f"SiliconFlow error: {response.text}",
                "status_code": response.status_code
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
