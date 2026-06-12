-- ============================================================
-- multitenant_07_calendar.sql
-- 目的：顧問自訂行事曆事件 + LINE 提醒 (前一天 / 當天)。
-- 執行方式：Supabase → SQL Editor → 貼上 → Run (一次即可)。
-- 安全性：只新增資料表，不動既有資料。
-- ============================================================

create table if not exists calendar_events (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null default '3da82a79-8ef5-4f8c-9df3-faed33e75b64',
    title           text not null,            -- 事件標題
    event_date      date not null,            -- 事件日期
    notes           text,                     -- 備註
    remind_1day     boolean default true,     -- 前一天提醒 LINE
    remind_sameday  boolean default true,     -- 當天提醒 LINE
    done            boolean default false,    -- 已完成
    created_at      timestamptz default now()
);

create index if not exists idx_calendar_events_date   on calendar_events(event_date);
create index if not exists idx_calendar_events_tenant on calendar_events(tenant_id);

-- 驗證
select 'calendar_events created' as label, count(*) from calendar_events;
