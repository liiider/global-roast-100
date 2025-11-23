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

print("✅ V15.0 全自动浏览器模拟版 (JSON-LD 增强版) 已启动...")
print("📂 正在初始化混合动力引擎 (API + Playwright)...")

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 目标名单配置
# ==========================================

# A组：API 模式
# 这些网站的 /products.json 是公开的，速度极快，优先使用
SHOPIFY_ROASTERS = [
    # 日本/亚洲
    {"name": "Glitch Coffee", "country": "Japan", "url": "https://shop.glitchcoffee.com"}, 
    {"name": "Kurasu", "country": "Japan", "url": "https://kurasu.kyoto"},
    {"name": "Onibus Coffee", "country": "Japan", "url": "https://onibuscoffee.com"},
    {"name": "Mel Coffee Roasters", "country": "Japan", "url": "https://melcoffee.jp"},
    {"name": "The Cupping Room", "country": "Hong Kong", "url": "https://cuppingroom.hk"},
    
    # 北欧/欧洲
    {"name": "La Cabra", "country": "Denmark", "url": "https://www.lacabra.dk"},
    {"name": "April Coffee", "country": "Denmark", "url": "https://www.aprilcoffeeroasters.com"},
    {"name": "Coffee Collective", "country": "Denmark", "url": "https://coffeecollective.dk"},
    {"name": "Koppi", "country": "Sweden", "url": "https://www.koppi.se"},
    {"name": "Drop Coffee", "country": "Sweden", "url": "https://www.dropcoffee.com"},
    {"name": "Morgon Coffee Roasters", "country": "Sweden", "url": "https://www.morgoncoffeeroasters.com"},
    {"name": "Five Elephant", "country": "Germany", "url": "https://www.fiveelephant.com"},
    {"name": "The Barn", "country": "Germany", "url": "https://thebarn.de"},
    {"name": "DAK Coffee", "country": "Netherlands", "url": "https://dakcoffeeroasters.com"},
    {"name": "Nomad Coffee", "country": "Spain", "url": "https://nomadcoffee.es"},
    {"name": "Right Side Coffee", "country": "Spain", "url": "https://www.rightsidecoffee.com"},
    {"name": "MOK Coffee", "country": "Belgium", "url": "https://mokcoffee.be"},
    
    # 北美
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
    
    # 澳洲
    {"name": "ONA Coffee", "country": "Australia", "url": "https://onacoffee.com.au"},
    {"name": "Market Lane", "country": "Australia", "url": "https://marketlane.com.au"},
    {"name": "Seven Seeds", "country": "Australia", "url": "https://sevenseeds.com.au"},
    {"name": "Code Black", "country": "Australia", "url": "https://codeblackcoffee.com.au"},
    {"name": "Reuben Hills", "country": "Australia", "url": "https://reubenhills.com.au"},
    {"name": "Flight Coffee", "country": "New Zealand", "url": "https://flightcoffee.co.nz"},
]

# B组：浏览器增强模式
# 针对屏蔽了 API 或非 Shopify 的网站 (Friedhats, Canyon 等在此)
PLAYWRIGHT_ROASTERS = [
    # 屏蔽了 .json 接口的 Shopify 网站
    {"name": "Friedhats", "country": "Netherlands", "url": "https://friedhats.com/collections/coffees"},
    {"name": "Canyon Coffee", "country": "USA", "url": "https://canyoncoffee.co/collections/coffee"},
    {"name": "Leaves Coffee", "country": "Japan", "url": "https://leavescoffee.jp/collections/coffee-beans"},
    {"name": "Three Marks Coffee", "country": "Spain", "url": "https://www.threemarkscoffee.com/collections/coffee"},
    {"name": "Fjord Coffee", "country": "Germany", "url": "https://fjord-coffee-roasters.com/collections/coffee-beans"},
    
    # 非 Shopify / 高度定制网站
    {"name": "Manhattan", "country": "Netherlands", "url": "https://manhattan.coffee/catalog/coffee"},
    {"name": "Gardelli", "country": "Italy", "url": "https://shop.gardellicoffee.com/collections/coffees"},
    {"name": "Tim Wendelboe", "country": "Norway", "url": "https://timwendelboe.no/product-category/coffee/"},
    {"name": "A Matter of Concrete", "country": "Netherlands", "url": "https://amatterofconcrete.com/product-category/coffee/"},
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
    origin = ""
    origin_match = re.search(r'(Region|Origin|Farm)[:\s]+(.*?)(?:\.|\||\n|$)', clean_text, re.IGNORECASE)
    if origin_match: origin = origin_match.group(2).strip()
    result_parts = []
    if origin: result_parts.append(f"产地: {origin[:30]}")
    if flavor: result_parts.append(f"风味: {flavor[:60]}")
    if result_parts: return " | ".join(result_parts)
    return clean_text[:80] + "..."

def is_fresh_drop(date_str):
    if not date_str: return False
    try:
        pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        thirty_days_ago = datetime.now(pub_date.tzinfo) - timedelta(days=45) # 放宽到45天
        return pub_date >= thirty_days_ago
    except:
        return True

# ==========================================
# 引擎 1: Requests (API)
# ==========================================
def fetch_shopify_api(roaster):
    print(f"👉 [API] 正在连接: {roaster['name']} ...", end="", flush=True)
    url = f"{roaster['url'].rstrip('/')}/products.json?limit=250"
    products = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
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
            
            if any(k in title.lower() for k in ['subscription', 'gift', 'merch', 'tee', 'sample', 'course', 'equipment', 'dripper', 'capsule']): continue
            
            is_coffee = False
            coffee_keywords = ['coffee', 'bean', 'roast', 'filter', 'espresso', 'geisha', 'blend', 'single origin', 'decaf']
            if any(k in p_type for k in coffee_keywords): is_coffee = True
            if any(k in title.lower() for k in coffee_keywords): is_coffee = True
            if roaster['name'] in ["Right Side Coffee", "MOK Coffee", "Onibus Coffee", "Glitch Coffee"]: is_coffee = True
            
            if not is_coffee: continue
            if not is_fresh_drop(pub_at): continue

            variant = item['variants'][0] if item['variants'] else {}
            img_src = item['images'][0]['src'] if item['images'] else ""
            
            products.append({
                "roaster_name": roaster['name'],
                "roaster_country": roaster['country'],
                "name": title,
                "url": f"{roaster['url']}/products/{item['handle']}",
                "image": img_src,
                "price": variant.get('price', '0'),
                "description": extract_flavor_info(item.get('body_html', '')),
                "published_at": pub_at,
                "source_type": "api"
            })
        print(f" [成功] {len(products)} 款")
    except Exception as e:
        print(f" [超时]")
        
    return products

# ==========================================
# 引擎 2: Playwright (增强版: JSON-LD + 强力滚动)
# ==========================================
async def fetch_with_browser(roaster):
    print(f"🕵️ [Browser] 正在渲染: {roaster['name']} ...", end="", flush=True)
    products = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        try:
            await page.goto(roaster['url'], timeout=60000, wait_until="domcontentloaded")
            
            # --- 强力滚动：确保懒加载图片被触发 ---
            for _ in range(5):
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # --- 核心技术：解析 JSON-LD (专门解决 Friedhats/Canyon 缺图问题) ---
            json_ld_images = {}
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    # 处理 List 类型的 Schema
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        # 查找 Product 或 ListItem
                        url = item.get('url') or item.get('item', {}).get('url')
                        img = item.get('image')
                        
                        # 尝试获取 Shopify 特有的 offers 里的 URL
                        if not url and 'offers' in item:
                            offers = item['offers']
                            if isinstance(offers, list) and len(offers) > 0:
                                url = offers[0].get('url')
                            elif isinstance(offers, dict):
                                url = offers.get('url')

                        if url and img:
                            # 统一 URL 格式 (去掉域名部分，只留路径用于匹配)
                            if 'http' in url: 
                                url_path = url.split('com')[-1].split('co')[-1].split('jp')[-1].split('?')[0]
                            else:
                                url_path = url.split('?')[0]
                            
                            if isinstance(img, list): img = img[0]
                            json_ld_images[url_path] = img
                except:
                    continue

            # --- 常规 HTML 解析 ---
            links = soup.find_all('a', href=True)
            seen = set()
            
            for link in links:
                href = link['href']
                
                # 判定规则
                is_product = False
                if '/products/' in href: is_product = True
                if '/product/' in href: is_product = True
                if '/catalog/coffee/' in href: is_product = True
                
                if is_product and not any(x in href for x in ['sub', 'gift', 'merch', 'login', 'account', 'page', 'cart']):
                    
                    # 提取标题
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        t_el = link.find(['h2', 'h3', 'h4', 'div', 'span'], class_=lambda x: x and ('title' in x or 'name' in x))
                        if t_el: title = t_el.get_text(strip=True)
                    if not title: # 再次尝试找父级
                         parent = link.parent
                         if parent:
                             t_el = parent.find(['h2', 'h3', 'h4'], text=True)
                             if t_el: title = t_el.get_text(strip=True)

                    if title and title not in seen and len(title) > 3 and len(title) < 100:
                        if any(k in title.lower() for k in ['subscription', 'gift', 'course', 'workshop', 'brew']): continue
                        
                        # --- 图片提取逻辑 ---
                        img_url = ""
                        clean_href_path = href.split('?')[0]

                        # 策略 A: 匹配 JSON-LD (最高优先级，高清)
                        for j_path, j_img in json_ld_images.items():
                            if j_path in clean_href_path or clean_href_path in j_path:
                                img_url = j_img
                                break
                        
                        # 策略 B: HTML 寻找 img 标签
                        if not img_url:
                            search_area = link
                            for _ in range(3):
                                if not search_area: break
                                img = search_area.find('img')
                                if img:
                                    # 优先拿 srcset
                                    srcset = img.get('srcset')
                                    if srcset:
                                        img_url = srcset.split(',')[-1].strip().split(' ')[0]
                                    # 其次拿 data-src
                                    if not img_url: img_url = img.get('data-src')
                                    # 最后拿 src
                                    if not img_url: img_url = img.get('src')
                                    
                                    if img_url and 'base64' not in img_url and 'svg' not in img_url: break
                                search_area = search_area.parent

                        # 策略 C: 寻找 background-image
                        if not img_url:
                            search_area = link
                            for _ in range(2):
                                if not search_area: break
                                divs = search_area.find_all('div', style=True)
                                for div in divs:
                                    if 'background-image' in div['style']:
                                        match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', div['style'])
                                        if match:
                                            img_url = match.group(1)
                                            break
                                search_area = search_area.parent

                        # 清洗图片链接 (去除 Shopify 尺寸后缀，如 _300x.jpg)
                        if img_url:
                            if img_url.startswith('//'): img_url = "https:" + img_url
                            img_url = re.sub(r'_\d+x(\d+)?\.', '.', img_url) # 强力去除尺寸限制

                        # 提取价格
                        price = "Check Site"
                        p_container = link.parent
                        if p_container:
                            p_text = p_container.get_text()
                            p_match = re.search(r'([€$£¥]\s?\d+([.,]\d{2})?)', p_text)
                            if p_match: price = p_match.group(0)

                        # 修正 URL
                        full_url = href
                        if not href.startswith('http'):
                            domain = "/".join(roaster['url'].split('/')[:3])
                            if not href.startswith('/'): href = '/' + href
                            full_url = domain + href

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
                        seen.add(title)

            print(f" [成功] {len(products)} 款")
            
        except Exception as e:
            print(f" [错误] {str(e)[:50]}...")
        finally:
            await context.close()
            await browser.close()
    
    return products

# ==========================================
# 主程序入口
# ==========================================
async def main_async():
    all_beans = []
    print(f"\n🚀 开始双模抓取 (API + 浏览器模拟)...\n")
    
    # 1. API 组 (同步执行)
    for roaster in SHOPIFY_ROASTERS:
        beans = fetch_shopify_api(roaster)
        all_beans.extend(beans)

    # 2. 浏览器组 (异步执行)
    for roaster in PLAYWRIGHT_ROASTERS:
        beans = await fetch_with_browser(roaster)
        all_beans.extend(beans)

    # 排序
    all_beans.sort(key=lambda x: x['published_at'], reverse=True)

    # 保存
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
