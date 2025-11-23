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

print("✅ V16.0 终极版 (Friedhats 深潜模式 + JSON-LD) 已启动...")
print("📂 正在初始化混合动力引擎...")

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 目标名单配置
# ==========================================

# A组：API 模式 (速度快，优先使用)
SHOPIFY_ROASTERS = [
    {"name": "Glitch Coffee", "country": "Japan", "url": "https://shop.glitchcoffee.com"}, 
    {"name": "Kurasu", "country": "Japan", "url": "https://kurasu.kyoto"},
    {"name": "Onibus Coffee", "country": "Japan", "url": "https://onibuscoffee.com"},
    {"name": "Mel Coffee Roasters", "country": "Japan", "url": "https://melcoffee.jp"},
    {"name": "The Cupping Room", "country": "Hong Kong", "url": "https://cuppingroom.hk"},
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

# B组：浏览器模式 (Friedhats 开启 deep_crawl)
PLAYWRIGHT_ROASTERS = [
    # ！！！重点：Friedhats 开启 deep_crawl=True，强制进入详情页抓取！！！
    {"name": "Friedhats", "country": "Netherlands", "url": "https://friedhats.com/collections/coffees", "deep_crawl": True},
    
    # 其他网站继续尝试列表页抓取，如果也出现问题，可以把 deep_crawl 设为 True
    {"name": "Canyon Coffee", "country": "USA", "url": "https://canyoncoffee.co/collections/coffee", "deep_crawl": False},
    {"name": "Leaves Coffee", "country": "Japan", "url": "https://leavescoffee.jp/collections/coffee-beans", "deep_crawl": False},
    {"name": "Three Marks Coffee", "country": "Spain", "url": "https://www.threemarkscoffee.com/collections/coffee", "deep_crawl": False},
    {"name": "Fjord Coffee", "country": "Germany", "url": "https://fjord-coffee-roasters.com/collections/coffee-beans", "deep_crawl": False},
    {"name": "Manhattan", "country": "Netherlands", "url": "https://manhattan.coffee/catalog/coffee", "deep_crawl": False},
    {"name": "Gardelli", "country": "Italy", "url": "https://shop.gardellicoffee.com/collections/coffees", "deep_crawl": False},
    {"name": "Tim Wendelboe", "country": "Norway", "url": "https://timwendelboe.no/product-category/coffee/", "deep_crawl": False},
    {"name": "A Matter of Concrete", "country": "Netherlands", "url": "https://amatterofconcrete.com/product-category/coffee/", "deep_crawl": False},
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
        thirty_days_ago = datetime.now(pub_date.tzinfo) - timedelta(days=45) 
        return pub_date >= thirty_days_ago
    except:
        return True

# ==========================================
# 引擎 1: API (保持不变)
# ==========================================
def fetch_shopify_api(roaster):
    print(f"👉 [API] 正在连接: {roaster['name']} ...", end="", flush=True)
    url = f"{roaster['url'].rstrip('/')}/products.json?limit=250"
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
# 引擎 2: Playwright (Deep Crawl 增强版)
# ==========================================
async def fetch_with_browser(roaster):
    print(f"🕵️ [Browser] 正在渲染: {roaster['name']} ...", end="", flush=True)
    products = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()
        
        try:
            # 1. 访问列表页收集链接
            await page.goto(roaster['url'], timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # 滚动加载更多
            for _ in range(3):
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(1)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            links = soup.find_all('a', href=True)
            candidate_urls = []
            seen_titles = set()
            
            # 初步筛选链接
            for link in links:
                href = link['href']
                is_product = False
                if '/products/' in href or '/product/' in href or '/catalog/coffee/' in href:
                    is_product = True
                if is_product and not any(x in href for x in ['sub', 'gift', 'merch', 'login', 'account', 'page', 'cart']):
                    title = link.get_text(strip=True)
                    # 简单过滤标题
                    if not title or len(title) < 3:
                        t_el = link.find(['h2', 'h3', 'h4'], text=True)
                        if t_el: title = t_el.get_text(strip=True)
                    
                    if title and title not in seen_titles:
                        if any(k in title.lower() for k in ['subscription', 'gift', 'course', 'workshop']): continue
                        
                        # 补全 URL
                        full_url = href
                        if not href.startswith('http'):
                            domain = "/".join(roaster['url'].split('/')[:3])
                            if not href.startswith('/'): href = '/' + href
                            full_url = domain + href
                        
                        # 保存待处理
                        clean_url = full_url.split('?')[0]
                        candidate_urls.append({"title": title, "url": clean_url, "el": link})
                        seen_titles.add(title)

            # 2. 判断是否需要“深潜” (Deep Crawl)
            # 如果配置了 deep_crawl=True (如 Friedhats)，或者列表页没抓到图片
            do_deep_crawl = roaster.get('deep_crawl', False)
            
            final_products = []
            
            if do_deep_crawl:
                print(f" [深潜模式: 需访问 {len(candidate_urls)} 个详情页] ", end="", flush=True)
                
                for i, item in enumerate(candidate_urls):
                    try:
                        # 限制一下数量，防止太慢，通常咖啡店新品也就10-20个
                        if i > 25: break 
                        
                        # 访问详情页
                        await page.goto(item['url'], timeout=30000, wait_until="domcontentloaded")
                        
                        # 抓取 OpenGraph Meta Data (最稳的数据源)
                        # 图片
                        img_url = await page.get_attribute('meta[property="og:image"]', 'content')
                        if not img_url: 
                            img_url = await page.get_attribute('meta[property="og:image:secure_url"]', 'content')
                        
                        # 价格
                        price = await page.get_attribute('meta[property="og:price:amount"]', 'content')
                        currency = await page.get_attribute('meta[property="og:price:currency"]', 'content')
                        if not price:
                            # 尝试找 JSON-LD 里的价格
                            try:
                                json_data = await page.locator('script[type="application/ld+json"]').all_inner_texts()
                                for j in json_data:
                                    jd = json.loads(j)
                                    if 'offers' in jd:
                                        offers = jd['offers']
                                        if isinstance(offers, list): price = offers[0].get('price')
                                        elif isinstance(offers, dict): price = offers.get('price')
                                        break
                            except: pass

                        # 格式化
                        if not price: price = "Check Site"
                        else: 
                            if currency: price = f"{price} {currency}"
                            else: price = f"{price}"

                        if img_url:
                             # 清洗图片链接
                            if img_url.startswith('//'): img_url = "https:" + img_url
                            img_url = re.sub(r'_\d+x(\d+)?\.', '.', img_url)

                        final_products.append({
                            "roaster_name": roaster['name'],
                            "roaster_country": roaster['country'],
                            "name": item['title'],
                            "url": item['url'],
                            "image": img_url or "",
                            "price": price,
                            "description": f"Fresh from {roaster['name']}",
                            "published_at": datetime.now().isoformat(),
                            "source_type": "deep_browser"
                        })
                        print(".", end="", flush=True) # 进度条点点点
                        
                    except Exception as e:
                        print("x", end="", flush=True)
                        continue
                        
            else:
                # 常规模式：只解析列表页 HTML
                # (这里复用之前的列表页解析逻辑，为节省篇幅，核心就是把之前的逻辑放在这里)
                # 为了保证代码完整性，我这里简单写回之前的逻辑
                for item in candidate_urls:
                    link = item['el']
                    title = item['title']
                    full_url = item['url']
                    
                    # 尝试在列表页找图片
                    img_url = ""
                    search_area = link
                    for _ in range(3):
                        if not search_area: break
                        img = search_area.find('img')
                        if img:
                            srcset = img.get('srcset')
                            if srcset: img_url = srcset.split(',')[-1].strip().split(' ')[0]
                            if not img_url: img_url = img.get('src') or img.get('data-src')
                            if img_url and 'base64' not in img_url: break
                        search_area = search_area.parent
                    
                    if img_url:
                        if img_url.startswith('//'): img_url = "https:" + img_url
                        img_url = re.sub(r'_\d+x(\d+)?\.', '.', img_url)

                    # 尝试在列表页找价格
                    price = "Check Site"
                    p_container = link.parent
                    if p_container:
                        p_text = p_container.get_text()
                        p_match = re.search(r'([€$£¥]\s?\d+([.,]\d{2})?)', p_text)
                        if p_match: price = p_match.group(0)

                    final_products.append({
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

            print(f" [成功] {len(final_products)} 款")
            products = final_products
            
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
    
    # 1. API 组
    for roaster in SHOPIFY_ROASTERS:
        beans = fetch_shopify_api(roaster)
        all_beans.extend(beans)

    # 2. 浏览器组
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
