import os
from flask import Flask, request, Response, stream_with_context
import requests
import re
from urllib.parse import unquote

app = Flask(__name__)

headers_shack = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Connection": "keep-alive"
}

@app.route('/')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "URL eksik usta!", 400

    try:
        domain = "/".join(target_url.split("/")[:3]) + "/"
        headers_shack["Referer"] = domain
        headers_shack["Cookie"] = "age_verified=1"

        res = requests.get(target_url, headers=headers_shack, timeout=10)
        html = res.text
        
        video_regex = r'https?://[^"\'\s\\]+\.(?:mp4|m3u8)[^"\'\s\\]*'
        matches = re.findall(video_regex, html)
        
        link_map = []
        for l in matches:
            dec = unquote(l.replace("\\", ""))
            if not any(x in dec for x in [".", "get_file", "video", "cdn"]): continue
            if any(x in dec for x in ["thumbs", "preview", "player", "_small"]): continue
            
            score = 1080 if "1080" in dec else (720 if "720" in dec else 360)
            if any(x in dec for x in ["/videos/", "_hd", "dcdn", "edge"]): score += 5000
            
            link_map.append({"url": dec, "q": score})
            
        if not link_map:
            return "Video linki bulunamadi usta!", 404
            
        link_map.sort(key=lambda x: x['q'], reverse=True)
        best_link = link_map[0]['url']

        req_headers = {}
        if 'Range' in request.headers:
            req_headers['Range'] = request.headers['Range']
        
        req_headers['User-Agent'] = headers_shack['User-Agent']
        req_headers['Referer'] = domain

        video_res = requests.get(best_link, headers=req_headers, stream=True)
        
        res_headers = dict(video_res.headers)
        res_headers["Access-Control-Allow-Origin"] = "*"
        res_headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        res_headers["Access-Control-Allow-Headers"] = "Range, Content-Type"
        res_headers["Accept-Ranges"] = "bytes"

        def generate():
            for chunk in video_res.iter_content(chunk_size=128 * 1024):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            status=video_res.status_code,
            headers=res_headers
        )

    except Exception as e:
        return f"Hata Oluştu: {str(e)}", 500

if __name__ == '__main__':
    # Render sunucusunun portunu otomatik yakalaması için port ayarı eklendi usta
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)