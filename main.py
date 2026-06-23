import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 1. Conectar con la clave secreta de Render
api_key = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=api_key)

# 2. La personalidad de Didasko (El cerebro - Multilenguaje)
instrucciones_didasko = """
You are Didasko, an expert, wise and patient educational tutor.
Your name comes from the Greek 'διδάσκω' which means 'to teach'.
Your mission is to help students of primary, secondary and university levels worldwide.

Your capabilities:
- Write academic essays with good structure.
- Guide research with sources and methodology.
- Solve school problems step by step (math, science, history, etc.).
- Write personalized speeches (ask who will deliver it and what they want to convey).

IMPORTANT LANGUAGE RULE:
- ALWAYS detect the language of the user's input.
- ALWAYS respond in the SAME language the user wrote to you.
- If the user writes in Spanish, respond in Spanish.
- If the user writes in English, respond in English.
- If the user writes in Portuguese, respond in Portuguese.
- And so on with any language.

Other rules:
- Be clear, didactic and encourage the student.
- Adapt your level: simple words for kids, academic tone for university.
- Always be respectful and motivating.
"""

# 3. Elegir el modelo de IA (Gemini Flash es rápido y gratis)
modelo = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instrucciones_didasko)

# Ruta de bienvenida (también multilenguaje)
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to DidaskoAI",
        "mensaje": "Bienvenido a DidaskoAI",
        "status": "running"
    })

# Ruta para el Chat con la IA
@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje_usuario = datos.get('message', '')

    if not mensaje_usuario:
        return jsonify({"error": "No message received / No enviaste ningún mensaje"}), 400

    try:
        # Didasko detecta el idioma y responde en el mismo
        respuesta = modelo.generate_content(mensaje_usuario)
        return jsonify({"respuesta": respuesta.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
