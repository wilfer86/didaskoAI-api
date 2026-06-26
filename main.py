import os
import base64
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai
from urllib.parse import quote

app = Flask(__name__)

# Claves
gemini_api_key = os.environ.get('GEMINI_API_KEY')
siliconflow_api_key = os.environ.get('SILICONFLOW_API_KEY')

genai.configure(api_key=gemini_api_key)

# Personalidad de Didasko (para DeepSeek y Gemini)
instrucciones_didasko = """Eres Didasko, un tutor educativo experto, sabio y paciente.
Tu nombre viene del griego 'διδάσκω' que significa 'enseñar'.
Tu misión es ayudar a estudiantes de primaria, secundaria y universidad de todo el mundo.

Capacidades:
- Escribir ensayos académicos con buena estructura
- Guiar investigaciones con fuentes y metodología
- Resolver problemas escolares paso a paso (matemáticas, ciencias, historia, etc.)
- Escribir discursos personalizados
- Analizar fotos de tareas y resolverlas
- Leer y explicar texto en imágenes

REGLA DE IDIOMA:
- Detecta el idioma del usuario y responde en el MISMO idioma
- Si te escribe en español, responde en español
- Si te escribe en inglés, responde en inglés

Reglas generales:
- Sé claro, didáctico y motivador
- Adapta el nivel: simple para niños, académico para universidad
- Sé respetuoso y motivador siempre"""

# Modelo Gemini para visión y respaldo
modelo_gemini = genai.GenerativeModel('gemini-2.5-flash-lite', system_instruction=instrucciones_didasko)

# Función para mejorar prompt de imagen
def mejorar_prompt(prompt_original):
    try:
        instruccion = f"""Convert this prompt into a detailed, professional image generation prompt.
Add: lighting, style, quality, composition details.
Keep the original idea but enhance it.
Respond ONLY with the enhanced prompt in ENGLISH, no explanations.

Original: {prompt_original}"""
        respuesta = modelo_gemini.generate_content(instruccion)
        return respuesta.text.strip()
    except:
        return prompt_original

# Función PRINCIPAL: DeepSeek V3 vía SiliconFlow
def chat_deepseek(mensaje_usuario):
    url = "https://api.siliconflow.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {siliconflow_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [
            {"role": "system", "content": instrucciones_didasko},
            {"role": "user", "content": mensaje_usuario}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        return data['choices'][0]['message']['content']
    else:
        raise Exception(f"DeepSeek error: {response.text}")

# Función RESPALDO: Gemini
def chat_gemini(mensaje_usuario):
    respuesta = modelo_gemini.generate_content(mensaje_usuario)
    return respuesta.text

# RUTA 1: Bienvenida
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to DidaskoAI",
        "mensaje": "Bienvenido a DidaskoAI",
        "status": "running",
        "endpoints": ["/chat", "/vision", "/image", "/image-flux", "/image-qwen"],
        "modelo_principal": "DeepSeek V3",
        "modelo_respaldo": "Gemini"
    })

# RUTA 2: Chat (DeepSeek principal + Gemini respaldo)
@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje_usuario = datos.get('message', '')

    if not mensaje_usuario:
        return jsonify({"error": "No message received"}), 400

    # Intentar primero con DeepSeek
    try:
        respuesta_texto = chat_deepseek(mensaje_usuario)
        return jsonify({
            "respuesta": respuesta_texto,
            "modelo": "deepseek-v3"
        })
    except Exception as e1:
        # Si falla DeepSeek, usar Gemini como respaldo
        try:
            respuesta_texto = chat_gemini(mensaje_usuario)
            return jsonify({
                "respuesta": respuesta_texto,
                "modelo": "gemini-respaldo"
            })
        except Exception as e2:
            return jsonify({
                "error": "Ambos modelos fallaron",
                "deepseek_error": str(e1),
                "gemini_error": str(e2)
            }), 500

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
        
        respuesta = modelo_gemini.generate_content([pregunta, imagen_parte])
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
        "9:16": (720, 1280)
    }

    width, height = formatos.get(formato, (1024, 1024))

    try:
        prompt_mejorado = mejorar_prompt(prompt)
        prompt_codificado = quote(prompt_mejorado)
        url_imagen = f"https://image.pollinations.ai/prompt/{prompt_codificado}?width={width}&height={height}&model=flux&nologo=true&enhance=true"
        
        return jsonify({
            "url": url_imagen,
            "modelo": "pollinations",
            "mensaje": "Imagen generada"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RUTA 5: Generar imagen con Flux Schnell
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
        "9:16": "720x1280"
    }

    image_size = formatos.get(formato, "1024x1024")

    try:
        prompt_mejorado = mejorar_prompt(prompt)
        
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
            return jsonify({
                "url": data['images'][0]['url'],
                "modelo": "flux-schnell",
                "mensaje": "Imagen generada"
            })
        else:
            return jsonify({"error": response.text}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RUTA 6: Generar imagen con QWEN (alta calidad)
@app.route('/image-qwen', methods=['POST'])
def generate_image_qwen():
    datos = request.get_json()
    prompt = datos.get('prompt', '')
    formato = datos.get('format', '1:1')

    if not prompt:
        return jsonify({"error": "No prompt received"}), 400

    formatos = {
        "1:1": "1024x1024",
        "16:9": "1280x720",
        "9:16": "720x1280"
    }

    image_size = formatos.get(formato, "1024x1024")

    try:
        prompt_mejorado = mejorar_prompt(prompt)
        prompt_final = f"{prompt_mejorado}, photorealistic, highly detailed, perfect anatomy, professional photography, sharp focus, 8k uhd, masterpiece"
        negative_prompt = "deformed faces, bad anatomy, mutated hands, extra fingers, blurry, low quality, ugly, distorted, watermark, text"
        
        url = "https://api.siliconflow.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {siliconflow_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "Qwen/Qwen-Image",
            "prompt": prompt_final,
            "negative_prompt": negative_prompt,
            "image_size": image_size,
            "num_inference_steps": 30,
            "guidance_scale": 7.5
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "url": data['images'][0]['url'],
                "modelo": "qwen-image",
                "mensaje": "Imagen generada con Qwen"
            })
        else:
            return jsonify({"error": response.text}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
