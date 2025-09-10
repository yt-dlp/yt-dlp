# Music Downloader API

Una API REST para descargar música y playlists de YouTube usando yt-dlp.

## 🚀 Inicio Rápido

### 1. Configuración automática
```bash
chmod +x setup.sh
./setup.sh
```

### 2. Iniciar la API
```bash
python3 api_downloader.py
```

### 3. Abrir el frontend
```bash
open frontend.html
```

## 📋 Endpoints de la API

### POST `/download`
Inicia una descarga de música/playlist.

**Parámetros:**
```json
{
  "url": "https://music.youtube.com/playlist?list=...",
  "format": "mp3",           // mp3, mp4, best
  "quality": "0",           // 0, 320K, 256K, 192K, 128K
  "naming": "artist-title", // title, artist-title
  "output_dir": "/path/to/folder"
}
```

**Respuesta:**
```json
{
  "job_id": "job_1234567890_0",
  "status": "iniciado",
  "message": "Descarga iniciada. Usa /status/job_id para ver el progreso"
}
```

### GET `/status/<job_id>`
Consulta el estado de una descarga.

**Respuesta:**
```json
{
  "status": "completado",
  "url": "https://...",
  "created_at": "2025-09-10T...",
  "progress": 100,
  "files": ["/path/to/downloaded/file.mp3"],
  "error": null
}
```

### GET `/formats`
Lista los formatos y calidades disponibles.

### GET `/jobs`
Lista todos los trabajos de descarga.

### POST `/clear-jobs`
Limpia el historial de trabajos.

## 🎯 Ejemplos de uso

### Con curl:
```bash
# Descargar playlist en MP3
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://music.youtube.com/playlist?list=PLHxRosSB9sj0FRQu8igy6rYnVy8aC2swf",
    "format": "mp3",
    "quality": "0",
    "naming": "artist-title"
  }'

# Verificar estado
curl http://localhost:5000/status/job_1234567890_0
```

### Con JavaScript:
```javascript
// Descargar
const response = await fetch('http://localhost:5000/download', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://music.youtube.com/playlist?list=...',
    format: 'mp3',
    quality: '320K'
  })
});

const { job_id } = await response.json();

// Verificar estado
const statusResponse = await fetch(`http://localhost:5000/status/${job_id}`);
const status = await statusResponse.json();
```

## 🛠️ Configuración

### Variables de entorno (opcionales):
```bash
export MUSIC_DOWNLOADER_PORT=5000
export MUSIC_DOWNLOADER_HOST=0.0.0.0
export DEFAULT_OUTPUT_DIR="/Users/O002545/Music/playlist"
```

### Dependencias:
- Python 3.6+
- flask
- flask-cors
- yt-dlp
- ffmpeg (para conversión a MP3)

## 📁 Estructura del proyecto

```
yt-dlp/
├── api_downloader.py    # API principal
├── frontend.html        # Interfaz web
├── setup.sh            # Script de configuración
└── API_README.md       # Esta documentación
```

## 🎵 Frontend Web

El frontend incluye:
- ✅ Interfaz moderna y responsive
- ✅ Selección de formato y calidad
- ✅ Monitoreo de progreso en tiempo real
- ✅ Visualización de archivos descargados
- ✅ Log de salida detallado

## 🔧 Solución de problemas

### Error: ffmpeg no encontrado
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### Error: Puerto en uso
Cambiar el puerto en `api_downloader.py`:
```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

### Error: Permisos de directorio
```bash
mkdir -p /Users/O002545/Music/playlist
chmod 755 /Users/O002545/Music/playlist
```

## 🔒 Seguridad

**⚠️ Importante:** Esta API no incluye autenticación. Para uso en producción:

1. Agregar autenticación (JWT, API keys)
2. Validar URLs permitidas
3. Limitar rate limiting
4. Ejecutar en HTTPS
5. Configurar CORS apropiadamente

## 📝 Notas

- Los trabajos se almacenan en memoria (se pierden al reiniciar)
- Para persistencia, considera usar Redis o una base de datos
- YouTube Music se redirige automáticamente a youtube.com
- Algunos videos pueden requerir autenticación especial

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la misma licencia que yt-dlp.
