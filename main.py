# RUTA 4: Generar imagen (Pollinations) - CON FORMATOS
@app.route('/image', methods=['POST'])
def generate_image():
    datos = request.get_json()
    prompt = datos.get('prompt', '')
    formato = datos.get('format', '1:1')  # Formato por defecto cuadrado

    if not prompt:
        return jsonify({"error": "No prompt received"}), 400

    # Diccionario de formatos disponibles
    formatos = {
        "1:1": (1024, 1024),      # Cuadrado (Instagram)
        "16:9": (1280, 720),      # Horizontal (YouTube, PowerPoint)
        "9:16": (720, 1280),      # Vertical (TikTok, Stories)
        "4:3": (1024, 768),       # Tradicional (TV antigua)
        "3:4": (768, 1024),       # Vertical clásico
        "2:3": (768, 1152),       # Portada de libro
        "3:2": (1152, 768),       # Foto clásica
        "21:9": (1536, 640),      # Ultra panorámico
        "banner": (1920, 480),    # Banner web
        "poster": (1024, 1536)    # Poster vertical grande
    }

    # Validar formato
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
