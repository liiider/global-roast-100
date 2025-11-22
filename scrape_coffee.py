import requests
import json
import re
from datetime import datetime

# 1. 经过验证的“白名单”网站 (已修正 Gardelli)
ROASTERS = [
    {"id": "la_cabra", "name": "La Cabra", "country": "Denmark", "url": "https://www.lacabra.dk"},
    {"id": "april", "name": "April Coffee", "country": "Denmark", "url": "https://www.aprilcoffeeroasters.com"},
    {"id": "coffee_collective", "name": "Coffee Collective", "country": "Denmark", "url": "https://coffeecollective.dk"},
    {"id": "onyx", "name": "Onyx Coffee Lab", "country": "USA", "url": "https://onyxcoffeelab.com"},
    {"id": "sey", "name": "Sey Coffee", "country": "USA", "url": "https://www.seycoffee.com"},
    {"id": "the_barn", "name": "The Barn", "country": "Germany", "url": "https://thebarn.de"},
    {"id": "kurasu", "name": "Kurasu", "country": "Japan", "url": "https://kurasu.kyoto"},
    {"id": "ona", "name": "ONA Coffee", "country": "Australia", "url": "https://onacoffee.com.au"},
    {"id": "gardelli", "name": "Gardelli", "country": "Italy", "url": "https://gardellicoffees.com"}, # 修正后的网址
]

def clean_html(raw_html):
    """简单的 HTML 清洗，去除标签，只留文字"""
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()[:200] + "..." # 只取前200字作为简介

def fetch_shopify_data(roaster):
    """抓取单个 Shopify 网站的数据"""
    print(f"☕ 正在抓取: {roaster['name']} ...")
    
    url = f"{roaster['url'].rstrip('/')}/products.json?limit=30" # 每次抓最新30个
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    products = []
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"   ❌ 失败: 状态码 {r.status_code}")
            return []
            
        data = r.json()
        
        for item in data.get('products', []):
            # --- 过滤器 ---
            title = item.get('title', '')
            product_type = item.get('product_type', '').lower()
            tags = [t.lower() for t in item.get('tags', [])]
            
            # 排除掉非咖啡豆商品 (比如 Gift Card, Subscription, Merch, Equipment)
            # 关键词排除法
            exclude_keywords = ['subscription', 'gift card', 'course', 'workshop', 'tee', 'tote', 'paper', 'brewer']
            if any(k in title.lower() for k in exclude_keywords):
                continue
                
            # 确保是咖啡 (有些网站 type 没写，所以也要看 title)
            is_coffee = 'coffee' in product_type or 'bean' in product_type or 'coffee' in title.lower()
            if not is_coffee:
                continue

            # --- 数据提取 ---
            variant = item['variants'][0] if item['variants'] else {}
            price = variant.get('price', '0')
            
            # 寻找图片
            image_src = ""
            if item.get('images'):
                image_src = item['images'][0].get('src', '')

            bean = {
                "roaster_name": roaster['name'],
                "roaster_country": roaster['country'],
                "name": title,
                "url": f"{roaster['url']}/products/{item['handle']}",
                "image": image_src,
                "price": price,
                "currency": "Local", # 暂时没法统一货币，先存数值
                "description": clean_html(item.get('body_html', '')),
                "published_at": item.get('published_at', ''),
                "tags": item.get('tags', [])[:3] # 只取前3个标签
            }
            products.append(bean)
            
        print(f"   ✅ 成功获取 {len(products)} 款豆子")
        return products

    except Exception as e:
        print(f"   ❌ 出错: {e}")
        return []

def main():
    all_beans = []
    
    print(f"🚀 开始全网抓取 ({datetime.now().strftime('%Y-%m-%d %H:%M')})...\n")
    
    for roaster in ROASTERS:
        beans = fetch_shopify_data(roaster)
        all_beans.extend(beans)
        
    # 按发布时间倒序排列 (最新的在最上面)
    all_beans.sort(key=lambda x: x['published_at'], reverse=True)
    
    # 保存为 data.json
    output_file = "data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_beans, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 抓取完成!")
    print(f"共收录: {len(all_beans)} 款咖啡豆")
    print(f"文件已保存至: {output_file}")

if __name__ == "__main__":
    main()