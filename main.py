import os
import base64
import requests
import time
from flask import Flask, request, jsonify
import google.generativeai as genai
from urllib.parse import quote

app = Flask(__name__)

# Claves
gemini_api_key = os.environ.get('GEMINI_API_KEY')
siliconflow_api_key = os.environ.get('SILICONFLOW_API_KEY')

genai.configure(api_key=gemini_api_key)

# Personalidad de Didasko
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

modelo_gemini = genai.GenerativeModel('gemini-2.5-flash-lite', system_instruction=instrucciones_didasko)

# Función para mejorar prompt (usa Gemini gratis)
def mejorar_prompt(prompt_original):
    try:
        instruccion = f"""Convert this prompt into a detailed, professional prompt for AI generation.
Add: lighting, style, quality, composition details.
Keep the original idea but enhance it.
Respond ONLY with the enhanced prompt in ENGLISH, no explanations.

Original: {prompt_original}"""
        respuesta = modelo_gemini.generate_content(instruccion)
        return respuesta.text.strip()
    except:
        return prompt_original

# CHAT BARATO: Qwen 2.5 7B (por defecto, ahorra créditos)
def chat_qwen(mensaje_usuario):
    url = "https://api.siliconflow.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {siliconflow_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
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
        raise Exception(f"Qwen error: {response.text}")

# CHAT PREMIUM: DeepSeek V3 (solo cuando se pida)
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

# CHAT RESPALDO: Gemini (gratis con cuota diaria)
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
        "endpoints": ["/chat", "/chat-premium", "/vision", "/image", "/image-flux", "/image-qwen", "/video"],
        "modelo_default": "Qwen 2.5 7B (ahorra créditos)",
        "modelo_premium": "DeepSeek V3",
        "modelo_respaldo": "Gemini"
    })

# RUTA 2: Chat NORMAL (BARATO - usa Qwen por defecto)
@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje_usuario = datos.get('message', '')

    if not mensaje_usuario:
        return jsonify({"error": "No message received"}), 400

    # Intentar Qwen primero (barato)
    try:
        respuesta_texto = chat_qwen(mensaje_usuario)
        return jsonify({
            "respuesta": respuesta_texto,
            "modelo": "qwen-2.5-7b"
        })
    except Exception as e1:
        # Si falla, usar Gemini (gratis)
        try:
            respuesta_texto = chat_gemini(mensaje_usuario)
            return jsonify({
                "respuesta": respuesta_texto,
                "modelo": "gemini-respaldo"
            })
        except Exception as e2:
            return jsonify({
                "error": "Modelos no disponibles",
                "details": str(e1)
            }), 500

# RUTA 3: Chat PREMIUM (DeepSeek - solo para usuarios PRO)
@app.route('/chat-premium', methods=['POST'])
def chat_premium():
    datos = request.get_json()
    mensaje_usuario = datos.get('message', '')

    if not mensaje_usuario:
        return jsonify({"error": "No message received"}), 400

    try:
        respuesta_texto = chat_deepseek(mensaje_usuario)
        return jsonify({
            "respuesta": respuesta_texto,
            "modelo": "deepseek-v3-premium"
        })
    except Exception as e:
        # Si falla DeepSeek, usar Qwen
        try:
            respuesta_texto = chat_qwen(mensaje_usuario)
            return jsonify({
                "respuesta": respuesta_texto,
                "modelo": "qwen-respaldo"
            })
        except Exception as e2:
            return jsonify({"error": str(e)}), 500

# RUTA 4: Vision (Gemini gratis)
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

# RUTA 5: Pollinations (GRATIS ILIMITADO - respaldo eterno)
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

# RUTA 6: Flux Schnell (BARATO - usar por defecto en app)
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
            # Si falla, usar Pollinations como respaldo
            prompt_codificado = quote(prompt_mejorado)
            url_imagen = f"https://image.pollinations.ai/prompt/{prompt_codificado}?width=1024&height=1024&model=flux&nologo=true&enhance=true"
            return jsonify({
                "url": url_imagen,
                "modelo": "pollinations-respaldo",
                "mensaje": "Imagen generada (respaldo)"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RUTA 7: Qwen-Image (CARO - solo para premium o casos especiales)
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
                "mensaje": "Imagen premium generada"
            })
        else:
            return jsonify({"error": response.text}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RUTA 8: VIDEO con Wan 2.2 T2V (MUY LIMITADO - solo primeros usuarios)
@app.route('/video', methods=['POST'])
def generate_video():
    datos = request.get_json()
    prompt = datos.get('prompt', '')
    formato = datos.get('format', '9:16')

    if not prompt:
        return jsonify({"error": "No prompt received"}), 400

    formatos = {
        "16:9": "1280x720",
        "9:16": "720x1280",
        "1:1": "960x960"
    }

    image_size = formatos.get(formato, "720x1280")

    try:
        prompt_mejorado = mejorar_prompt(prompt)
        
        url = "https://api.siliconflow.com/v1/video/submit"
        headers = {
            "Authorization": f"Bearer {siliconflow_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "Wan-AI/Wan2.2-T2V-A14B",
            "prompt": prompt_mejorado,
            "image_size": image_size,
            "seed": 42
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            return jsonify({
                "error": "Videos no disponibles",
                "mensaje": "Los videos gratuitos se agotaron. ¡Plan PRO próximamente! 🎬"
            }), 500
        
        data = response.json()
        request_id = data.get('requestId') or data.get('id')
        
        if not request_id:
            return jsonify({
                "error": "Error al iniciar video",
                "response": data
            }), 500
        
        status_url = "https://api.siliconflow.com/v1/video/status"
        max_intentos = 60
        
        for intento in range(max_intentos):
            time.sleep(5)
            
            status_payload = {"requestId": request_id}
            status_response = requests.post(status_url, headers=headers, json=status_payload, timeout=30)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status', '')
                
                if status == 'Succeed':
                    videos = status_data.get('results', {}).get('videos', [])
                    if videos and len(videos) > 0:
                        video_url = videos[0].get('url')
                        if video_url:
                            return jsonify({
                                "url": video_url,
                                "prompt_original": prompt,
                                "modelo": "wan-2.2-t2v",
                                "formato": formato,
                                "duracion": "5 segundos",
                                "mensaje": "¡Video generado! 🎬"
                            })
                
                elif status == 'Failed':
                    return jsonify({
                        "error": "El video falló al generarse"
                    }), 500
        
        return jsonify({
            "error": "Tardó demasiado",
            "mensaje": "Intenta de nuevo"
        }), 408
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "mensaje": "Videos no disponibles temporalmente"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
