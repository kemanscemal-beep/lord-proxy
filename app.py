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
    if '1080' in url_lower: return 1080
    if '720' in url_lower: return 720
    if '480' in url_lower: return 480
    return 0

def tv_box_youtube_formati(max_kalite):
    return f"best[height<={max_kalite}][ext=mp4]/best[height<={max_kalite}]"

# SARMALARDA SIFIR GECİKME: Önbellek
@lru_cache(maxsize=1024)
def coz_video_cekirdek(url, max_kalite):
    url_lower = url.lower()
    domain = urlparse(url).netloc
    referer = f"https://{domain}/"
    
    print(f"[➔] BULUT MOTORU TETİKLENDİ: {url} (Üst Sınır: {max_kalite}p)", flush=True)

    # STRATEJİ 1: SPANKBANG RADARI
    if "spankbang" in url_lower:
        response = scraper.get(url, timeout=6)
        if response.status_code == 200:
            html_content = response.text
            links = re.findall(r'["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']', html_content)
            potential_videos = []
            for link in links:
                clean_link = link.replace('\\/', '/')
                if any(x in clean_link.lower() for x in ["preview", "trailer", "ad_stream"]): continue
                
                # KALİTE KONTROLÜ: Belirlenen max_kalite'den büyük linkleri eliyoruz usta!
                if kalite_puani(clean_link) <= max_kalite:
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
        # BURAYI SABİTLEDİK: Sitenin kafasına göre 2K/4K getirmesini engellemek için filtreyi yt-dlp seviyesine çektik
        ydl_opts = {
            'format': f'best[height<={max_kalite}][ext=mp4]/best[height<={max_kalite}]/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'socket_timeout': 6,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'http_headers': {
                'Referer': referer,
                'Accept-Language': 'tr-TR,tr;q=0.9',
                'Connection': 'keep-alive'
            },
            'no_check_certificate': True,
            'extractor_args': {
                'general': ['preconn'],
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'url' in info: 
                # Eğer tek dönen url bizim sınırdan büyükse filtre uygulayalım
                if kalite_puani(info['url']) <= max_kalite:
                    return info['url']
                    
            if 'formats' in info and len(info['formats']) > 0:
                # Reklamları temizle ve sadece senin istediğin max_kalite ve altındaki formatları filtrele usta!
                clean_formats = []
                for f in info['formats']:
                    if 'url' in f and not any(x in f['url'].lower() for x in ["preview", "trailer", "ad_stream", "manifest", "playlist"]):
                        # Çözünürlük kontrolü (height değeri veya url kontrolü)
                        f_height = f.get('height', 0) or kalite_puani(f['url'])
                        if f_height <= max_kalite:
                            clean_formats.append(f)
                            
                if clean_formats:
                    # Kalan en yüksek ama sınırı geçmeyen formatı seçiyoruz
                    return sorted(clean_formats, key=lambda x: x.get('height', 0) or kalite_puani(x['url']), reverse=True)[0]['url']
                
                # Eğer hiçbir şey filtrelenemezse sigorta olarak en son formatı dön
                return info['formats'][-1]['url']
                
    return None

@app.route('/')
def get_video():
    url = request.args.get('url')
    max_kalite = int(request.args.get('q', 1080)) # Varsayılan yine 1080p usta
    
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
