# app.py

import os
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
    all_results = [] # 儲存所有網站的搜尋結果

    # 我們將依序呼叫各個網站的爬蟲函數
    # 1. 搜尋 RS Components
    rs_results = scrape_rs_components(component_name)
    if rs_results:
        all_results.extend(rs_results)

    # 2. 搜尋 WAGO
    wago_results = scrape_wago(component_name)
    if wago_results:
        all_results.extend(wago_results)

    # 3. 搜尋 Digi-Key (這是範例，需要您自行實現)
    digikey_results = scrape_digikey(component_name)
    if digikey_results:
        all_results.extend(digikey_results)

    # 4. 搜尋 Mouser (這是範例，需要您自行實現)
    mouser_results = scrape_mouser(component_name)
    if mouser_results:
        all_results.extend(mouser_results)
        
    # 5. 搜尋 Octopart (這是範例，可能需要進階技術)
    octopart_results = scrape_octopart(component_name)
    if octopart_results:
        all_results.extend(octopart_results)

    # 6. KSS PDF (特殊處理，說明困難點)
    kss_info = handle_kss_pdf_info() # 專門處理 KSS 的提示信息
    all_results.append(kss_info)

    return all_results

# --- 各個網站的專屬爬蟲函數 ---
# 請再次注意：以下程式碼的 CSS Selector (例如 class_='...') 都是範例，
# 您必須實際訪問網站，按 F12 檢查其 HTML 結構來獲取正確的 Selector。
# 如果這些函數中的爬蟲邏輯沒有正確抓到資料，它們會回傳空的列表或包含錯誤的字典。

def scrape_rs_components(component_name):
    vendor_results = []
    # 範例 URL，請確認 RS Components 實際的搜尋 URL 格式
    search_url = f"https://twcn.rs-online.com/web/search/searchBrowseAction.html?sra=grp&searchTerm={component_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status() # 如果狀態碼不是 200，拋出異常
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- RS Components 網頁結構分析範例 ---
        # 這是撰寫時的可能結構，未來可能變動。
        # 您需要使用 F12 檢查，找到包含產品資訊的 HTML 元素
        product_rows = soup.find_all('tr', class_='product-row') 

        if not product_rows:
            print(f"RS Components: 未找到 '{component_name}' 相關結果。")
            return []

        for row in product_rows[:3]: # 只抓取前 3 個結果以簡化輸出
            product_link_tag = row.find('a', class_='description-link')
            product_price_tag = row.find('span', class_='price')
            product_stock_tag = row.find('span', class_='stock-value')

            if product_link_tag and product_price_tag:
                title = product_link_tag.get_text(strip=True)
                # RS 的連結通常是相對路徑，需要補上域名
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

def scrape_wago(component_name):
    vendor_results = []
    # 範例 URL，請確認 WAGO 實際的搜尋 URL 格式
    search_url = f"https://www.wago.com/tw/search?query={component_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- WAGO 網頁結構分析範例 ---
        # 這是撰寫時的可能結構，未來可能變動
        product_cards = soup.find_all('div', class_='product-list__item') 
        
        if not product_cards:
            print(f"WAGO: 未找到 '{component_name}' 相關結果。")
            return []

        for card in product_cards[:3]: # 只取前 3 個結果
            title_tag = card.find('h3', class_='product-list__item-title')
            link_tag = card.find('a', class_='product-list__item-link')

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                link = "https://www.wago.com" + link_tag['href']
                
                vendor_results.append({
                    "vendor": "WAGO",
                    "name": title,
                    "link": link,
                    "price": "製造商網站通常不提供價格", # 製造商通常不直接販售
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

# --- 其他網站的爬蟲函數 (這是您需要自行依循範例完成的部分) ---
# 目前這些是佔位符，您可以根據需要來實現它們
def scrape_digikey(component_name):
    vendor_results = []
    # Digi-Key 的搜尋 URL 格式通常如下
    search_url = f"https://www.digikey.tw/zh/products/search?keywords={component_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
    }

    print(f"正在搜尋 Digi-Key for {component_name}...") # 增加日誌輸出

    try:
        response = requests.get(search_url, headers=headers, timeout=15) # 增加超時時間
        response.raise_for_status() # 如果狀態碼不是 200，拋出異常

        # 檢查是否被反爬蟲機制阻擋（例如重定向到驗證碼頁面）
        if "recaptcha" in response.url or "captcha" in response.text.lower():
            print(f"Digi-Key: 可能遇到反爬蟲機制，需要手動驗證。")
            vendor_results.append({
                "vendor": "Digi-Key",
                "error": "可能遇到反爬蟲機制，請嘗試手動訪問或稍後再試。"
            })
            return vendor_results

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- **重要：這部分需要根據您 F12 觀察到的實際 HTML 結構修改** ---
        # 尋找包含所有產品結果的容器。例如，它可能是個 div 且有一個特定的 class 或 id。
        # 範例：如果所有產品結果在一個 id 為 'resultsTable' 的 table 裡
        # 或者一個 class 為 'MuiGrid-container' 的 div 裡
        
        # 假設產品列表的每個產品在一個 class 為 'product-card' 的 div 裡 (僅為範例)
        # 您需要替換這裡的選擇器來匹配 Digi-Key 的實際 HTML 結構
        product_items = soup.find_all('div', class_='MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12 MuiGrid-grid-sm-6 MuiGrid-grid-md-4 MuiGrid-grid-lg-3') 
        
        if not product_items:
            print(f"Digi-Key: 未找到 '{component_name}' 相關產品項目，檢查選擇器或結果頁面。")
            vendor_results.append({
                "vendor": "Digi-Key",
                "error": "未找到產品結果，可能網頁結構有變或無相關產品。"
            })
            return vendor_results

        for item in product_items[:3]: # 只抓取前 3 個結果以簡化輸出
            # 產品名稱和連結：通常在一個 <a> 標籤裡
            # 範例：<a class="product-link" href="...">Product Name</a>
            title_tag = item.find('a', class_='MuiTypography-root MuiLink-root MuiLink-underlineNone MuiTypography-body1')
            
            # 產品價格：通常在一個 span 標籤裡，例如 <span class="price">NT$ 123.45</span>
            price_tag = item.find('span', class_='MuiTypography-root MuiTypography-body1 MuiTypography-noWrap') # 這是範例，請替換
            
            # 庫存：通常在另一個 span 或 div 裡
            stock_tag = item.find('p', class_='MuiTypography-root MuiTypography-body2 MuiTypography-colorTextSecondary') # 這是範例，請替換

            if title_tag and price_tag and stock_tag:
                title = title_tag.get_text(strip=True)
                # 確保連結是完整的，Digi-Key 的連結通常是相對路徑，需要加上域名
                link = "https://www.digikey.tw" + title_tag['href']
                price = price_tag.get_text(strip=True)
                stock = stock_tag.get_text(strip=True) # 可能需要進一步處理，例如只取數字

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

def scrape_mouser(component_name):
    vendor_results = []
    # Mouser 的搜尋 URL 格式通常如下
    search_url = f"https://www.mouser.tw/Search/Refine?Keyword={component_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
    }

    print(f"正在搜尋 Mouser for {component_name}...")

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Mouser 通常不會直接顯示驗證碼，但可能會有其他反爬蟲策略
        if "captcha" in response.text.lower() or "verify" in response.url.lower():
            print(f"Mouser: 可能遇到反爬蟲機制。")
            vendor_results.append({
                "vendor": "Mouser",
                "error": "可能遇到反爬蟲，請手動訪問或稍後再試。"
            })
            return vendor_results

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- **重要：這部分需要根據您 F12 觀察到的實際 HTML 結構修改** ---
        # Mouser 搜尋結果通常在一個表格中，每行代表一個產品。
        # 假設產品行是 <tr class="SearchResultsRow"> (這是一個範例，請替換)
        product_rows = soup.find_all('tr', class_='searchResultsRow') # 這是範例，請替換為實際的 class

        if not product_rows:
            print(f"Mouser: 未找到 '{component_name}' 相關結果，檢查選擇器或結果頁面。")
            vendor_results.append({
                "vendor": "Mouser",
                "error": "未找到產品結果，可能網頁結構有變或無相關產品。"
            })
            return vendor_results

        for row in product_rows[:3]: # 只抓取前 3 個結果
            # 產品名稱和連結：例如在一個 <a class="product-title-link" href="...">...</a>
            # 您需要找到包含名稱和連結的標籤
            title_link_tag = row.find('a', class_='MfrPartLink') # 這是範例，請替換為實際的 class

            # 價格：例如在一個 <span class="price-value">...</span>
            price_tag = row.find('td', class_='pricing').find('span', class_='pricing-value') # 這是範例，請替換

            # 庫存：例如在一個 <span class="avail-stock">...</span>
            stock_tag = row.find('div', class_='availableStock') # 這是範例，請替換

            if title_link_tag: # 至少有標題和連結才處理
                title = title_link_tag.get_text(strip=True)
                link = "https://www.mouser.tw" + title_link_tag['href'] # Mouser 連結通常是相對路徑

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

def scrape_octopart(component_name):
    vendor_results = []
    # Octopart 搜尋 URL 格式
    search_url = f"https://octopart.com/search?q={component_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
    }

    print(f"正在搜尋 Octopart for {component_name}...")

    try:
        response = requests.get(search_url, headers=headers, timeout=20) # 增加超時時間
        response.raise_for_status()

        # Octopart 的內容可能 heavily relies on JavaScript,
        # 所以直接用 BeautifulSoup 抓取原始 HTML 可能會得到空的結果。
        # 您可以在 Render 的 Logs 中檢查 response.text 的內容，看看是否有實際的產品 HTML。
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- **重要：以下選擇器是假設內容在原始 HTML 中可見** ---
        # 您需要仔細觀察 F12 中，產品卡片或列表的 HTML 結構
        # 例如：<div class="card product-card"> ... </div>
        product_cards = soup.find_all('div', class_='ProductSearch_ProductSummaryCard__vjM4O') # 這是撰寫時的範例，極可能變動

        if not product_cards:
            print(f"Octopart: 未找到 '{component_name}' 相關結果，可能網頁內容動態載入或結構變動。")
            vendor_results.append({
                "vendor": "Octopart",
                "error": "未找到產品結果，可能內容動態載入或結構有變，請考慮使用進階爬蟲或 API。"
            })
            return vendor_results

        for card in product_cards[:3]: # 只抓取前 3 個結果
            # 產品名稱和連結
            title_link_tag = card.find('a', class_='ProductSummaryCard_productLink__aD4sE') # 範例
            
            # 通常 Octopart 會列出多個供應商的價格和庫存，這會更複雜
            # 您可能需要遍歷供應商的列表，例如：
            # supplier_info_tags = card.find_all('div', class_='supplier-row')

            if title_link_tag:
                title = title_link_tag.get_text(strip=True)
                link = "https://octopart.com" + title_link_tag['href'] # Octopart 連結通常是相對路徑

                # 為了簡化，這裡暫時不實作多個供應商的價格/庫存，
                # 您可以找到一個代表性的價格/庫存顯示位置
                # 例如：
                price_tag = card.find('span', class_='ProductSummaryCard_price__some_hash') # 這是範例，請替換
                stock_tag = card.find('span', class_='ProductSummaryCard_stock__some_hash') # 這是範例，請替換
                
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