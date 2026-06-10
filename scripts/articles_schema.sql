-- 文章 (投資觀點) 資料表 — 貼到 Supabase SQL Editor 執行一次即可
create table if not exists articles (
  id          uuid primary key default gen_random_uuid(),
  slug        text unique not null,
  title_zh    text not null,
  title_en    text,
  excerpt_zh  text,
  excerpt_en  text,
  body_zh     text,
  body_en     text,
  cover_url   text,
  published   boolean default false,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

create index if not exists articles_published_idx on articles (published, created_at desc);

-- RLS：公開只能讀「已發布」；寫入由後台用 service key (繞過 RLS)
alter table articles enable row level security;

drop policy if exists "public read published articles" on articles;
create policy "public read published articles"
  on articles for select
  using (published = true);
