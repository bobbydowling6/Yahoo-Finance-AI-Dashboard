from fastapi import HTTPException
import yfinance as yf

def get_stock_data(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    if not info or ("regularMarketPrice" not in info and "currentPrice" not in info):
            raise HTTPException(
                status_code=404, 
                detail=f"Ticker '{ticker}' not found or Yahoo Finance data unavailable."
            )

    return {
            "ticker": ticker.upper(),
            "company_name": info.get("longName") or info.get("shortName") or ticker.upper(),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
            "currency": info.get("currency") or "USD",
            "previous_close": info.get("previousClose") or info.get("regularMarketPreviousClose"),
            "market_cap": info.get("marketCap"),
            "year_to_date_high": info.get("fiftyTwoWeekHigh"),
            "year_to_date_low": info.get("fiftyTwoWeekLow"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "summary": info.get("longBusinessSummary") or info.get("description") or "No summary available."
        }
