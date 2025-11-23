import requests
import json
import re
import time
import urllib3
import os
import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

print("🚀 Global Roast 100 - V1.0 正式发布版")
print("📝 策略: 仅保留 100% 稳定的 API 源 + 已验证的 Browser 源")

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 目标名单
# ==========================================

# A组：API 模式 (速度快，数据最准，包含高清图)
SHOPIFY_ROASTERS = [
    {"name": "Fjord Coffee", "country": "Germany", "url": "https://fjord-coffee.de"},
    {"name": "Glitch Coffee", "country": "Japan", "url": "https://shop.glitchcoffee.com"}, 
    {"name": "Kurasu", "country": "Japan", "url": "https://kurasu.kyoto"},
    {"name": "Onibus Coffee", "country": "Japan", "url": "https://onibuscoffee.com"},
    {"name": "La Cabra", "country": "Denmark", "url": "https://www.lacabra.dk"},
    {"name": "April Coffee", "country": "Denmark", "url": "https://www.aprilcoffeeroasters.com"},
    {"name": "Coffee Collective", "country": "Denmark", "url": "https://coffeecollective.dk"},
    {"name": "Koppi", "country": "Sweden", "url": "https://www.koppi.se"},
    {"name": "Drop Coffee", "country": "Sweden", "url": "https://www.dropcoffee.com"},
    {"name": "Morgon Coffee Roasters", "country": "Sweden", "url": "https://www.morgoncoffeeroasters.com"},
    {"name": "Five Elephant", "country": "Germany", "url": "https://www.fiveelephant.com"},
    {"name": "The Barn", "country": "Germany", "url": "https://thebarn.de"},
    {"name": "Nomad Coffee", "country": "Spain", "url": "https://nomadcoffee.es"},
    {"name": "Right Side Coffee", "country": "Spain", "url": "https://www.rightsidecoffee.com"},
    {"name": "Onyx Coffee Lab", "country": "USA", "url": "https://onyxcoffeelab.com"},
    {"name": "Sey Coffee", "country": "USA", "url": "https://www.seycoffee.com"},
    {"name": "George Howell", "country": "USA", "url": "https://georgehowellcoffee.com"},
    {"name": "Cat & Cloud", "country": "USA", "url": "https://catandcloud.com"},
    {"name": "Passenger Coffee", "country": "USA", "url": "https://www.passengercoffee.com"},
    {"name": "Brandywine", "country": "USA", "url": "https://www.brandywinecoffeeroasters.com"},
    {"name": "Verve Coffee", "country": "USA", "url": "https://www.vervecoffee.com"},
    {"name": "Black & White", "country": "USA", "url": "https://www.blackwhiteroasters.com"},
    {"name": "Proud Mary USA", "country": "USA", "url": "https://proudmarycoffee.com"}, 
    {"name": "Monogram", "country": "Canada", "url": "https://monogramcoffee.com"},
    {"name": "Rogue Wave", "country": "Canada", "url": "https://www.roguewavecoffee.ca"},
    {"name": "ONA Coffee", "country": "Australia", "url": "https://onacoffee.com.au"},
    {"name": "Market Lane", "country": "Australia", "url": "https://marketlane.com.au"},
    {"name": "Seven Seeds", "country": "Australia", "url": "https://sevenseeds.com.au"},
    {"name": "Code Black", "country": "Australia", "url": "https://codeblackcoffee.com.au"},
    {"name": "Reuben Hills", "country": "Australia", "url": "https://reubenhills.com.au"},
    {"name": "Flight Coffee", "country": "New Zealand", "url": "https://flightcoffee.co.nz"},
]

# B组：Browser 模式 (仅保留已验证成功的)
PLAYWRIGHT_ROASTERS = [
    # 之前验证成功的
    {"name": "Friedhats", "country": "Netherlands", "url": "https://friedhats.com/collections/coffees"},
    {"name": "MOK Coffee", "country": "Belgium", "url": "https://mokcoffee.be/collections/coffee"},
    {"name": "Three Marks Coffee", "country": "Spain", "url": "https://threemarkscoffee.com/shop/"},
    
    # 暂时移除的不稳定源:
    # Canyon Coffee (图片问题)
    # DAK Coffee (React 结构问题)
    # Cupping Room (标题抓取问题)
    # Mel Coffee (深度嵌套问题)
]

# ==========================================
# 工具函数
# ==========================================

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    return cleantext.strip()

def extract_flavor_info(html_text):
    if not html_text: return ""
    clean_text = clean_html(html_text)
    flavor = ""
    flavor_match = re.search(r'(Tasting Notes|Flavor|Tastes|Notes|Profile)[:\s]+(.*?)(?:\.|\||\n|$)', clean_text, re.IGNORECASE)
    if flavor_match: flavor = flavor_match.group(2).strip()
    return f"风味: {flavor[:60]}" if flavor else clean_text[:80] + "..."

def is_fresh_drop(date_str):
    if not date_str: return False
    try:
        pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        thirty_days_ago = datetime.now(pub_date.tzinfo) - timedelta(days=60) 
        return pub_date >= thirty_days_ago
    except:
        return True

def clean_title(text):
    if not text: return ""
    # 强力过滤：价格、购物车、已售罄
    split_chars = ['€', '$', '£', '¥', 'Regular', 'Sold', 'Out of', 'from', 'From', 'Add to', 'Quick', 'TASTING']
    for char in split_chars:
        if char in text:
            text = text.split(char)[0]
    if '\n' in text:
        text = text.split('\n')[0]
    return text.strip()

# ==========================================
# 引擎 1: API (Shopify JSON)
# ==========================================
def fetch_shopify_api(roaster):
    print(f"👉 [API] 正在连接: {roaster['name']} ...", end="", flush=True)
    # 智能提取 base_url
    base_url = "/".join(roaster['url'].split('/')[:3]) 
    url = f"{base_url}/products.json?limit=250"
    
    products = []
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" }
    
    try:
        r = requests.get(url, headers=headers, timeout=30, verify=False)
        if r.status_code != 200: 
            print(f" [跳过] {r.status_code}")
            return []
        
        data = r.json()
        for item in data.get('products', []):
            title = item.get('title', '')
            p_type = item.get('product_type', '').lower()
            pub_at = item.get('published_at')
            
            # 过滤周边产品
            if any(k in title.lower() for k in ['subscription', 'gift', 'merch', 'tee', 'sample', 'course', 'equipment', 'dripper', 'capsule', 'box', 'set']): continue
            
            is_coffee = False
            coffee_keywords = ['coffee', 'bean', 'roast', 'filter', 'espresso', 'geisha', 'blend', 'single origin', 'decaf']
            if any(k in p_type for k in coffee_keywords): is_coffee = True
            if any(k in title.lower() for k in coffee_keywords): is_coffee = True
            # 白名单
            if roaster['name'] in ["Right Side Coffee", "MOK Coffee", "Onibus Coffee", "Glitch Coffee", "Mel Coffee Roasters"]: is_coffee = True
            
            if not is_coffee: continue
            if not is_fresh_drop(pub_at): continue

            variant = item['variants'][0] if item['variants'] else {}
            img_src = item['images'][0]['src'] if item['images'] else ""
            products.append({
                "roaster_name": roaster['name'],
                "roaster_country": roaster['country'],
                "name": title,
                "url": f"{base_url}/products/{item['handle']}",
                "image": img_src,
                "price": variant.get('price', '0'),
                "description": extract_flavor_info(item.get('body_html', '')),
                "published_at": pub_at,
                "source_type": "api"
            })
        print(f" [成功] {len(products)} 款")
    except Exception as e:
        print(f" [超时/错误]")
    return products

# ==========================================
# 引擎 2: Playwright (Browser)
# ==========================================
async def fetch_with_browser(roaster):
    print(f"🕵️ [Browser] 正在渲染: {roaster['name']} ...", end="", flush=True)
    products = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            locale='en-US'
        )
        page = await context.new_page()
        
        try:
            await page.goto(roaster['url'], timeout=60000, wait_until="networkidle")
            
            # 强力滚动 (Friedhats/MOK 必须)
            for _ in range(6):
                await page.mouse.wheel(0, 3000)
                await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 1. JSON-LD 优先匹配 (Friedhats 神器)
            json_ld_images = {}
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        url = item.get('url') or item.get('item', {}).get('url')
                        img = item.get('image')
                        if not url and 'offers' in item:
                            offers = item['offers']
                            if isinstance(offers, list) and len(offers) > 0: url = offers[0].get('url')
                            elif isinstance(offers, dict): url = offers.get('url')
                        if url and img:
                            url_path = url.split('?')[0].replace('https://', '').replace('http://', '').rstrip('/')
                            if isinstance(img, list): img = img[0]
                            json_ld_images[url_path] = img
                except: continue

            # 2. 遍历链接
            links = soup.find_all('a', href=True)
            seen_titles = set()
            
            for link in links:
                href = link['href']
                
                # 判定是否为产品
                is_product = False
                if '/products/' in href: is_product = True
                if '/product/' in href: is_product = True # Three Marks
                if '/collections/coffees/products/' in href: is_product = True
                
                if is_product and not any(x in href for x in ['sub', 'gift', 'merch', 'login', 'cart', 'equipment', 'brew', 'pages', 'account', 'wholesale']):
                    
                    # 提取标题
                    title = ""
                    t_el = link.find(['h2', 'h3', 'h4', 'div', 'span'], class_=lambda x: x and ('title' in x or 'name' in x))
                    if t_el: title = t_el.get_text(strip=True, separator=' ')
                    if not title: title = link.get_text(strip=True, separator=' ')
                    
                    # 清洗标题
                    title = clean_title(title)

                    if title and title not in seen_titles and len(title) > 2 and len(title) < 100:
                        if title.lower() in ['shop now', 'view all', 'learn more', 'add to cart']: continue
                        if 'subscription' in title.lower(): continue

                        full_url = href
                        if not href.startswith('http'):
                            base_url = "/".join(roaster['url'].split('/')[:3])
                            if not href.startswith('/'): href = '/' + href
                            full_url = base_url + href
                        
                        # --- 图片匹配 ---
                        img_url = ""
                        clean_url_key = full_url.split('?')[0].replace('https://', '').replace('http://', '').rstrip('/')
                        for k, v in json_ld_images.items():
                            if k in clean_url_key or clean_url_key in k:
                                img_url = v
                                break
                        
                        # 常规 img 标签
                        if not img_url:
                            search_area = link
                            for _ in range(3):
                                if not search_area: break
                                imgs = search_area.find_all('img')
                                for img in imgs:
                                    if int(img.get('width', 100)) < 50: continue
                                    srcset = img.get('srcset')
                                    if srcset: img_url = srcset.split(',')[-1].strip().split(' ')[0]
                                    if not img_url: img_url = img.get('data-src') or img.get('src')
                                    if img_url and 'base64' not in img_url: break
                                if img_url: break
                                search_area = search_area.parent

                        # 背景图
                        if not img_url:
                            search_area = link
                            for _ in range(3):
                                if not search_area: break
                                divs = search_area.find_all('div', style=True)
                                for div in divs:
                                    if 'background-image' in div['style']:
                                        match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', div['style'])
                                        if match:
                                            img_url = match.group(1)
                                            break
                                if img_url: break
                                search_area = search_area.parent

                        # 图片 URL 清洗
                        if img_url:
                            if img_url.startswith('//'): img_url = "https:" + img_url
                            img_url = re.sub(r'_\d+x(\d+)?\.', '.', img_url)
                            img_url = re.sub(r'\?.*', '', img_url)

                        # 价格
                        price = "Check Site"
                        p_container = link.parent
                        if p_container:
                            p_text = p_container.get_text()
                            p_match = re.search(r'([€$£¥]\s?\d+([.,]\d{2})?)', p_text)
                            if p_match: price = p_match.group(0)

                        products.append({
                            "roaster_name": roaster['name'],
                            "roaster_country": roaster['country'],
                            "name": title,
                            "url": full_url,
                            "image": img_url,
                            "price": price,
                            "description": f"Fresh from {roaster['name']}",
                            "published_at": datetime.now().isoformat(),
                            "source_type": "browser"
                        })
                        seen_titles.add(title)

            print(f" [成功] {len(products)} 款")
            
        except Exception as e:
            print(f" [错误] {str(e)[:50]}...")
        finally:
            await context.close()
            await browser.close()
    
    return products

async def main_async():
    all_beans = []
    print(f"\n🚀 开始抓取任务...\n")
    
    # 1. API 组
    for roaster in SHOPIFY_ROASTERS:
        beans = fetch_shopify_api(roaster)
        all_beans.extend(beans)

    # 2. Browser 组
    for roaster in PLAYWRIGHT_ROASTERS:
        beans = await fetch_with_browser(roaster)
        all_beans.extend(beans)

    # 排序
    all_beans.sort(key=lambda x: x['published_at'], reverse=True)

    # 保存 (使用绝对路径或相对路径)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'data.json')

    print(f"\n💾 正在保存到: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(all_beans, f, ensure_ascii=False, indent=2)
    print(f"🎉 抓取结束! 总收录: {len(all_beans)} 款豆子")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
