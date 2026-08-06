import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta

# ===== 配置区 =====
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
if not NEWSAPI_KEY:
    raise ValueError("请在环境变量 NEWSAPI_KEY 中设置 NewsAPI 密钥")
KEYWORDS = '"人工智能" OR "具身智能"'
FROM_DATE = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

# 新疆政策抓取页（政策解读栏目）
XINJIANG_POLICY_URL = "http://www.xinjiang.gov.cn/xinjiang/zcjd/zcjd.shtml"
# ===================

def fetch_newsapi():
    """从 NewsAPI 获取行业新闻"""
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': KEYWORDS,
        'from': FROM_DATE,
        'sortBy': 'publishedAt',
        'language': 'zh',
        'pageSize': 100,
        'apiKey': NEWSAPI_KEY
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"NewsAPI 请求失败: {resp.status_code}")
        return []
    data = resp.json()
    if data.get('status') != 'ok':
        print(f"NewsAPI 错误: {data.get('message')}")
        return []
    articles = []
    for art in data['articles']:
        title = art['title']
        description = art['description'] or ''
        url = art['url']
        published = art['publishedAt']
        source = art['source']['name']
        # 分类
        combined_text = title + description
        category = 'general'
        if any(w in combined_text for w in ['融资', '轮融资', '获投', '投资', '估值']):
            category = '融资'
        elif any(w in combined_text for w in ['发布', '推出', '新品', '上市']):
            category = '产品发布'
        elif any(w in combined_text for w in ['案例', '落地', '合作', '应用']):
            category = '案例与合作'
        articles.append({
            'title': title,
            'description': description,
            'url': url,
            'published': published,
            'source': source,
            'category': category
        })
    return articles

def fetch_xinjiang_policy():
    """抓取新疆政策解读列表"""
    try:
        resp = requests.get(XINJIANG_POLICY_URL, timeout=10)
        resp.encoding = 'utf-8'
    except Exception as e:
        print(f"新疆政策页请求失败: {e}")
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    policies = []
    # 根据页面结构调整选择器（已提供多个备选）
    items = soup.select('.list-content li') or soup.select('.news-list li') or soup.select('ul.list li')
    for li in items[:10]:
        a_tag = li.find('a')
        if a_tag:
            title = a_tag.get_text(strip=True)
            href = a_tag.get('href', '')
            if href and not href.startswith('http'):
                base = 'http://www.xinjiang.gov.cn'
                href = base + href if href.startswith('/') else base + '/' + href
            date_tag = li.find('span') or li.find('em')
            date = date_tag.get_text(strip=True) if date_tag else ''
            policies.append({
                'title': title,
                'url': href,
                'date': date
            })
    return policies

def classify_and_organize(news_items, policies):
    """将数据组织成日报需要的结构"""
    data = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'policies': policies,
        'funding_news': [],
        'product_news': [],
        'case_news': [],
        'general_news': []
    }
    for item in news_items:
        if item['category'] == '融资':
            data['funding_news'].append(item)
        elif item['category'] == '产品发布':
            data['product_news'].append(item)
        elif item['category'] == '案例与合作':
            data['case_news'].append(item)
        else:
            data['general_news'].append(item)
    return data

def generate_html(data):
    """生成美观的静态日报 HTML"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI & 具身智能 市场日报</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: auto; padding: 20px; background: #f5f7fa; }}
  h1 {{ color: #2c3e50; }}
  .section {{ margin: 30px 0; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
  .section h2 {{ margin-top: 0; color: #16a085; }}
  ul {{ list-style: none; padding-left: 0; }}
  li {{ margin: 10px 0; padding: 10px; border-bottom: 1px solid #eee; }}
  a {{ color: #2980b9; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .meta {{ font-size: 0.8em; color: #7f8c8d; }}
  .update {{ text-align: right; color: #95a5a6; margin-bottom: 20px; }}
</style>
</head>
<body>
  <h1>🤖 AI & 具身智能 市场日报</h1>
  <div class="update">更新时间：{data['update_time']}</div>

  <div class="section">
    <h2>📜 新疆政策发布</h2>
    <ul>
"""
    for p in data['policies']:
        html += f"""<li><a href="{p['url']}" target="_blank">{p['title']}</a> <span class="meta">{p['date']}</span></li>\n"""
    html += "</ul></div>"

    # 融资动态
    html += '<div class="section"><h2>💰 融资动态</h2><ul>'
    for n in data['funding_news']:
        html += f"""<li><a href="{n['url']}" target="_blank">{n['title']}</a> <span class="meta">{n['source']} | {n['published'][:10]}</span></li>\n"""
    html += "</ul></div>"

    # 产品发布
    html += '<div class="section"><h2>🚀 产品发布</h2><ul>'
    for n in data['product_news']:
        html += f"""<li><a href="{n['url']}" target="_blank">{n['title']}</a> <span class="meta">{n['source']} | {n['published'][:10]}</span></li>\n"""
    html += "</ul></div>"

    # 案例与合作
    html += '<div class="section"><h2>🏗️ 案例与合作</h2><ul>'
    for n in data['case_news']:
        html += f"""<li><a href="{n['url']}" target="_blank">{n['title']}</a> <span class="meta">{n['source']} | {n['published'][:10]}</span></li>\n"""
    html += "</ul></div>"

    # 综合动态
    html += '<div class="section"><h2>📰 综合动态</h2><ul>'
    for n in data['general_news']:
        html += f"""<li><a href="{n['url']}" target="_blank">{n['title']}</a> <span class="meta">{n['source']} | {n['published'][:10]}</span></li>\n"""
    html += "</ul></div>"

    html += "</body></html>"
    return html

def main():
    print("开始抓取行业新闻...")
    news = fetch_newsapi()
    print(f"获取到 {len(news)} 条新闻")
    print("抓取新疆政策...")
    policies = fetch_xinjiang_policy()
    print(f"获取到 {len(policies)} 条政策")
    data = classify_and_organize(news, policies)
    html_content = generate_html(data)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("日报已生成：index.html，用浏览器打开即可查看。")

if __name__ == '__main__':
    main()