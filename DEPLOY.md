# Music Downloader API - Deploy Guide

## 🚀 Deploy gratuito en Railway (Recomendado)

### Paso 1: Preparar el proyecto
```bash
git add .
git commit -m "Preparar para deploy"
git push origin main
```

### Paso 2: Deploy en Railway
1. Ve a [railway.app](https://railway.app)
2. Conecta tu GitHub
3. Selecciona este repositorio
4. ¡Railway auto-detecta que es Python y lo deploya!

### Paso 3: Configurar variables
En Railway dashboard:
- `PORT=8080` (automático)
- `DEBUG=False` (opcional)

---

## 🌐 Deploy en Render

### Paso 1: Crear servicio
1. Ve a [render.com](https://render.com)
2. New → Web Service
3. Conecta tu repositorio

### Paso 2: Configuración
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python api_downloader.py`
- **Environment**: Python 3

---

## 🪰 Deploy en Fly.io

### Paso 1: Instalar CLI
```bash
brew install flyctl
```

### Paso 2: Deploy
```bash
fly launch
fly deploy
```

---

## 🐍 Deploy en PythonAnywhere

### Paso 1: Subir archivos
- Sube todos los archivos a tu cuenta
- Instala dependencias en consola bash

### Paso 2: Configurar Web App
- New Web App → Flask
- Apunta a `api_downloader.py`

---

## ⚠️ Consideraciones importantes

### Limitaciones del free tier:
- **Storage limitado**: Los archivos se pueden borrar
- **Timeouts**: Descargas largas pueden fallar
- **CPU/RAM limitados**: Para playlists grandes

### Recomendaciones:
1. **Para uso personal**: Railway o Render
2. **Para compartir**: Agrega autenticación
3. **Para playlists grandes**: Considera un VPS barato

### URLs después del deploy:
- Frontend: `https://tu-app.railway.app/` (servir frontend.html)
- API: `https://tu-app.railway.app/download`

### Ejemplo de uso en producción:
```bash
curl -X POST https://tu-app.railway.app/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://music.youtube.com/playlist?list=...",
    "output_dir": "/tmp/downloads",
    "format": "mp3",
    "quality": "320K"
  }'
```

## 🔧 Troubleshooting

### Error: ffmpeg not found
- Railway/Render: Agrega buildpack de ffmpeg
- Fly.io: Incluye en Dockerfile

### Error: Storage full
- Limpia archivos temporales
- Usa `/tmp` como output_dir

### Error: Timeout
- Reduce calidad para descargas más rápidas
- Procesa playlists en lotes pequeños
