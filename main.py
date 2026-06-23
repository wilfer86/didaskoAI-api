import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 1. Conectar con la clave secreta de Render
api_key = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=api_key)

# 2. La personalidad de Didasko (El cerebro)
instrucciones_didasko = """
Eres Didasko, un tutor educativo experto, sabio y paciente. 
Tu misión es ayudar a estudiantes de primaria, secundaria y universidad.
Tus capacidades son:
- Redactar ensayos académicos con buena estructura.
- Guiar investigaciones con fuentes y metodología.
- Resolver problemas escolares paso a paso (matemáticas, ciencias, historia, etc.).
- Escribir discursos personalizados (pregunta quién lo dirá y qué quiere transmitir).
Reglas:
- Responde siempre en español.
- Sé claro, didáctico y anima al estudiante.
- Si es primaria, usa palabras sencillas. Si es superior, usa tono académico.
"""

# 3. Elegir el modelo de IA (Gemini Flash es rápido y gratis)
modelo = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instrucciones_didasko)

# Ruta de bienvenida
@app.route('/')
def home():
    return jsonify({"mensaje": "Bienvenido a DidaskoAI", "estado": "funcionando"})

# Ruta para el Chat con la IA
@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje_usuario = datos.get('message', '')

    if not mensaje_usuario:
        return jsonify({"error": "No enviaste ningún mensaje"}), 400

    try:
        # Aquí es donde Didasko piensa y responde
        respuesta = modelo.generate_content(mensaje_usuario)
        return jsonify({"respuesta": respuesta.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
