# app.py
import os
import random # 新增
import time   # 新增
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# --- 引入網路爬蟲相關函式庫 ---
import requests
from bs4 import BeautifulSoup
# -----------------------------

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

if LINE_CHANNEL_ACCESS_TOKEN is None:
    print('錯誤：請設定環境變數 LINE_CHANNEL_ACCESS_TOKEN。')
    exit(1)
if LINE_CHANNEL_SECRET is None:
    print('錯誤：請設定環境變數 LINE_CHANNEL_SECRET。')
    exit(1)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- 新增 User-Agent 列表 ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"
]

@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("簽名無效。請檢查您的 Channel Access Token 或 Channel Secret 設定。")
        abort(400)

    return 'OK'

# --- 網路爬蟲函式入口 ---
def search_component_info(component_name):
    """
    根據料件名稱，從設定的多個網站搜尋資訊。
    """
    all_results = []
    
    # 獲取一個隨機的 User-Agent 和基礎 HTTP 標頭
    random_user_agent = random.choice(USER_AGENTS)
    base_headers = {
        'User-Agent': random_user_agent,
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
    }

    # 我們將依序呼叫各個網站的爬蟲函數，並在每次呼叫後添加隨機延遲
    
    # 1. 搜尋 RS Components
    rs_results = scrape_rs_components(component_name, base_headers)
    if rs_results:
        all_results.extend(rs_results)
    time.sleep(random.uniform(2, 5)) # 隨機延遲 2 到 5 秒

    # 2. 搜尋 WAGO
    wago_results = scrape_wago(component_name, base_headers)
    if wago_results:
        all_results.extend(wago_results)
    time.sleep(random.uniform(2, 5))

    # 3. 搜尋 Digi-Key
    digikey_results = scrape_digikey(component_name, base_headers)
    if digikey_results:
        all_results.extend(digikey_results)
    time.sleep(random.uniform(2, 5))

    # 4. 搜尋 Mouser
    mouser_results = scrape_mouser(component_name, base_headers)
    if mouser_results:
        all_results.extend(mouser_results)
    time.sleep(random.uniform(2, 5))
        
    # 5. 搜尋 Octopart
    octopart_results = scrape_octopart(component_name, base_headers)
    if octopart_results:
        all_results.extend(octopart_results)
    # KSS 是 PDF，不需要延遲

    # 6. KSS PDF (特殊處理，說明困難點)
    kss_info = handle_kss_pdf_info()
    all_results.append(kss_info)

    return all_results

# --- 各個網站的專屬爬蟲函數 ---
# 請再次注意：以下程式碼的 CSS Selector (例如 class_='...') 都是範例，
# 您必須實際訪問網站，按 F12 檢查其 HTML 結構來獲取正確的 Selector。

def scrape_rs_components(component_name, headers): # <--- 已修改
    vendor_results = []
    search_url = f"https://twcn.rs-online.com/web/search/searchBrowseAction.html?sra=grp&searchTerm={component_name}"

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        product_rows = soup.find_all('tr', class_='product-row') 

        if not product_rows:
            print(f"RS Components: 未找到 '{component_name}' 相關結果。")
            return []

        for row in product_rows[:3]:
            product_link_tag = row.find('a', class_='description-link')
            product_price_tag = row.find('span', class_='price')
            product_stock_tag = row.find('span', class_='stock-value')

            if product_link_tag and product_price_tag:
                title = product_link_tag.get_text(strip=True)
                link = "https://twcn.rs-online.com" + product_link_tag['href']
                price = product_price_tag.get_text(strip=True)
                stock = product_stock_tag.get_text(strip=True) if product_stock_tag else "無資訊"

                vendor_results.append({
                    "vendor": "RS Components",
                    "name": title,
                    "link": link,
                    "price": price,
                    "stock": stock
                })

    except requests.exceptions.RequestException as e:
        print(f"RS Components 訪問錯誤: {e}")
        vendor_results.append({
            "vendor": "RS Components",
            "error": f"訪問失敗: {e}"
        })
    except Exception as e:
        print(f"RS Components 解析錯誤: {e}")
        vendor_results.append({
            "vendor": "RS Components",
            "error": "頁面解析失敗，可能網站結構有變。"
        })
    
    return vendor_results

def scrape_wago(component_name, headers): # <--- 已修改
    vendor_results = []
    search_url = f"https://www.wago.com/tw/search?query={component_name}"

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        product_cards = soup.find_all('div', class_='product-list__item') 
        
        if not product_cards:
            print(f"WAGO: 未找到 '{component_name}' 相關結果。")
            return []

        for card in product_cards[:3]:
            title_tag = card.find('h3', class_='product-list__item-title')
            link_tag = card.find('a', class_='product-list__item-link')

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                link = "https://www.wago.com" + link_tag['href']
                
                vendor_results.append({
                    "vendor": "WAGO",
                    "name": title,
                    "link": link,
                    "price": "製造商網站通常不提供價格",
                    "stock": "製造商網站通常不提供庫存"
                })

    except requests.exceptions.RequestException as e:
        print(f"WAGO 訪問錯誤: {e}")
        vendor_results.append({
            "vendor": "WAGO",
            "error": f"訪問失敗: {e}"
        })
    except Exception as e:
        print(f"WAGO 解析錯誤: {e}")
        vendor_results.append({
            "vendor": "WAGO",
            "error": "頁面解析失敗，可能網站結構有變。"
        })
    
    return vendor_results

def scrape_digikey(component_name, headers): # <--- 已修改
    vendor_results = []
    search_url = f"https://www.digikey.tw/zh/products/search?keywords={component_name}"

    print(f"正在搜尋 Digi-Key for {component_name}...")

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status() 

        if "recaptcha" in response.url or "captcha" in response.text.lower():
            print(f"Digi-Key: 可能遇到反爬蟲機制，需要手動驗證。")
            vendor_results.append({
                "vendor": "Digi-Key",
                "error": "可能遇到反爬蟲機制，請嘗試手動訪問或稍後再試。"
            })
            return vendor_results

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- **重要：這部分需要根據您 F12 觀察到的實際 HTML 結構修改** ---
        product_items = soup.find_all('div', class_='MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12 MuiGrid-grid-sm-6 MuiGrid-grid-md-4 MuiGrid-grid-lg-3') 
        
        if not product_items:
            print(f"Digi-Key: 未找到 '{component_name}' 相關產品項目，檢查選擇器或結果頁面。")
            vendor_results.append({
                "vendor": "Digi-Key",
                "error": "未找到產品結果，可能網頁結構有變或無相關產品。"
            })
            return vendor_results

        for item in product_items[:3]:
            title_tag = item.find('a', class_='MuiTypography-root MuiLink-root MuiLink-underlineNone MuiTypography-body1')
            price_tag = item.find('span', class_='MuiTypography-root MuiTypography-body1 MuiTypography-noWrap')
            stock_tag = item.find('p', class_='MuiTypography-root MuiTypography-body2 MuiTypography-colorTextSecondary')

            if title_tag and price_tag and stock_tag:
                title = title_tag.get_text(strip=True)
                link = "https://www.digikey.tw" + title_tag['href']
                price = price_tag.get_text(strip=True)
                stock = stock_tag.get_text(strip=True)

                vendor_results.append({
                    "vendor": "Digi-Key",
                    "name": title,
                    "link": link,
                    "price": price,
                    "stock": stock
                })
            else:
                print(f"Digi-Key: 某些產品資訊（標題/價格/庫存）未找到，檢查選擇器。")
                
    except requests.exceptions.RequestException as e:
        print(f"Digi-Key 訪問錯誤: {e}")
        vendor_results.append({
            "vendor": "Digi-Key",
            "error": f"訪問失敗: {e}"
        })
    except Exception as e:
        print(f"Digi-Key 解析錯誤: {e}")
        vendor_results.append({
            "vendor": "Digi-Key",
            "error": "頁面解析失敗，可能網站結構有變或選擇器錯誤。"
        })
    
    return vendor_results

def scrape_mouser(component_name, headers): # <--- 已修改
    vendor_results = []
    search_url = f"https://www.mouser.tw/Search/Refine?Keyword={component_name}"

    print(f"正在搜尋 Mouser for {component_name}...")

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        if "captcha" in response.text.lower() or "verify" in response.url.lower():
            print(f"Mouser: 可能遇到反爬蟲機制。")
            vendor_results.append({
                "vendor": "Mouser",
                "error": "可能遇到反爬蟲，請手動訪問或稍後再試。"
            })
            return vendor_results

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- **重要：這部分需要根據您 F12 觀察到的實際 HTML 結構修改** ---
        product_rows = soup.find_all('tr', class_='searchResultsRow') 

        if not product_rows:
            print(f"Mouser: 未找到 '{component_name}' 相關結果，檢查選擇器或結果頁面。")
            vendor_results.append({
                "vendor": "Mouser",
                "error": "未找到產品結果，可能網頁結構有變或無相關產品。"
            })
            return vendor_results

        for row in product_rows[:3]:
            title_link_tag = row.find('a', class_='MfrPartLink')
            price_tag = row.find('td', class_='pricing').find('span', class_='pricing-value')
            stock_tag = row.find('div', class_='availableStock')

            if title_link_tag:
                title = title_link_tag.get_text(strip=True)
                link = "https://www.mouser.tw" + title_link_tag['href']

                price = price_tag.get_text(strip=True) if price_tag else "無資訊"
                stock = stock_tag.get_text(strip=True) if stock_tag else "無資訊"

                vendor_results.append({
                    "vendor": "Mouser",
                    "name": title,
                    "link": link,
                    "price": price,
                    "stock": stock
                })
            else:
                print(f"Mouser: 某些產品資訊（標題/連結）未找到。")

    except requests.exceptions.RequestException as e:
        print(f"Mouser 訪問錯誤: {e}")
        vendor_results.append({
            "vendor": "Mouser",
            "error": f"訪問失敗: {e}"
        })
    except Exception as e:
        print(f"Mouser 解析錯誤: {e}")
        vendor_results.append({
            "vendor": "Mouser",
            "error": "頁面解析失敗，可能網站結構有變或選擇器錯誤。"
        })
    
    return vendor_results

def scrape_octopart(component_name, headers): # <--- 已修改
    vendor_results = []
    search_url = f"https://octopart.com/search?q={component_name}"

    print(f"正在搜尋 Octopart for {component_name}...")

    try:
        response = requests.get(search_url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- **重要：以下選擇器是假設內容在原始 HTML 中可見** ---
        product_cards = soup.find_all('div', class_='ProductSearch_ProductSummaryCard__vjM4O') 

        if not product_cards:
            print(f"Octopart: 未找到 '{component_name}' 相關結果，可能網頁內容動態載入或結構變動。")
            vendor_results.append({
                "vendor": "Octopart",
                "error": "未找到產品結果，可能內容動態載入或結構有變，請考慮使用進階爬蟲或 API。"
            })
            return vendor_results

        for card in product_cards[:3]:
            title_link_tag = card.find('a', class_='ProductSummaryCard_productLink__aD4sE')
            
            # 以下價格/庫存的選擇器需要您仔細觀察 Octopart 頁面來填寫
            price_tag = card.find('span', class_='ProductSummaryCard_price__some_hash') 
            stock_tag = card.find('span', class_='ProductSummaryCard_stock__some_hash') 
            
            if title_link_tag:
                title = title_link_tag.get_text(strip=True)
                link = "https://octopart.com" + title_link_tag['href']

                price = price_tag.get_text(strip=True) if price_tag else "無資訊"
                stock = stock_tag.get_text(strip=True) if stock_tag else "無資訊"

                vendor_results.append({
                    "vendor": "Octopart",
                    "name": title,
                    "link": link,
                    "price": price,
                    "stock": stock
                })
            else:
                print(f"Octopart: 某些產品資訊未找到。")

    except requests.exceptions.RequestException as e:
        print(f"Octopart 訪問錯誤: {e}")
        vendor_results.append({
            "vendor": "Octopart",
            "error": f"訪問失敗: {e}"
        })
    except Exception as e:
        print(f"Octopart 解析錯誤: {e}")
        vendor_results.append({
            "vendor": "Octopart",
            "error": "頁面解析失敗，可能網站結構有變或選擇器錯誤，或內容為JS動態載入。"
        })
    
    return vendor_results

def handle_kss_pdf_info():
    return {
        "vendor": "KSS",
        "name": "KSS 型錄 (PDF 格式)",
        "link": "https://www.kss.com.tw/filedown.php?file=catalog.pdf&site=dXBsb2FkL3RlY3Bkb3duLzQ4Ny1DUy5wZGY=",
        "price": "請自行查閱 PDF",
        "stock": "請自行查閱 PDF",
        "error": "需手動查閱 PDF 型錄，自動化查詢困難。"
    }

# --- 更新訊息處理器 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    reply_token = event.reply_token

    print(f"使用者傳送了: {user_message}") # 在您的電腦控制台印出使用者訊息

    if user_message: # 只有當使用者發送了訊息才進行查詢
        # 呼叫我們的料件查詢函數
        search_results = search_component_info(user_message)
        reply_messages = format_search_results_for_line(search_results)
    else:
        # 如果使用者發送了空訊息或其他非文字訊息，給出提示
        reply_messages = [TextSendMessage(text="您好！請輸入您想查詢的料件名稱或型號。")]

    # 使用 LINE Bot API 發送回覆訊息
    line_bot_api.reply_message(
        reply_token,
        reply_messages # 現在可以發送多個訊息或不同的訊息類型
    )

# --- 新增格式化搜尋結果的函數 (準備 LINE 訊息) ---
def format_search_results_for_line(all_results):
    """
    將所有搜尋結果格式化成 LINE 訊息。
    考慮使用多個 TextMessage 或 FlexMessage。
    """
    messages = []
    if not all_results:
        messages.append(TextSendMessage(text="抱歉，沒有找到相關料件的販售資訊。請嘗試其他關鍵字。"))
        return messages
    
    # 為了簡潔，我們現在先使用多個 TextMessage
    # 如果要更好的體驗，應該用 Flex Message (更複雜)
    
    current_message_text = "找到以下料件資訊：\n\n"
    for item in all_results:
        if isinstance(item, dict):
            # 處理錯誤訊息
            if "error" in item:
                item_text = f"廠商: {item['vendor']}\n狀態: {item['error']}\n\n"
            else:
                # 正常結果
                item_text = (
                    f"廠商: {item.get('vendor', '未知廠商')}\n"
                    f"名稱: {item.get('name', 'N/A')}\n"
                    f"價格/庫存: {item.get('price', 'N/A')} / {item.get('stock', 'N/A')}\n"
                    f"連結: {item.get('link', 'N/A')}\n\n"
                )
            
            # 檢查訊息長度，避免超出 LINE 的單條訊息限制 (2000 字元)
            if len(current_message_text) + len(item_text) > 1800: # 留點餘裕
                messages.append(TextSendMessage(text=current_message_text))
                current_message_text = "" # 重置為新訊息

            current_message_text += item_text
        else:
            # 處理直接傳遞的字符串（例如來自錯誤或提示）
            if len(current_message_text) + len(item) > 1800:
                messages.append(TextSendMessage(text=current_message_text))
                current_message_text = ""
            current_message_text += f"{item}\n\n"
    
    # 將最後剩餘的內容也加入訊息列表
    if current_message_text.strip():
        messages.append(TextSendMessage(text=current_message_text.strip()))

    return messages

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False) # 部署時 debug 應為 False