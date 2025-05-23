import json
import os
from flask import Flask, request, jsonify, send_from_directory, Response
from yt_dlp import YoutubeDL

app = Flask(__name__, static_folder='web')

# Ensure the 'downloads' directory exists
DOWNLOADS_DIR = os.path.join(os.getcwd(), 'downloads')
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            # 'skip_download': True, # We are only fetching info
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Example, might want more flexibility
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            if 'formats' in info:
                for f in info['formats']:
                    # Include only formats that are likely downloadable and have essential info
                    if f.get('url') or f.get('manifest_url'): # Check if there's a direct URL or manifest
                         formats.append({
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'resolution': f.get('resolution') or f.get('format_note'),
                            'format_note': f.get('format_note'),
                            'filesize': f.get('filesize'),
                            'filesize_approx': f.get('filesize_approx'),
                            'fps': f.get('fps'),
                            'vcodec': f.get('vcodec'),
                            'acodec': f.get('acodec'),
                        })
            # Fallback if no formats are explicitly listed but there's a direct URL (e.g. for single-file downloads)
            elif 'url' in info:
                 formats.append({
                    'format_id': info.get('format_id', 'best'),
                    'ext': info.get('ext', 'unknown'),
                    'resolution': info.get('resolution') or info.get('format_note', 'N/A'),
                    'format_note': info.get('format_note', 'Direct Download'),
                    'filesize': info.get('filesize'),
                    'filesize_approx': info.get('filesize_approx'),
                    'vcodec': info.get('vcodec', 'N/A'),
                    'acodec': info.get('acodec', 'N/A'),
                })


            return jsonify({
                'title': info.get('title', 'Video'),
                'formats': formats
            })
    except Exception as e:
        # Try to provide a more specific error if possible
        error_message = str(e)
        if "Unsupported URL" in error_message:
            return jsonify({'error': f"Unsupported URL: {url}"}), 500
        elif "Unable to extract video data" in error_message: # Common yt-dlp error
            return jsonify({'error': f"Could not extract video data. The video might be private, unavailable, or the URL is incorrect."}), 500
        return jsonify({'error': f"Error fetching video info: {error_message}"}), 500


@app.route('/download_video', methods=['GET'])
def download_video():
    url = request.args.get('url')
    format_id = request.args.get('format_id')

    if not url or not format_id:
        return jsonify({'error': 'URL and Format ID are required'}), 400

    try:
        # Ensure the 'downloads' directory exists (it should, but double check)
        if not os.path.exists(DOWNLOADS_DIR):
            os.makedirs(DOWNLOADS_DIR)

        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
            'noplaylist': True,
            # 'progress_hooks': [lambda d: print(d)] # for debugging
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True) # Trigger download
            # The file is downloaded to the server's `downloads` directory.
            # For a real-world app, you'd likely want to stream this back to the user
            # or provide a direct link to the static file after download.
            # For simplicity here, we'll just confirm download initiation on the server.
            
            # Attempt to find the downloaded file to provide its name
            # This is a simplified way and might need refinement for robustness
            filename = ydl.prepare_filename(info)
            
            # Check if the file exists (it should have been downloaded by yt-dlp)
            if os.path.exists(filename):
                 # This is a simplified approach. For large files, this will load the entire file into memory.
                 # A more robust solution would use Flask's send_file with streaming.
                def generate():
                    with open(filename, 'rb') as f:
                        while True:
                            chunk = f.read(4096) # Read in chunks
                            if not chunk:
                                break
                            yield chunk
                    # Optionally, remove the file after streaming if it's a temporary download
                    # os.remove(filename)

                # Ensure correct headers for download
                # Extract the actual file name from the full path
                base_filename = os.path.basename(filename)
                return Response(generate(),
                                mimetype=f"application/{info.get('ext', 'octet-stream')}",
                                headers={"Content-Disposition": f"attachment;filename={base_filename}"})

            else:
                return jsonify({'error': 'File not found after download completion.'}), 500


    except Exception as e:
        return jsonify({'error': f"Error downloading video: {str(e)}"}), 500

if __name__ == '__main__':
    # Before running the app, ensure Flask is installed.
    # You can typically install it using pip:
    # pip install Flask yt-dlp
    print("Flask and yt-dlp are required. Install them with: pip install Flask yt-dlp")
    print(f"Serving on http://127.0.0.1:5000")
    print(f"Video downloads will be saved to: {DOWNLOADS_DIR}")
    app.run(host='0.0.0.0', port=5000, debug=True)
