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

Other rules:
- Be clear, didactic and encourage the student.
- Adapt your level: simple words for kids, academic tone for university.
- Always be respectful and motivating.
"""

# 3. Modelo de Gemini (texto + visión)
modelo = genai.GenerativeModel('gemini-2.5-flash-lite', system_instruction=instrucciones_didasko)

# Función para mejorar el prompt automáticamente con Gemini
def mejorar_prompt(prompt_original):
    """Usa Gemini para convertir el prompt en uno más profesional"""
    try:
        instruccion = f"""
        Convierte este prompt en uno más detallado y profesional para generar una imagen de alta calidad.
        Agrega detalles sobre: iluminación, estilo, calidad, composición.
        Mantén la idea original pero hazla más rica.
        Responde SOLO con el prompt mejorado en INGLÉS, sin explicaciones.
        
        Prompt original: {prompt_original}
        """
        respuesta = modelo.generate_content(instruccion)
        return respuesta.text.strip()
    except:
        return prompt_original  # Si falla, usa el original

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

# RUTA 4: Generar imagen MEJORADA
@app.route('/image', methods=['POST'])
def generate_image():
    datos = request.get_json()
    prompt = datos.get('prompt', '')
    formato = datos.get('format', '1:1')
    modelo_img = datos.get('model', 'flux')  # flux, turbo
    mejorar = datos.get('enhance', True)  # Mejorar prompt automáticamente
    semilla = datos.get('seed', '')  # Para variar resultados

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
        # Si está activado, mejora el prompt con Gemini
        prompt_final = prompt
        if mejorar:
            prompt_mejorado = mejorar_prompt(prompt)
            prompt_final = prompt_mejorado

        # Agregar tags de calidad al prompt
        prompt_con_calidad = f"{prompt_final}, high quality, detailed, professional, 8k, masterpiece"
        
        prompt_codificado = quote(prompt_con_calidad)
        
        # Construir URL con parámetros
        url_imagen = f"https://image.pollinations.ai/prompt/{prompt_codificado}?width={width}&height={height}&model={modelo_img}&nologo=true&enhance=true"
        
        if semilla:
            url_imagen += f"&seed={semilla}"
        
        return jsonify({
            "url": url_imagen,
            "prompt_original": prompt,
            "prompt_mejorado": prompt_final,
            "formato": formato,
            "dimensiones": f"{width}x{height}",
            "modelo": modelo_img,
            "mensaje": "Imagen generada exitosamente"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
