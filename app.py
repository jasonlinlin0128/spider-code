# app.py

import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# --- 引入網路爬蟲相關函式庫，但現在先不用，會慢慢加入 ---
# import requests
# from bs4 import BeautifulSoup
# ----------------------------------------

app = Flask(__name__)

# 從環境變數中讀取你的 Channel Access Token 和 Channel Secret
# 這是為了安全考量，避免將敏感資訊直接寫在程式碼中
# 在部署到雲端前，您在本機測試時需要手動設定這些環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# 檢查環境變數是否設定
if LINE_CHANNEL_ACCESS_TOKEN is None:
    print('錯誤：請設定環境變數 LINE_CHANNEL_ACCESS_TOKEN。')
    exit(1) # 如果沒有設定，程式會退出
if LINE_CHANNEL_SECRET is None:
    print('錯誤：請設定環境變數 LINE_CHANNEL_SECRET。')
    exit(1) # 如果沒有設定，程式會退出

# 初始化 LINE Bot API 和 Webhook Handler
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- Webhook 接收點 ---
# LINE 平台會將所有訊息發送到這個 URL 路徑 (例如：https://您的網址/webhook)
@app.route("/webhook", methods=['POST'])
def webhook():
    # 取得請求頭中的 LINE 簽名 (用於驗證請求來源)
    signature = request.headers['X-Line-Signature']
    # 取得請求體，也就是 LINE 傳送過來的 JSON 資料
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body) # 在日誌中記錄接收到的請求體

    try:
        # 處理 Webhook 事件，會自動呼叫對應的事件處理器 (例如 handle_message)
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 如果簽名無效，表示請求不是來自 LINE 平台或 Channel Access Token/Secret 不正確
        print("簽名無效。請檢查您的 Channel Access Token 或 Channel Secret 設定。")
        abort(400) # 返回 HTTP 400 錯誤給 LINE 平台

    return 'OK' # 成功接收並處理，返回 OK 給 LINE 平台

# --- 訊息處理器 ---
# 當 LINE 傳送過來的是文字訊息事件時，會執行這個函式
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 取得使用者傳送的文字訊息內容
    user_message = event.message.text
    # 取得回覆用的 token，這個 token 只能使用一次且有時間限制
    reply_token = event.reply_token

    print(f"使用者傳送了: {user_message}") # 在您的電腦控制台印出使用者訊息

    # --- 這裡目前只是簡單的回應，未來會加入料件查詢邏輯 ---
    reply_text = f"您說了: {user_message}" # 簡單地回覆使用者說的話

    # 使用 LINE Bot API 發送回覆訊息
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=reply_text) # 傳送一個文字訊息給使用者
    )

# --- 啟動 Flask 應用程式 ---
# 這是讓您的 Flask 程式運行起來的部分
if __name__ == "__main__":
    # 在本地開發時，通常會用 5000 端口
    # 當部署到雲端時，雲端服務會自動提供 PORT 環境變數
    port = int(os.environ.get("PORT", 5000))
    # 讓 Flask 應用程式在所有可用的網絡接口上監聽 (0.0.0.0)，這樣外部才能訪問 (在部署時)
    # debug=True 僅限於開發階段，在生產環境中應該設置為 False 或移除
    app.run(host="0.0.0.0", port=port, debug=False)