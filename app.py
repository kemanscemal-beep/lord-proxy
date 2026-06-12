import os
from flask import Flask, redirect, request
import yt_dlp
import cloudscraper
import re
from urllib.parse import urlparse
from functools import lru_cache

app = Flask(__name__)

# [SİBER SİGORTA 1]: Cloudscraper motorunu daha agresif bir Windows/Chrome kimliğiyle donattık
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True,
        'mobile': False
    },
    delay=10
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

# BULUT HIZLANDIRICI: 512 video linkini RAM'de tutar
@lru_cache(maxsize=512)
def coz_video_cekirdek(url, max_kalite):
    url_lower = url.lower()
    domain = urlparse(url).netloc
    referer = f"https://{domain}/"
    
    print(f"[➔] SİBER MOTOR TETİKLENDİ: {url}", flush=True)

    # STRATEJİ 1: SPANKBANG RADARI (Gelişmiş Güvenlik Aşılı)
    if "spankbang" in url_lower:
        # Kodun siteyi ev bilgisayarı gibi görmesini sağlamak için özel çerez taklidi
        scraper.headers.update({
            "Referer": referer,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none"
        })
        try:
            response = scraper.get(url, timeout=10)
            if response.status_code == 200:
                html_content = response.text
                links = re.findall(r'["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']', html_content)
                potential_videos = []
                for link in links:
                    clean_link = link.replace('\\/', '/')
                    if any(x in clean_link.lower() for x in ["preview", "trailer", "ad_stream"]): continue
                    if "sb-cd.com" in clean_link or ".mp4" in clean_link:
                        potential_videos.append(clean_link)
                
                if potential_videos:
                    return sorted(potential_videos, key=kalite_puani, reverse=True)[0]
        except Exception:
            pass # Eğer özel mod patlarsa genel moda (yt_dlp) devret

    # STRATEJİ 2: YOUTUBE RADARI
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        ydl_opts = {
            'format': tv_box_youtube_formati(max_kalite),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'socket_timeout': 10,
            'no_check_certificate': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'url' in info: return info['url']
            elif 'formats' in info and len(info['formats']) > 0: return info['formats'][-1]['url']

    # STRATEJİ 3: GENEL SİTELER VE GÜVENLİK DUVARI BYPASS (PORNTREX, TNAFLIX VB.)
    # [SİBER SİGORTA 2]: yt_dlp motoruna Cloudflare ve bot korumalarını delmesi için ek parametreler gömdük
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 12,
        'no_check_certificate': True,
        'geo_bypass': True,  # Ülke engellerini aşma simülasyonu
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': referer,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'url' in info: return info['url']
        elif 'formats' in info and len(info['formats']) > 0:
            clean_formats = [f for f in info['formats'] if 'url' in f and not any(x in f['url'].lower() for x in ["preview", "trailer", "ad_stream"])]
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
            print(f"[+] 302 SİBER SEVKİYAT BAŞARILI", flush=True)
            return redirect(final_link, code=302)
        
        return "Kara Lord Hata: Kaynak sökülemedi!", 404
        
    except Exception as e:
        return f"Bulut Çatışması: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)
