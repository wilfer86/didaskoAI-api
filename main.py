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

# Función para mejorar prompt
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

# DeepSeek V3 vía SiliconFlow
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
        "endpoints": ["/chat", "/vision", "/image", "/image-flux", "/image-qwen", "/video"],
        "modelo_principal": "DeepSeek V3",
        "modelo_respaldo": "Gemini",
        "video_disponible": "Wan 2.1 (limitado - primeros usuarios)"
    })

# RUTA 2: Chat
@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje_usuario = datos.get('message', '')

    if not mensaje_usuario:
        return jsonify({"error": "No message received"}), 400

    try:
        respuesta_texto = chat_deepseek(mensaje_usuario)
        return jsonify({
            "respuesta": respuesta_texto,
            "modelo": "deepseek-v3"
        })
    except Exception as e1:
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

# RUTA 3: Vision
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

# RUTA 4: Pollinations
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

# RUTA 5: Flux
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

# RUTA 6: Qwen
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

# RUTA 7: VIDEO con Wan 2.1 (LIMITADO - primeros usuarios)
@app.route('/video', methods=['POST'])
def generate_video():
    datos = request.get_json()
    prompt = datos.get('prompt', '')
    formato = datos.get('format', '9:16')

    if not prompt:
        return jsonify({"error": "No prompt received"}), 400

    # Mapeo de formatos para Wan 2.1
    formatos = {
        "16:9": "1280x720",
        "9:16": "720x1280",
        "1:1": "960x960"
    }

    image_size = formatos.get(formato, "720x1280")

    try:
        # Mejorar prompt
        prompt_mejorado = mejorar_prompt(prompt)
        
        # PASO 1: Crear solicitud de video
        url = "https://api.siliconflow.com/v1/video/submit"
        headers = {
            "Authorization": f"Bearer {siliconflow_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "Wan-AI/Wan2.1-T2V-14B-Turbo",
            "prompt": prompt_mejorado,
            "image_size": image_size,
            "seed": 42
        }
        
        # Enviar solicitud
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            return jsonify({
                "error": "No hay créditos disponibles o servicio no disponible",
                "details": response.text,
                "mensaje": "¡Ups! Los videos gratuitos se agotaron. Pronto agregaremos plan PRO."
            }), 500
        
        data = response.json()
        request_id = data.get('requestId') or data.get('id')
        
        if not request_id:
            return jsonify({
                "error": "No se recibió ID de solicitud",
                "response": data
            }), 500
        
        # PASO 2: Esperar a que se procese (puede tardar 30-120 segundos)
        status_url = "https://api.siliconflow.com/v1/video/status"
        max_intentos = 60  # 60 intentos x 5 segundos = 5 minutos max
        
        for intento in range(max_intentos):
            time.sleep(5)
            
            status_payload = {"requestId": request_id}
            status_response = requests.post(status_url, headers=headers, json=status_payload, timeout=30)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status', '')
                
                if status == 'Succeed':
                    video_url = status_data.get('results', {}).get('videos', [{}])[0].get('url')
                    if video_url:
                        return jsonify({
                            "url": video_url,
                            "prompt_original": prompt,
                            "prompt_mejorado": prompt_mejorado,
                            "modelo": "wan-2.1",
                            "formato": formato,
                            "duracion": "5 segundos",
                            "mensaje": "¡Video generado exitosamente! 🎬"
                        })
                
                elif status == 'Failed':
                    return jsonify({
                        "error": "El video falló al generarse",
                        "details": status_data
                    }), 500
        
        # Si se acaba el tiempo
        return jsonify({
            "error": "El video tardó demasiado en generarse",
            "request_id": request_id,
            "mensaje": "Intenta de nuevo en unos minutos"
        }), 408
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "mensaje": "Error al generar video. Los videos gratuitos pueden haberse agotado."
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
