# api/analyze.py

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json # 導入 json 庫用於構建 JSON 響應

# 核心分析函數 (與之前基本相同，但不再打印輸出，而是返回結果)
def analyze_stock_technical(ticker):
    """
    基於技術指標分析股票，返回分析結果的字典。
    """
    try:
        # --- 數據獲取 ---
        # 獲取足夠的歷史數據
        print(f"Fetching data for {ticker}...") # 在服務器日誌中可見
        data = yf.download(ticker, period="1y", interval="1d")

        if data.empty:
            return {"error": f"無法獲取 {ticker} 的股票數據，請檢查股票代號或網絡連接。"}

        # --- 技術指標計算 ---
        print("Calculating indicators...")
        data.ta.sma(length=20, append=True)
        data.ta.sma(length=50, append=True)
        data.ta.rsi(length=14, append=True)
        data.dropna(inplace=True)

        if data.empty:
             return {"error": f"數據不足以計算 {ticker} 的技術指標 (至少需要50天歷史數據)。"}

        # --- 獲取最新指標值 ---
        latest_data = data.iloc[-1]

        if pd.isna(latest_data['SMA_20']) or pd.isna(latest_data['SMA_50']) or pd.isna(latest_data['RSI_14']):
             return {"error": f"無法從獲取的數據中計算 {ticker} 的有效技術指標值。"}

        sma_20 = latest_data['SMA_20']
        sma_50 = latest_data['SMA_50']
        rsi = latest_data['RSI_14']
        latest_price = latest_data['Close']

        # --- 生成買賣建議 ---
        recommendation = "建議持有/觀察" # 默認建議
        details = "根據 SMA 和 RSI 指標綜合判斷" # 增加詳細信息字段

        if sma_20 > sma_50:
            if rsi < 70:
                recommendation = "建議買入"
                details = "20日SMA > 50日SMA (趨勢向上) 且 RSI < 70 (未超買)"
            else:
                recommendation = "建議持有/觀察"
                details = "20日SMA > 50日SMA (趨勢向上) 但 RSI >= 70 (可能超買)"
        elif sma_20 < sma_50:
            if rsi > 30:
                recommendation = "建議賣出"
                details = "20日SMA < 50日SMA (趨勢向下) 且 RSI > 30 (未超賣)"
            else:
                recommendation = "建議持有/觀察"
                details = "20日SMA < 50日SMA (趨勢向下) 但 RSI <= 30 (可能超賣)"
        else:
             recommendation = "建議持有/觀察"
             details = "20日SMA ~ 50日SMA (移動平均線纏繞或橫行)"

        # 返回包含結果的字典
        return {
            "ticker": ticker,
            "latest_price": round(latest_price, 2),
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "rsi_14": round(rsi, 2),
            "recommendation": recommendation,
            "details": details,
            "error": None # 沒有錯誤時 error 為 None
        }

    except Exception as e:
        # 捕獲其他潛在錯誤
        print(f"Error analyzing {ticker}: {e}") # 在服務器日誌中可見
        return {"error": f"分析 {ticker} 時發生錯誤: {str(e)}"}

# --- 無伺服器函數的入口點 ---
# Vercel 的 Python 無伺服器函數需要一個 handler 函數，
# 它接收一個 request 對象，並返回一個 response。
# 使用 Vercel 的 @vercel/python 構建包時，通常這樣定義：
# from http.server import BaseHTTPRequestHandler # 其實 Vercel 會有自己的 wrapper

# 這裡我們模擬一個簡單的處理，Vercel 會將 HTTP 請求的細節
# 轉換成方便 Python 處理的格式。最簡單的方式是從 query string 獲取參數。

def handler(request):
    """
    Vercel Serverless Function 入口點。
    從 HTTP 請求的 query string 中獲取 'ticker' 參數。
    """
    # 獲取 HTTP 請求中的 query parameters
    # request.query 是一個字典，包含 URL 中的所有參數
    # 例如 /api/analyze?ticker=AAPL -> request.query = {'ticker': ['AAPL']}
    # 需要處理參數不存在或格式錯誤的情況

    try:
        query_params = request.query # Vercel 提供的 request object

        # 從 query parameters 中獲取 ticker
        # 注意： query_params 中的值通常是列表，因為同名參數可以有多個
        ticker = query_params.get('ticker', [None])[0] # 取第一個 ticker 參數的值

        if not ticker:
            # 如果沒有提供 ticker 參數
            response_data = {"error": "請在 URL 中提供 'ticker' 參數。例如: /api/analyze?ticker=AAPL"}
            status_code = 400 # Bad Request
        else:
            # 調用核心分析函數
            analysis_result = analyze_stock_technical(ticker.strip().upper())
            response_data = analysis_result

            # 根據結果設置 HTTP 狀態碼
            if response_data.get("error"):
                status_code = 500 # Internal Server Error 或其他合適的錯誤碼
            else:
                status_code = 200 # OK

    except Exception as e:
        # 捕獲處理請求時發生的其他錯誤
        print(f"Error processing request: {e}")
        response_data = {"error": f"處理請求時發生內部錯誤: {str(e)}"}
        status_code = 500

    # 構建 HTTP 響應
    # Vercel 的 Python 無伺服器函數通常返回一個包含 body, statusCode, headers 的字典
    # 或者更簡單的，直接返回一個 JSON-serializable 的對象，Vercel 會自動處理

    # 返回一個字典，Vercel 會自動將其轉換為 JSON 響應
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*' # 允許跨域訪問，方便從任何地方調用
        },
        'body': json.dumps(response_data, ensure_ascii=False) # 將字典轉換為 JSON 字符串
    }