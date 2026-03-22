def calculate_intraday_costs(buy_price: float, sell_price: float, qty: int) -> dict:
    buy_turnover = buy_price * qty
    sell_turnover = sell_price * qty
    total_turnover = buy_turnover + sell_turnover
    
    # 1. Brokerage: Flat ₹20 per executed order -> ₹40 for round trip, or 0.03% whichever is lower
    brokerage_buy = min(20.0, buy_turnover * 0.0003)
    brokerage_sell = min(20.0, sell_turnover * 0.0003)
    brokerage = brokerage_buy + brokerage_sell
    
    # 2. STT: 0.025% on Sell side only
    stt = round(sell_turnover * 0.00025)
    
    # 3. Exchange Transaction Charges: ~0.00325% on turnover
    exc_charges = total_turnover * 0.0000325
    
    # 4. SEBI Charges: ₹10 per crore
    sebi_charges = total_turnover * (10 / 10000000)
    
    # 5. Stamp Duty: 0.003% on Buy side only
    stamp_duty = round(buy_turnover * 0.00003)
    
    # 6. GST: 18% on (Brokerage + SEBI + Exchange charges)
    gst = (brokerage + sebi_charges + exc_charges) * 0.18
    
    total_charges = brokerage + stt + exc_charges + sebi_charges + stamp_duty + gst
    gross_pnl = (sell_price - buy_price) * qty
    net_pnl = gross_pnl - total_charges
    
    return {
        'gross_pnl': gross_pnl,
        'net_pnl': net_pnl,
        'brokerage': brokerage,
        'stt': stt,
        'exc_charges': exc_charges,
        'sebi_charges': sebi_charges,
        'stamp_duty': stamp_duty,
        'gst': gst,
        'total_charges': total_charges
    }
