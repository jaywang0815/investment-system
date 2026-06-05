-- ============================================================
-- 投資管理系統 - Supabase 資料庫結構
-- 請在 Supabase Dashboard > SQL Editor 執行此 SQL
-- ============================================================

-- 客戶資料表
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    unified_account BOOLEAN DEFAULT FALSE,     -- 統一開戶
    pi_signed BOOLEAN DEFAULT FALSE,           -- PI見簽
    ordered BOOLEAN DEFAULT FALSE,             -- 已下單
    usd_amount NUMERIC(15,2),                  -- USD 金額
    ctbc_position NUMERIC(15,2),               -- 中信部位
    fund_amount NUMERIC(15,2),                 -- FUND
    notes TEXT,                                -- 備註
    portal_token TEXT UNIQUE DEFAULT gen_random_uuid()::TEXT,  -- 客戶入口網址token
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 結構型商品資料表
CREATE TABLE IF NOT EXISTS structured_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code TEXT NOT NULL,                -- 代號 e.g. EQDS05027345
    trade_date DATE,                           -- 日期
    underlying_1 TEXT,                         -- 標的1
    underlying_2 TEXT,                         -- 標的2
    underlying_3 TEXT,                         -- 標的3
    underlying_4 TEXT,                         -- 標的4
    underlying_5 TEXT,                         -- 標的5
    initial_price_1 NUMERIC(15,4),             -- 期初價格1
    initial_price_2 NUMERIC(15,4),             -- 期初價格2
    initial_price_3 NUMERIC(15,4),             -- 期初價格3
    initial_price_4 NUMERIC(15,4),             -- 期初價格4
    initial_price_5 NUMERIC(15,4),             -- 期初價格5
    strike_pct NUMERIC(8,6),                   -- 執行價 (小數, 0.80 = 80%)
    coupon_pct NUMERIC(8,6),                   -- 配息率 (小數, 0.15 = 15%)
    observation_date DATE,                     -- 比價日
    ko_barrier NUMERIC(8,6),                   -- KO提前 (小數, 1.0 = 100%)
    ki_barrier NUMERIC(8,6),                   -- KI下限 (小數, 0.5 = 50%)
    exit_date DATE,                            -- 出場日
    temp_settlement NUMERIC(15,2),             -- 暫結
    chu TEXT,                                  -- CHU
    month_label TEXT DEFAULT '5月',            -- 所屬月份
    status TEXT DEFAULT 'active',              -- active/ko_triggered/ki_triggered/expired/matured
    total_order_amount NUMERIC(15,2),          -- 總下單金額
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 投資記錄資料表 (客戶 <-> 商品 關聯)
CREATE TABLE IF NOT EXISTS investments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    sn_id UUID NOT NULL REFERENCES structured_notes(id) ON DELETE CASCADE,
    amount_usd NUMERIC(15,2) NOT NULL,         -- 下單金額
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_id, sn_id)
);

-- 每日股價快照
CREATE TABLE IF NOT EXISTS daily_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    price_date DATE NOT NULL,
    close_price NUMERIC(15,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, price_date)
);

-- 警示記錄
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sn_id UUID REFERENCES structured_notes(id) ON DELETE CASCADE,
    alert_type TEXT,                           -- ko_risk/ki_risk/observation_due/ko_triggered/ki_triggered
    message TEXT,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    sent_to_line BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE
);

-- 自動更新 updated_at 欄位
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER structured_notes_updated_at
    BEFORE UPDATE ON structured_notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER investments_updated_at
    BEFORE UPDATE ON investments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 加速查詢的索引
CREATE INDEX IF NOT EXISTS idx_investments_customer ON investments(customer_id);
CREATE INDEX IF NOT EXISTS idx_investments_sn ON investments(sn_id);
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date ON daily_prices(ticker, price_date);
CREATE INDEX IF NOT EXISTS idx_sn_status ON structured_notes(status);
CREATE INDEX IF NOT EXISTS idx_sn_observation_date ON structured_notes(observation_date);

-- 完成！
SELECT 'Database schema created successfully' AS result;
