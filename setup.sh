#!/bin/bash

# Script para inicializar el entorno de desarrollo de la API yt-dlp

echo "🎵 Iniciando configuración del Music Downloader API..."

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado. Por favor instálalo primero."
    exit 1
fi

echo "✅ Python3 encontrado: $(python3 --version)"

# Verificar si pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 no está instalado. Por favor instálalo primero."
    exit 1
fi

echo "✅ pip3 encontrado"

# Instalar dependencias
echo "📦 Instalando dependencias..."

# Instalar Flask y Flask-CORS
pip3 install flask flask-cors

# Verificar si yt-dlp está disponible
if ! python3 -m yt_dlp --version &> /dev/null; then
    echo "📥 Instalando yt-dlp..."
    pip3 install yt-dlp
else
    echo "✅ yt-dlp ya está instalado: $(python3 -m yt_dlp --version)"
fi

# Verificar si ffmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg no está instalado. Esto es necesario para convertir audio a MP3."
    echo "   Para instalarlo en macOS: brew install ffmpeg"
    echo "   Para instalarlo en Ubuntu: sudo apt install ffmpeg"
else
    echo "✅ ffmpeg encontrado: $(ffmpeg -version | head -1)"
fi

# Crear directorio de descargas por defecto si no existe
DEFAULT_DIR="/Users/O002545/Music/playlist"
if [ ! -d "$DEFAULT_DIR" ]; then
    echo "📁 Creando directorio por defecto: $DEFAULT_DIR"
    mkdir -p "$DEFAULT_DIR"
else
    echo "✅ Directorio por defecto existe: $DEFAULT_DIR"
fi

echo ""
echo "🎉 ¡Configuración completada!"
echo ""
echo "📋 Para usar la API:"
echo "   1. Ejecutar API: python3 api_downloader.py"
echo "   2. Abrir frontend: open frontend.html"
echo "   3. La API estará disponible en: http://localhost:5000"
echo ""
echo "🌐 Endpoints disponibles:"
echo "   POST /download - Descargar música"
echo "   GET /status/<job_id> - Ver estado"
echo "   GET /formats - Ver formatos"
echo "   GET /jobs - Listar trabajos"
echo ""
echo "💡 Ejemplo de uso con curl:"
echo '   curl -X POST http://localhost:5000/download \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"url": "https://music.youtube.com/playlist?list=..."}'"'"
echo ""

# Hacer ejecutable si no lo es
chmod +x "$0"

echo "🚀 ¡Listo para usar!"
