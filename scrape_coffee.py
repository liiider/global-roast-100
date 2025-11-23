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

print("✅ V14.0 全自动浏览器模拟版已启动...")
print("📂 正在初始化混合动力引擎 (API + Playwright)...")

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 目标名单
# ==========================================

# A组：API 模式 (速度快，优先使用)
SHOPIFY_ROASTERS = [
    # 日本/亚洲
    {"name": "Glitch Coffee", "country": "Japan", "url": "https://shop.glitchcoffee.com"}, 
    {"name": "Kurasu", "country": "Japan", "url": "https://kurasu.kyoto"},
    {"name": "Onibus Coffee", "country": "Japan", "url": "https://onibuscoffee.com"},
    {"name": "Switch Coffee Tokyo", "country": "Japan", "url": "https://switchcoffeetokyo.com"},
    {"name": "Mel Coffee Roasters", "country": "Japan", "url": "https://melcoffee.jp"},
    {"name": "The Cupping Room", "country": "Hong Kong", "url": "https://cuppingroom.hk"},
    
    # 北欧
    {"name": "La Cabra", "country": "Denmark", "url": "https://www.lacabra.dk"},
    {"name": "April Coffee", "country": "Denmark", "url": "https://www.aprilcoffeeroasters.com"},
    {"name": "Coffee Collective", "country": "Denmark", "url": "https://coffeecollective.dk"},
    {"name": "Koppi", "country": "Sweden", "url": "https://www.koppi.se"},
    {"name": "Drop Coffee", "country": "Sweden", "url": "https://www.dropcoffee.com"},
    {"name": "Morgon Coffee Roasters", "country": "Sweden", "url": "https://www.morgoncoffeeroasters.com"},
    {"name": "Five Elephant", "country": "Germany", "url": "https://www.fiveelephant.com"},
    {"name": "The Barn", "country": "Germany", "url": "https://thebarn.de"},
    
    # 欧美其他
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
    
    # 澳洲
    {"name": "ONA Coffee", "country": "Australia", "url": "https://onacoffee.com.au"},
    {"name": "Market Lane", "country": "Australia", "url": "https://marketlane.com.au"},
    {"name": "Seven Seeds", "country": "Australia", "url": "https://sevenseeds.com.au"},
    {"name": "Code Black", "country": "Australia", "url": "https://codeblackcoffee.com.au"},
    {"name": "Reuben Hills", "country": "Australia", "url": "https://reubenhills.com.au"},
    {"name": "Flight Coffee", "country": "New Zealand", "url": "https://flightcoffee.co.nz"},
]

# B组：浏览器模拟模式 (针对之前抓不到的硬骨头)
PLAYWRIGHT_ROASTERS = [
    # 之前死活抓不到的
    {"name": "Manhattan", "country": "Netherlands", "url": "https://manhattan.coffee/catalog/coffee", "selector": "a[href*='/catalog/coffee/']"},
    {"name": "Friedhats", "country": "Netherlands", "url": "https://friedhats.com/collections/coffees", "selector": "a[href*='/products/']"},
    {"name": "Leaves Coffee", "country": "Japan", "url": "https://leavescoffee.jp/collections/coffee-beans", "selector": "a[href*='/products/']"},
    {"name": "Gardelli", "country": "Italy", "url": "https://shop.gardellicoffee.com/collections/coffees", "selector": "div.product-item"},
    {"name": "Fjord Coffee", "country": "Germany", "url": "https://fjord-coffee-roasters.com/collections/coffee-beans", "selector": "a[href*='/products/']"},
    
    # WooCommerce 网站
    {"name": "Tim Wendelboe", "country": "Norway", "url": "https://timwendelboe.no/product-category/coffee/", "selector": "li.product"},
    {"name": "A Matter of Concrete", "country": "Netherlands", "url": "https://amatterofconcrete.com/product-category/coffee/", "selector": "li.product"},
    {"name": "Three Marks Coffee", "country": "Spain", "url": "https://www.threemarkscoffee.com/collections/coffee", "selector": "a[href*='/products/']"},
    {"name": "Canyon Coffee", "country": "USA", "url": "https://canyoncoffee.co/collections/coffee", "selector": "a[href*='/products/']"},
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
        thirty_days_ago = datetime.now(pub_date.tzinfo) - timedelta(days=30)
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
            
            if any(k in title.lower() for k in ['subscription', 'gift', 'merch', 'tee', 'sample', 'course', 'equipment', 'dripper']): continue
            
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
# 引擎 2: Playwright (浏览器模拟)
# ==========================================
async def fetch_with_browser(roaster):
    print(f"🕵️ [Browser] 正在渲染: {roaster['name']} ...", end="", flush=True)
    products = []
    
    async with async_playwright() as p:
        # 启动无头浏览器
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 设置超时 40秒
            await page.goto(roaster['url'], timeout=40000, wait_until="domcontentloaded")
            
            # 等待页面稍微加载一下
            await asyncio.sleep(3)
            
            # 获取页面内容
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # --- 通用 HTML 解析逻辑 (复用之前的强力解析) ---
            # 寻找所有链接
            links = soup.find_all('a', href=True)
            seen = set()
            
            for link in links:
                href = link['href']
                
                # 判定是否为产品链接
                is_product = False
                if '/products/' in href: is_product = True # Shopify
                if '/product/' in href: is_product = True # WooCommerce
                if '/catalog/coffee/' in href: is_product = True # Manhattan
                
                if is_product and not any(x in href for x in ['sub', 'gift', 'merch', 'login', 'account']):
                    
                    # 提取标题
                    title = link.get_text(strip=True)
                    if len(title) < 5: # 标题太短，尝试找子元素
                        t_el = link.find(['h2', 'h3', 'h4', 'div'])
                        if t_el: title = t_el.get_text(strip=True)
                    
                    # 如果还是没标题，向上找父容器
                    container = link
                    if not title:
                        for _ in range(3):
                            if not container: break
                            container = container.parent
                            t_el = container.find(['h2', 'h3', 'h4', 'a'], class_=lambda x: x and ('title' in x or 'name' in x))
                            if t_el: 
                                title = t_el.get_text(strip=True)
                                break
                    
                    # 验证标题有效性
                    if title and title not in seen and len(title) > 3 and len(title) < 100:
                        if any(k in title.lower() for k in ['subscription', 'gift', 'course']): continue
                        
                        # 提取图片
                        img_url = ""
                        container = link
                        for _ in range(4):
                            if not container: break
                            img = container.find('img')
                            if img:
                                img_url = img.get('src') or img.get('data-src') or img.get('srcset') or ""
                                if img_url.startswith('//'): img_url = "https:" + img_url
                                if 'base64' in img_url: img_url = "" # 忽略 base64 占位图
                                break
                            container = container.parent
                        
                        # 提取价格
                        price = "Check Site"
                        container = link
                        for _ in range(4):
                            if not container: break
                            p_el = container.find(string=re.compile(r'[\$€¥kr]'))
                            if p_el:
                                p_match = re.search(r'[\d\.,]+', p_el)
                                if p_match: 
                                    price = p_match.group(0)
                                    break
                            container = container.parent

                        # 修正 URL
                        full_url = href
                        if not href.startswith('http'):
                            base = "/".join(roaster['url'].split('/')[:3])
                            full_url = base + href

                        products.append({
                            "roaster_name": roaster['name'],
                            "roaster_country": roaster['country'],
                            "name": title,
                            "url": full_url,
                            "image": img_url,
                            "price": price,
                            "description": f"Fresh from {roaster['name']}",
                            "published_at": datetime.now().isoformat(), # 实时抓取默认最新
                            "source_type": "browser"
                        })
                        seen.add(title)

            print(f" [成功] {len(products)} 款")
            
        except Exception as e:
            print(f" [错误] {str(e)[:50]}...")
        finally:
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
