-- ============================================================
-- multitenant_07_calendar.sql  (v2 — รองรับเวลา + ตั้งเตือนล่วงหน้า)
-- 目的：顧問自訂行事曆事件 + LINE 提醒 (可設時間 + 提前提醒)。
-- 執行方式：Supabase → SQL Editor → 貼上 → Run。รันซ้ำได้ปลอดภัย (idempotent)。
-- ============================================================

create table if not exists calendar_events (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null default '3da82a79-8ef5-4f8c-9df3-faed33e75b64',
    title           text not null,
    event_date      date not null,
    event_time      time,                     -- null = 整天 (all-day)
    notes           text,
    remind_offsets  text default '0',         -- 逗號分隔「事件前幾分鐘提醒」(เช่น '1440,30'); '' = 不提醒
    remind_1day     boolean default true,     -- (legacy 保留)
    remind_sameday  boolean default true,     -- (legacy 保留)
    done            boolean default false,
    created_at      timestamptz default now()
);

-- เพิ่มคอลัมน์ใหม่ถ้าตารางมีอยู่แล้ว (รันซ้ำได้)
alter table calendar_events add column if not exists event_time     time;
alter table calendar_events add column if not exists remind_offsets text default '0';

create index if not exists idx_calendar_events_date   on calendar_events(event_date);
create index if not exists idx_calendar_events_tenant on calendar_events(tenant_id);

select 'calendar_events ready' as label, count(*) from calendar_events;
