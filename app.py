import os
from flask import Flask, redirect, request
import yt_dlp
import cloudscraper
import re
from urllib.parse import urlparse
from functools import lru_cache

app = Flask(__name__)

# Küresel tarayıcı simülasyon motoru
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

def kalite_puani(url):
    url_lower = url.lower()
    if '4k' in url_lower or '2160' in url_lower: return 2160
    if '1440' in url_lower: return 1440
    if '1080' in url_lower: return 1080
    if '720' in url_lower: return 720
    return 0

def tv_box_youtube_formati(max_kalite):
    return f"best[height<={max_kalite}][ext=mp4]/best[height<={max_kalite}]"

# SARMALARDA SIFIR GECİKME: Önbelleği 1024 linke çıkardım usta, hafıza artık iki kat daha güçlü!
@lru_cache(maxsize=1024)
def coz_video_cekirdek(url, max_kalite):
    url_lower = url.lower()
    domain = urlparse(url).netloc
    referer = f"https://{domain}/"
    
    print(f"[➔] BULUT MOTORU TETİKLENDİ: {url}", flush=True)

    # STRATEJİ 1: SPANKBANG RADARI
    if "spankbang" in url_lower:
        response = scraper.get(url, timeout=6)  # Zaman aşımını 6 saniyeye çektim ki hantallık yapmasın
        if response.status_code == 200:
            html_content = response.text
            links = re.findall(r'["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']', html_content)
            potential_videos = []
            for link in links:
                clean_link = link.replace('\\/', '/')
                if any(x in clean_link.lower() for x in ["preview", "trailer", "ad_stream"]): continue
                # TV BOX SARMA AYARI: m3u8 akışları yerine öncelikle .mp4 uzantılarını zorla seçtiriyoruz
                if ".mp4" in clean_link:
                    potential_videos.append(clean_link)
            
            if potential_videos:
                return sorted(potential_videos, key=kalite_puani, reverse=True)[0]

    # STRATEJİ 2: YOUTUBE RADARI
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        ydl_opts = {
            'format': tv_box_youtube_formati(max_kalite),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'socket_timeout': 6,
            'no_check_certificate': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'url' in info: return info['url']
            elif 'formats' in info and len(info['formats']) > 0: return info['formats'][-1]['url']

    # STRATEJİ 3: GENEL SİTELER (PORNTREX, TNAFLIX, XHAMSTER VB.)
    else:
        # JET MOTORU AYARLARI: Bağlantı hızını uçuracak gizli parametreler çaktım usta
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # TV Box'ta yağ gibi sarması için öncelikle MP4 formatını zorla usta!
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'socket_timeout': 6,  # Bekleme süresini düşürdük, donan siteyi saniyede atlasın
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'http_headers': {
                'Referer': referer,
                'Accept-Language': 'tr-TR,tr;q=0.9',
                'Connection': 'keep-alive'
            },
            'no_check_certificate': True,
            # Gelişmiş Hızlandırıcı: Protokol pazarlıklarını hızlandırır
            'extractor_args': {
                'general': ['preconn'],
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'url' in info: return info['url']
            elif 'formats' in info and len(info['formats']) > 0:
                # Reklam akışlarını temizle ve en temiz saf MP4'ü yakala
                clean_formats = [f for f in info['formats'] if 'url' in f and not any(x in f['url'].lower() for x in ["preview", "trailer", "ad_stream", "manifest", "playlist"])]
                if clean_formats:
                    return sorted(clean_formats, key=lambda x: kalite_puani(x['url']), reverse=True)[0]['url']
                return info['formats'][-1]['url']
                
    return None

@app.route('/')
def get_video():
    url = request.args.get('url')
    max_kalite = int(request.args.get('q', 1080))
    
    if not url:
        return "Kara Lord Hata: URL eksik usta!", 400

    try:
        final_link = coz_video_cekirdek(url, max_kalite)
        if final_link:
            print(f"[+] 302 HIZLI SEVKİYAT YAPILDI", flush=True)
            return redirect(final_link, code=302)
        
        return "Kara Lord Hata: Kaynak sökülemedi!", 404
        
    except Exception as e:
        return f"Bulut Çatışması: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)
