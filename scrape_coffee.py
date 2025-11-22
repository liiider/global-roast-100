import requests
import json
import re
import time
import urllib3
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

print("✅ V11.0 最终修复版已启动...")
print("📂 数据将保存在脚本所在目录")

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 目标名单
# ==========================================

# A组：标准 Shopify API
SHOPIFY_ROASTERS = [
    # --- 修正：Glitch 放 API 组是对的 (上次抓到了2个) ---
    {"name": "Glitch Coffee", "country": "Japan", "url": "https://shop.glitchcoffee.com"}, 

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
    {"name": "Kurasu", "country": "Japan", "url": "https://kurasu.kyoto"},
    {"name": "Onibus Coffee", "country": "Japan", "url": "https://onibuscoffee.com"},
    {"name": "Switch Coffee Tokyo", "country": "Japan", "url": "https://switchcoffeetokyo.com"},
    {"name": "Mel Coffee Roasters", "country": "Japan", "url": "https://melcoffee.jp"},
    {"name": "The Cupping Room", "country": "Hong Kong", "url": "https://cuppingroom.hk"},
    {"name": "ONA Coffee", "country": "Australia", "url": "https://onacoffee.com.au"},
    {"name": "Market Lane", "country": "Australia", "url": "https://marketlane.com.au"},
    {"name": "Seven Seeds", "country": "Australia", "url": "https://sevenseeds.com.au"},
    {"name": "Code Black", "country": "Australia", "url": "https://codeblackcoffee.com.au"},
    {"name": "Reuben Hills", "country": "Australia", "url": "https://reubenhills.com.au"},
    {"name": "Flight Coffee", "country": "New Zealand", "url": "https://flightcoffee.co.nz"},
]

# B组：HTML 模式
HTML_ROASTERS = [
    # 修正：Gardelli 移回 HTML 组，API 即使网址对了也容易被封
    {"name": "Gardelli", "country": "Italy", "url": "https://shop.gardellicoffee.com/collections/coffees", "parser": "shopify_html"},
    
    {"name": "Tim Wendelboe", "country": "Norway", "url": "https://timwendelboe.no/product-category/coffee/", "parser": "woo"},
    {"name": "A Matter of Concrete", "country": "Netherlands", "url": "https://amatterofconcrete.com/product-category/coffee/", "parser": "woo"},
    {"name": "Manhattan", "country": "Netherlands", "url": "https://manhattan.coffee/catalog/coffee", "parser": "manhattan"},
    
    # 必须用 HTML 抓取的 Shopify 站
    {"name": "Friedhats", "country": "Netherlands", "url": "https://friedhats.com/collections/coffees", "parser": "shopify_html"},
    {"name": "Leaves Coffee", "country": "Japan", "url": "https://leavescoffee.jp/collections/coffee-beans", "parser": "shopify_html"},
    {"name": "Canyon Coffee", "country": "USA", "url": "https://canyoncoffee.co/collections/coffee", "parser": "shopify_html"},
    {"name": "Three Marks Coffee", "country": "Spain", "url": "https://www.threemarkscoffee.com/collections/coffee", "parser": "shopify_html"},
    {"name": "Fjord Coffee", "country": "Germany", "url": "https://fjord-coffee-roasters.com/collections/coffee-beans", "parser": "shopify_html"},
]

# ==========================================
# 2. 工具函数
# ==========================================
def get_headers():
    # 增强伪装
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"'
    }

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()[:200] + "..."

def is_fresh_drop(date_str):
    if not date_str: return False
    try:
        pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        thirty_days_ago = datetime.now(pub_date.tzinfo) - timedelta(days=30)
        return pub_date >= thirty_days_ago
    except:
        return True

# ==========================================
# 3. 抓取逻辑
# ==========================================

def fetch_shopify_api(roaster):
    print(f"👉 正在连接: {roaster['name']} ...", end="", flush=True)
    url = f"{roaster['url'].rstrip('/')}/products.json?limit=250"
    products = []
    
    try:
        # 超时延长至 40 秒
        r = requests.get(url, headers=get_headers(), timeout=40, verify=False)
        if r.status_code != 200: 
            print(f" [跳过] 状态码: {r.status_code}")
            return []
        
        data = r.json()
        for item in data.get('products', []):
            title = item.get('title', '')
            p_type = item.get('product_type', '').lower()
            pub_at = item.get('published_at')
            
            if any(k in title.lower() for k in ['subscription', 'gift card', 'workshop', 'merch', 'tee', 'sample', 'course', 'equipment', 'dripper']): continue
            
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
                "description": clean_html(item.get('body_html', '')),
                "published_at": pub_at,
                "source_type": "api"
            })
        print(f" [成功] {len(products)} 款新品")
    except Exception as e:
        print(f" [超时]")
        
    return products

def fetch_html_parse(roaster):
    print(f"🕵️ [HTML] 正在潜入: {roaster['name']} ...", end="", flush=True)
    products = []
    try:
        r = requests.get(roaster['url'], headers=get_headers(), timeout=40, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # --- Woo 模式 ---
        if roaster['parser'] == 'woo':
            # 扩大搜索范围：li 或 div (某些主题用 div)
            items = soup.find_all(['li', 'div'], class_=lambda x: x and 'product' in x and 'type-product' in x)
            for item in items:
                try:
                    title_el = item.find(['h2', 'h3'], class_=lambda x: x and 'title' in x)
                    if not title_el: title_el = item.find(['h2', 'h3'])
                    if not title_el: continue
                    
                    title = title_el.get_text(strip=True)
                    if "subscription" in title.lower(): continue
                    
                    link_el = item.find('a')
                    link = link_el['href'] if link_el else ""
                    
                    price_el = item.find(class_=lambda x: x and 'price' in x)
                    price = price_el.get_text(strip=True).replace("kr","").strip() if price_el else "Check Site"
                    
                    img_el = item.find('img')
                    img = img_el['src'] if img_el else ""
                    
                    if title and link:
                        products.append({
                            "roaster_name": roaster['name'],
                            "roaster_country": roaster['country'],
                            "name": title,
                            "url": link,
                            "image": img,
                            "price": price,
                            "description": "Specialty Coffee.",
                            "published_at": datetime.now().isoformat()
                        })
                except: continue
        
        # --- Shopify HTML 模式 (修正版) ---
        elif roaster['parser'] == 'shopify_html':
            links = soup.find_all('a', href=True)
            seen = set()
            for link in links:
                href = link['href']
                if '/products/' in href and not any(x in href for x in ['sub', 'gift', 'merch', 'login']):
                    container = link
                    # 向上寻找容器
                    found = False
                    for _ in range(4):
                        if not container: break
                        
                        # 修正点：扩大标题搜索范围，包含 h2 和 a 和 p
                        title_el = container.find(['h2', 'h3', 'h4', 'a', 'span', 'p', 'div'], class_=lambda x: x and ('title' in x or 'name' in x))
                        # 如果找不到带 title class 的，就找普通的 h2/h3
                        if not title_el: title_el = container.find(['h2', 'h3'])
                        # 如果还是找不到，就把 link 自己的文本通过
                        if not title_el and len(link.get_text(strip=True)) > 3: title_el = link

                        img_el = container.find('img')
                        
                        if title_el:
                            title = title_el.get_text(strip=True)
                            if len(title) > 3 and len(title) < 120 and title not in seen:
                                # 二次过滤杂项
                                if any(k in title.lower() for k in ['box', 'gift', 'sub', 'course', 'filter papers']): break

                                # URL 修复
                                full_url = href if href.startswith('http') else roaster['url'].split('/collections')[0] + href
                                
                                # 图片修复
                                img_url = ""
                                if img_el:
                                    img_url = img_el.get('src') or img_el.get('data-src') or ""
                                    if img_url.startswith('//'): img_url = "https:" + img_url
                                
                                products.append({
                                    "roaster_name": roaster['name'],
                                    "roaster_country": roaster['country'],
                                    "name": title,
                                    "url": full_url,
                                    "image": img_url,
                                    "price": "Check Site",
                                    "description": f"Fresh from {roaster['name']}",
                                    "published_at": datetime.now().isoformat()
                                })
                                seen.add(title)
                                found = True
                                break
                        container = container.parent
                    if found: continue

        # --- Manhattan ---
        elif roaster['parser'] == 'manhattan':
            links = soup.find_all('a', href=True)
            seen = set()
            for link in links:
                if '/catalog/coffee/' in link['href']:
                    try:
                        title = link.get_text(strip=True)
                        if not title: 
                            t_el = link.find(['h2','h3'])
                            if t_el: title = t_el.get_text(strip=True)
                        
                        if title and title not in seen and "Filter" not in title:
                            products.append({
                                "roaster_name": roaster['name'],
                                "roaster_country": roaster['country'],
                                "name": title,
                                "url": "https://manhattan.coffee" + link['href'],
                                "image": "",
                                "price": "Check Site",
                                "description": "Competition grade coffee.",
                                "published_at": datetime.now().isoformat()
                            })
                            seen.add(title)
                    except: continue

        print(f" [成功] {len(products)} 款")
    except Exception as e:
        print(f" [超时/错误]")
    
    return products

# ==========================================
# 主程序
# ==========================================
def main():
    all_beans = []
    print(f"\n🚀 开始抓取 (超时设定: 40秒)...")
    
    for roaster in SHOPIFY_ROASTERS:
        beans = fetch_shopify_api(roaster)
        all_beans.extend(beans)

    for roaster in HTML_ROASTERS:
        beans = fetch_html_parse(roaster)
        all_beans.extend(beans)

    all_beans.sort(key=lambda x: x['published_at'], reverse=True)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'data.json')

    print(f"\n💾 正在保存到: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(all_beans, f, ensure_ascii=False, indent=2)
        
    print(f"🎉 抓取结束! 总收录: {len(all_beans)} 款豆子")

if __name__ == "__main__":
    main()

