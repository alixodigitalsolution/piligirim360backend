-- Combined Supabase Schema and Sample Data for Pilgrim360
-- Generated on 2026-05-18

-- ==== Extension ==== 
create extension if not exists pgcrypto;

-- ==== Full Schema (from supabase_full_schema.sql) ==== 
-- (Tables, indexes, policies, RLS, etc.)
create table if not exists agencies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  city text,
  status text not null default 'active',
  member_count int not null default 0,
  online_count int not null default 0,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists users_table (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  full_name text,
  role text not null check (role in ('super_admin','admin','leader','pilgrim')),
  agency_id uuid references agencies(id) on delete set null,
  leader_id uuid references users_table(id) on delete set null,
  phone text,
  journey_type text check (journey_type in ('hajj','umrah')),
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists pilgrim_locations (
  id uuid primary key default gen_random_uuid(),
  pilgrim_id uuid references users_table(id) on delete cascade,
  group_id uuid references agencies(id) on delete cascade,
  latitude double precision not null,
  longitude double precision not null,
  battery_level int,
  is_online boolean default true,
  recorded_at timestamptz not null default timezone('utc', now())
);

-- Insert test agency data
INSERT INTO agencies (id, name, city, status, member_count, online_count)
VALUES 
('550e8400-e29b-41d4-a716-446655440001', 'Elite Hajj Tours', 'Karachi', 'active', 12, 10)
ON CONFLICT (id) DO NOTHING;

create table if not exists group_messages (
  id uuid primary key default gen_random_uuid(),
  group_id uuid references agencies(id) on delete cascade,
  leader_id uuid references users_table(id) on delete set null,
  message_type text default 'text',
  message_text text,
  pin_latitude double precision,
  pin_longitude double precision,
  pin_label text,
  sent_at timestamptz not null default timezone('utc', now())
);

create table if not exists sos_alerts (
  id uuid primary key default gen_random_uuid(),
  pilgrim_id uuid references users_table(id) on delete cascade,
  group_id uuid references agencies(id) on delete cascade,
  latitude double precision,
  longitude double precision,
  status text default 'active',
  created_at timestamptz not null default timezone('utc', now()),
  resolved_at timestamptz
);

create table if not exists medical_cards (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique references users_table(id) on delete cascade,
  blood_type text,
  allergies text,
  medications text,
  medical_history text,
  emergency_contact_name text,
  emergency_contact_phone text,
  passport_number text,
  visa_number text,
  visa_qr_data text,
  photo_url text,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists tracking_sessions (
  id uuid primary key default gen_random_uuid(),
  pilgrim_id uuid references users_table(id) on delete cascade,
  group_id uuid references agencies(id) on delete set null,
  tracking_type text not null,
  rounds_completed int default 0,
  steps_count int default 0,
  distance_meters double precision default 0,
  started_at timestamptz not null default timezone('utc', now()),
  ended_at timestamptz,
  status text default 'active'
);

create table if not exists tracking_points (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references tracking_sessions(id) on delete cascade,
  pilgrim_id uuid references users_table(id) on delete cascade,
  latitude double precision,
  longitude double precision,
  steps_count int default 0,
  distance_meters double precision default 0,
  round_number int default 0,
  recorded_at timestamptz not null default timezone('utc', now())
);

create table if not exists sync_queue (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users_table(id) on delete cascade,
  action_type text not null,
  payload jsonb not null,
  synced boolean default true,
  created_at timestamptz not null default timezone('utc', now()),
  synced_at timestamptz default timezone('utc', now())
);

create table if not exists danger_zones (
  id uuid primary key default gen_random_uuid(),
  agency_id uuid references agencies(id) on delete cascade,
  leader_id uuid references users_table(id) on delete set null,
  latitude double precision not null,
  longitude double precision not null,
  radius_meters int default 50,
  label text,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists meeting_points (
  id uuid primary key default gen_random_uuid(),
  group_id uuid references agencies(id) on delete cascade,
  latitude double precision not null,
  longitude double precision not null,
  label text not null,
  description text,
  set_by uuid references users_table(id) on delete set null,
  is_active boolean default true,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists jamarat_slots (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users_table(id) on delete cascade,
  group_id uuid references agencies(id) on delete cascade,
  date date not null,
  time_from text not null,
  time_to text not null,
  slot_label text,
  notes text,
  assigned_by uuid references users_table(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists hotel_info (
  id uuid primary key default gen_random_uuid(),
  org_id uuid unique references agencies(id) on delete cascade,
  hotel_name text not null,
  address text,
  latitude double precision,
  longitude double precision,
  room_info text,
  check_in_date date,
  check_out_date date,
  hotel_phone text,
  driver_name text,
  driver_phone text,
  bus_number text,
  bus_schedule jsonb default '[]'::jsonb,
  madinah_hotel_name text,
  madinah_hotel_address text,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists medicines (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users_table(id) on delete cascade,
  medicine_name text not null,
  dose text,
  frequency text,
  times text[] default '{}',
  notes text,
  start_date date,
  end_date date,
  is_active boolean default true,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists diary_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users_table(id) on delete cascade,
  text text not null,
  photo_url text,
  latitude double precision,
  longitude double precision,
  location_label text,
  mood text,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists family_links (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users_table(id) on delete cascade,
  token uuid not null unique,
  expires_at timestamptz not null,
  is_active boolean default true,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists notifications_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users_table(id) on delete cascade,
  type text default 'INFO',
  message text not null,
  delivered boolean default false,
  read_at timestamptz,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists checkins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users_table(id) on delete cascade,
  status text not null check (status in ('ok','not_ok')),
  latitude double precision,
  longitude double precision,
  note text,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists map_points (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  city text not null check (city in ('makkah','madinah')),
  point_type text not null,
  latitude double precision not null,
  longitude double precision not null,
  description text,
  sort_order int default 0,
  is_active boolean default true,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists dua_categories (
  id uuid primary key default gen_random_uuid(),
  journey_type text not null check (journey_type in ('hajj','umrah','both')),
  title text not null,
  sort_order int default 0,
  is_active boolean default true
);

create table if not exists duas (
  id uuid primary key default gen_random_uuid(),
  category_id uuid references dua_categories(id) on delete cascade,
  title text not null,
  arabic text not null,
  transliteration text,
  urdu text,
  english text,
  audio_url text,
  sort_order int default 0,
  is_active boolean default true
);

create table if not exists tasbeehat (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  arabic text not null,
  transliteration text,
  urdu text,
  english text,
  default_target int default 33,
  sort_order int default 0,
  is_active boolean default true
);

create table if not exists app_settings (
  setting_key text primary key,
  setting_value jsonb not null,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists system_logs (
  id uuid primary key default gen_random_uuid(),
  level text default 'info',
  action text not null,
  details jsonb,
  user_id uuid references users_table(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now())
);

-- ==== Indexes ==== 
create index if not exists idx_locations_group_recorded on pilgrim_locations(group_id, recorded_at desc);
create index if not exists idx_locations_pilgrim_recorded on pilgrim_locations(pilgrim_id, recorded_at desc);
create index if not exists idx_messages_group_sent on group_messages(group_id, sent_at desc);
create index if not exists idx_sos_status_created on sos_alerts(status, created_at desc);
create index if not exists idx_users_role_agency on users_table(role, agency_id);
create index if not exists idx_map_points_city_active on map_points(city, is_active, sort_order);
create index if not exists idx_dua_categories_journey on dua_categories(journey_type, sort_order);
create index if not exists idx_duas_category_order on duas(category_id, sort_order);
create index if not exists idx_meeting_points_group on meeting_points(group_id);
create index if not exists idx_jamarat_slots_user on jamarat_slots(user_id, date);
create index if not exists idx_jamarat_slots_group on jamarat_slots(group_id);
create index if not exists idx_hotel_info_org on hotel_info(org_id);
create index if not exists idx_medicines_user on medicines(user_id);
create index if not exists idx_diary_entries_user on diary_entries(user_id, created_at desc);
create index if not exists idx_family_links_token on family_links(token);
create index if not exists idx_family_links_user on family_links(user_id);
create index if not exists idx_notifications_user on notifications_log(user_id, created_at desc);
create index if not exists idx_checkins_user on checkins(user_id, created_at desc);
create index if not exists idx_tracking_sessions_pilgrim on tracking_sessions(pilgrim_id, started_at desc);
create index if not exists idx_tracking_points_session on tracking_points(session_id, recorded_at asc);
create index if not exists idx_sync_queue_user on sync_queue(user_id, created_at DESC);

-- ==== Row Level Security ==== 
alter table agencies enable row level security;
alter table users_table enable row level security;
alter table pilgrim_locations enable row level security;
alter table group_messages enable row level security;
alter table sos_alerts enable row level security;
alter table medical_cards enable row level security;
alter table tracking_sessions enable row level security;
alter table tracking_points enable row level security;
alter table sync_queue enable row level security;
alter table danger_zones enable row level security;
alter table meeting_points enable row level security;
alter table jamarat_slots enable row level security;
alter table hotel_info enable row level security;
alter table medicines enable row level security;
alter table diary_entries enable row level security;
alter table family_links enable row level security;
alter table notifications_log enable row level security;
alter table checkins enable row level security;
alter table map_points enable row level security;
alter table dua_categories enable row level security;
alter table duas enable row level security;
alter table tasbeehat enable row level security;
alter table app_settings enable row level security;
alter table system_logs enable row level security;

-- ==== Policies (Open for all operations; actual auth handled by backend) ==== 
do $$
declare tbl text;
begin
  foreach tbl in array array[
    'agencies','users_table','pilgrim_locations','group_messages','sos_alerts','medical_cards',
    'tracking_sessions','tracking_points','sync_queue','danger_zones','meeting_points',
    'jamarat_slots','hotel_info','medicines','diary_entries','family_links','notifications_log',
    'checkins','map_points','dua_categories','duas','tasbeehat','app_settings','system_logs'
  ] loop
    execute format('drop policy if exists "%s_service_all" on %I', tbl, tbl);
    execute format('create policy "%s_service_all" on %I for all using (true) with check (true)', tbl, tbl);
  end loop;
end $$;

-- ==== Sample Data ==== 
-- Agencies and Users
INSERT INTO agencies (id, name, city, status, member_count, online_count) VALUES
  ('11111111-1111-1111-1111-111111111111', 'Al Noor Hajj Services', 'Karachi', 'active', 0, 0),
  ('22222222-2222-2222-2222-222222222222', 'Madinah Travel Group', 'Lahore', 'active', 0, 0)
  ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, city = EXCLUDED.city, status = EXCLUDED.status;

INSERT INTO users_table (id, email, password_hash, full_name, role, agency_id, phone) VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'admin@pilgrim360.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'System Admin', 'super_admin', NULL, '+920000000000'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'leader1@pilgrim360.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Ahmed Leader', 'leader', '11111111-1111-1111-1111-111111111111', '+923001111111'),
  ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'leader2@pilgrim360.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Fatima Leader', 'leader', '22222222-2222-2222-2222-222222222222', '+923002222222'),
  ('dddddddd-dddd-dddd-dddd-dddddddddd01', 'pilgrim1@pilgrim360.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Ali Hassan', 'pilgrim', '11111111-1111-1111-1111-111111111111', '+923101111111'),
  ('dddddddd-dddd-dddd-dddd-dddddddddd02', 'pilgrim2@pilgrim360.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Sara Khan', 'pilgrim', '11111111-1111-1111-1111-111111111111', '+923101111112'),
  ('dddddddd-dddd-dddd-dddd-dddddddddd03', 'pilgrim3@pilgrim360.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Omar Farooq', 'pilgrim', '11111111-1111-1111-1111-111111111111', '+923101111113'),
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01', 'pilgrim4@pilgrim360.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Zainab Ali', 'pilgrim', '22222222-2222-2222-2222-222222222222', '+923102222221')
  ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, password_hash = EXCLUDED.password_hash, full_name = EXCLUDED.full_name, role = EXCLUDED.role, agency_id = EXCLUDED.agency_id, phone = EXCLUDED.phone;

INSERT INTO pilgrim_locations (pilgrim_id, group_id, latitude, longitude, battery_level, is_online, recorded_at) VALUES
  ('dddddddd-dddd-dddd-dddd-dddddddddd01', '11111111-1111-1111-1111-111111111111', 21.42250, 39.82620, 86, true, timezone('utc'::text, now()) - interval '3 minutes'),
  ('dddddddd-dddd-dddd-dddd-dddddddddd02', '11111111-1111-1111-1111-111111111111', 21.41880, 39.83100, 62, true, timezone('utc'::text, now()) - interval '7 minutes'),
  ('dddddddd-dddd-dddd-dddd-dddddddddd03', '11111111-1111-1111-1111-111111111111', 21.41080, 39.84210, 28, false, timezone('utc'::text, now()) - interval '28 minutes'),
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01', '22222222-2222-2222-2222-222222222222', 21.39010, 39.85790, 74, true, timezone('utc'::text, now()) - interval '5 minutes'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '11111111-1111-1111-1111-111111111111', 21.41620, 39.83600, 92, true, timezone('utc'::text, now())),
  ('cccccccc-cccc-cccc-cccc-cccccccccccc', '22222222-2222-2222-2222-222222222222', 21.39500, 39.85200, 85, true, timezone('utc'::text, now()));

INSERT INTO danger_zones (agency_id, leader_id, latitude, longitude, radius_meters, label) VALUES
  ('11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 21.42250, 39.82620, 250, 'High Crowd Area'),
  ('11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 21.41400, 39.83550, 180, 'Restricted Walkway')
  ON CONFLICT DO NOTHING;

INSERT INTO group_messages (group_id, leader_id, message_type, message_text, sent_at) VALUES
  ('11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'text', 'Please stay close to your group leader.', timezone('utc'::text, now()) - interval '10 minutes'),
  ('11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'text', 'Next check-in is near Gate 79.', timezone('utc'::text, now()) - interval '5 minutes');

INSERT INTO sos_alerts (id, pilgrim_id, group_id, latitude, longitude, status, created_at, resolved_at) VALUES
  ('99999999-9999-9999-9999-999999999901', 'dddddddd-dddd-dddd-dddd-dddddddddd02', '11111111-1111-1111-1111-111111111111', 21.41880, 39.83100, 'active', timezone('utc'::text, now()) - interval '6 minutes', NULL),
  ('99999999-9999-9999-9999-999999999902', 'dddddddd-dddd-dddd-dddd-dddddddddd03', '11111111-1111-1111-1111-111111111111', 21.41080, 39.84210, 'resolved', timezone('utc'::text, now()) - interval '2 hours', timezone('utc'::text, now()) - interval '90 minutes'),
  ('99999999-9999-9999-9999-999999999903', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01', '22222222-2222-2222-2222-222222222222', 21.39010, 39.85790, 'active', timezone('utc'::text, now()) - interval '14 minutes', NULL)
  ON CONFLICT (id) DO UPDATE SET pilgrim_id = EXCLUDED.pilgrim_id, group_id = EXCLUDED.group_id, latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude, status = EXCLUDED.status, created_at = EXCLUDED.created_at, resolved_at = EXCLUDED.resolved_at;

INSERT INTO medical_cards (user_id, blood_type, allergies, medications, medical_history, emergency_contact_name, emergency_contact_phone, passport_number, visa_number, visa_qr_data) VALUES
  ('dddddddd-dddd-dddd-dddd-dddddddddd01', 'O+', 'Penicillin allergy', 'Blood pressure medicine', 'Hypertension', 'Hassan Ahmed', '+923331111111', 'PK1234561', 'VISA-1111', 'P360-VISA-QR-ALI'),
  ('dddddddd-dddd-dddd-dddd-dddddddddd02', 'A-', 'No known allergies', 'Insulin', 'Type 2 diabetes', 'Khan Family', '+923331111112', 'PK1234562', 'VISA-1112', 'P360-VISA-QR-SARA'),
  ('dddddddd-dddd-dddd-dddd-dddddddddd03', 'B+', 'Dust allergy', 'Inhaler', 'Asthma', 'Farooq Ahmed', '+923331111113', 'PK1234563', 'VISA-1113', 'P360-VISA-QR-OMAR')
  ON CONFLICT (user_id) DO UPDATE SET blood_type = EXCLUDED.blood_type, allergies = EXCLUDED.allergies, medications = EXCLUDED.medications, medical_history = EXCLUDED.medical_history, emergency_contact_name = EXCLUDED.emergency_contact_name, emergency_contact_phone = EXCLUDED.emergency_contact_phone, passport_number = EXCLUDED.passport_number, visa_number = EXCLUDED.visa_number, visa_qr_data = EXCLUDED.visa_qr_data, updated_at = timezone('utc'::text, now());

INSERT INTO tracking_sessions (id, pilgrim_id, group_id, tracking_type, rounds_completed, steps_count, distance_meters, status, started_at, ended_at) VALUES
  ('77777777-7777-7777-7777-777777777701', 'dddddddd-dddd-dddd-dddd-dddddddddd01', '11111111-1111-1111-1111-111111111111', 'tawaf', 4, 2480, 1600, 'active', timezone('utc'::text, now()) - interval '40 minutes', NULL),
  ('77777777-7777-7777-7777-777777777702', 'dddddddd-dddd-dddd-dddd-dddddddddd02', '11111111-1111-1111-1111-111111111111', 'sai', 7, 5320, 3150, 'completed', timezone('utc'::text, now()) - interval '3 hours', timezone('utc'::text, now()) - interval '2 hours')
  ON CONFLICT (id) DO UPDATE SET rounds_completed = EXCLUDED.rounds_completed, steps_count = EXCLUDED.steps_count, distance_meters = EXCLUDED.distance_meters, status = EXCLUDED.status, started_at = EXCLUDED.started_at, ended_at = EXCLUDED.ended_at;

INSERT INTO system_logs (level, action, details, user_id) VALUES
  ('info', 'Sample data loaded', '{"source":"backend/sample_data.sql"}', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');

-- App Settings
INSERT INTO app_settings (setting_key, setting_value, updated_at) VALUES
('app_version', '{"version": "1.0.0", "force_update": false}'::jsonb, timezone('utc'::text, now())),
('hajj_year', '{"hijri": "1447", "gregorian": "2026"}'::jsonb, timezone('utc'::text, now()))
ON CONFLICT (setting_key) DO NOTHING;

-- Map Points (Important places in Makkah and Madinah)
INSERT INTO map_points (name, city, point_type, latitude, longitude, description, sort_order) VALUES
('Masjid al-Haram', 'makkah', 'mosque', 21.4225, 39.8262, 'The Great Mosque of Makkah', 1),
('Mount Arafat', 'makkah', 'ritual_site', 21.3549, 39.9841, 'The Mount of Mercy', 2),
('Mina Tents', 'makkah', 'ritual_site', 21.4145, 39.8920, 'City of Tents', 3),
('Jamarat', 'makkah', 'ritual_site', 21.4226, 39.8732, 'The Stoning of the Devil', 4),
('Al-Masjid an-Nabawi', 'madinah', 'mosque', 24.4672, 39.6111, 'The Prophet''s Mosque', 1),
('Quba Mosque', 'madinah', 'mosque', 24.4392, 39.6172, 'First Mosque in Islam', 2);

-- Dua Categories
INSERT INTO dua_categories (id, journey_type, title, sort_order) VALUES
('11111111-2222-3333-4444-555555555551', 'both', 'Travel & Journey', 1),
('11111111-2222-3333-4444-555555555552', 'umrah', 'Tawaf Duas', 2),
('11111111-2222-3333-4444-555555555553', 'hajj', 'Arafat Duas', 3)
ON CONFLICT (id) DO NOTHING;

-- Duas
INSERT INTO duas (category_id, title, arabic, transliteration, english, urdu, sort_order) VALUES
('11111111-2222-3333-4444-555555555551', 'Dua for Travel', 'سُبْحَانَ الَّذِي سَخَّرَ لَنَا هَٰذَا وَمَا كُنَّا لَهُ مُقْرِنِينَ', 'Subhanal-ladhi sakh-khara lana hadha...', 'Glory to Him Who has subjected this to us...', 'پاک ہے وہ ذات جس نے اس سواری کو ہمارے تابع کیا...', 1),
('11111111-2222-3333-4444-555555555552', 'Talbiyah', 'لَبَّيْكَ اللَّهُمَّ لَبَّيْكَ', 'Labbayka Allahumma Labbayk', 'Here I am, O Allah, here I am', 'حاضر ہوں اے اللہ میں حاضر ہوں', 1);

-- Tasbeehat
INSERT INTO tasbeehat (name, arabic, transliteration, english, urdu, default_target, sort_order) VALUES
('Subhanallah', 'سُبْحَانَ ٱللَّٰهِ', 'Subhanallah', 'Glory be to Allah', 'اللہ پاک ہے', 33, 1),
('Alhamdulillah', 'ٱلْحَمْدُ لِلَّٰهِ', 'Alhamdulillah', 'Praise be to Allah', 'تمام تعریفیں اللہ کے لیے ہیں', 33, 2),
('Allahu Akbar', 'ٱللَّٰهُ أَكْبَرُ', 'Allahu Akbar', 'Allah is the Greatest', 'اللہ سب سے بڑا ہے', 34, 3),
('Astaghfirullah', 'أَسْتَغْفِرُ اللَّهَ', 'Astaghfirullah', 'I seek forgiveness from Allah', 'میں اللہ سے معافی مانگتا ہوں', 100, 4);

-- Meeting Points (Optional sample)
INSERT INTO meeting_points (group_id, latitude, longitude, label, description, is_active) VALUES
('11111111-1111-1111-1111-111111111111', 21.4225, 39.8262, 'King Abdulaziz Gate', 'Meet here after Isha', true);

-- ============================================================
-- EXTENDED: Agency Module Test Data (Elite Hajj Tours)
-- ============================================================

-- Create Agency if not exists
INSERT INTO agencies (id, name, city, status, member_count, online_count)
VALUES ('550e8400-e29b-41d4-a716-446655440001', 'Elite Hajj Tours', 'Karachi', 'active', 0, 0)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  city = EXCLUDED.city,
  status = EXCLUDED.status;

-- Create Admin Account (Tour Operator)
INSERT INTO users_table (id, email, password_hash, full_name, role, agency_id, phone, created_at)
VALUES ('550e8400-e29b-41d4-a716-446655440002', 'admin@elitehajj.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Ahmed Khan', 'admin', '550e8400-e29b-41d4-a716-446655440001', '+92 300 1234567', NOW())
ON CONFLICT (id) DO UPDATE SET
  email = EXCLUDED.email,
  password_hash = EXCLUDED.password_hash,
  full_name = EXCLUDED.full_name,
  role = EXCLUDED.role,
  agency_id = EXCLUDED.agency_id,
  phone = EXCLUDED.phone;

-- Create 4 Group Leaders
INSERT INTO users_table (id, email, password_hash, full_name, role, agency_id, phone, created_at)
VALUES
  ('550e8400-e29b-41d4-a716-446655440010', 'hassan.ahmed@elitehajj.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Hassan Ahmed', 'leader', '550e8400-e29b-41d4-a716-446655440001', '+92 321 1111111', NOW()),
  ('550e8400-e29b-41d4-a716-446655440011', 'fatima.ali@elitehajj.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Fatima Ali', 'leader', '550e8400-e29b-41d4-a716-446655440001', '+92 322 2222222', NOW()),
  ('550e8400-e29b-41d4-a716-446655440012', 'muhammad.khan@elitehajj.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Muhammad Khan', 'leader', '550e8400-e29b-41d4-a716-446655440001', '+92 323 3333333', NOW()),
  ('550e8400-e29b-41d4-a716-446655440013', 'aisha.hussain@elitehajj.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Aisha Hussain', 'leader', '550e8400-e29b-41d4-a716-446655440001', '+92 324 4444444', NOW())
ON CONFLICT (id) DO NOTHING;

-- Create 12 Pilgrims (distributed under leaders)
INSERT INTO users_table (id, email, password_hash, full_name, role, agency_id, leader_id, phone, journey_type, created_at)
VALUES
  -- Under Hassan Ahmed (3 pilgrims)
  ('550e8400-e29b-41d4-a716-446655440020', 'ali.hassan.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Ali Hassan', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440010', '+92 300 9000001', 'hajj', NOW()),
  ('550e8400-e29b-41d4-a716-446655440021', 'sara.hassan.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Sara Hassan', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440010', '+92 300 9000002', 'hajj', NOW()),
  ('550e8400-e29b-41d4-a716-446655440022', 'zain.hassan.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Zain Hassan', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440010', '+92 300 9000003', 'hajj', NOW()),
  
  -- Under Fatima Ali (3 pilgrims)
  ('550e8400-e29b-41d4-a716-446655440030', 'hana.ali.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Hana Ali', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440011', '+92 301 9000001', 'umrah', NOW()),
  ('550e8400-e29b-41d4-a716-446655440031', 'muna.ali.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Muna Ali', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440011', '+92 301 9000002', 'umrah', NOW()),
  ('550e8400-e29b-41d4-a716-446655440032', 'rabia.ali.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Rabia Ali', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440011', '+92 301 9000003', 'umrah', NOW()),
  
  -- Under Muhammad Khan (3 pilgrims)
  ('550e8400-e29b-41d4-a716-446655440040', 'bilal.khan.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Bilal Khan', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440012', '+92 302 9000001', 'hajj', NOW()),
  ('550e8400-e29b-41d4-a716-446655440041', 'amina.khan.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Amina Khan', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440012', '+92 302 9000002', 'hajj', NOW()),
  ('550e8400-e29b-41d4-a716-446655440042', 'nasir.khan.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Nasir Khan', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440012', '+92 302 9000003', 'hajj', NOW()),
  
  -- Under Aisha Hussain (3 pilgrims)
  ('550e8400-e29b-41d4-a716-446655440050', 'noor.hussain.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Noor Hussain', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440013', '+92 303 9000001', 'umrah', NOW()),
  ('550e8400-e29b-41d4-a716-446655440051', 'leila.hussain.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Leila Hussain', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440013', '+92 303 9000002', 'umrah', NOW()),
  ('550e8400-e29b-41d4-a716-446655440052', 'yasmin.hussain.pilgrim@email.com', '$2b$12$obvvmrsMdizF37iLP038l.CJ8ZNdqyEWtT8IMqNSTg04FDAjWnahq', 'Yasmin Hussain', 'pilgrim', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440013', '+92 303 9000003', 'umrah', NOW())
ON CONFLICT (id) DO NOTHING;

-- Add Pilgrim Locations (for Live Map)
INSERT INTO pilgrim_locations (pilgrim_id, group_id, latitude, longitude, battery_level, is_online, recorded_at)
VALUES
  ('550e8400-e29b-41d4-a716-446655440020', '550e8400-e29b-41d4-a716-446655440001', 21.4225, 39.8262, 85, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440001', 21.4225, 39.8270, 72, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440022', '550e8400-e29b-41d4-a716-446655440001', 21.4235, 39.8250, 45, false, timezone('utc'::text, now()) - interval '15 minutes'),
  ('550e8400-e29b-41d4-a716-446655440030', '550e8400-e29b-41d4-a716-446655440001', 24.4539, 39.5669, 92, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440031', '550e8400-e29b-41d4-a716-446655440001', 24.4545, 39.5675, 88, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440032', '550e8400-e29b-41d4-a716-446655440001', 24.4550, 39.5680, 76, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440040', '550e8400-e29b-41d4-a716-446655440001', 21.4200, 39.8300, 91, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440041', '550e8400-e29b-41d4-a716-446655440001', 21.4210, 39.8310, 82, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440050', '550e8400-e29b-41d4-a716-446655440001', 24.4500, 39.5600, 95, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440051', '550e8400-e29b-41d4-a716-446655440001', 24.4510, 39.5610, 87, true, NOW())
ON CONFLICT DO NOTHING;

-- Add SOS Alert (for testing alerts feature)
INSERT INTO sos_alerts (id, pilgrim_id, group_id, latitude, longitude, status, created_at, resolved_at)
VALUES ('550e8400-e29b-41d4-a716-446655440099', '550e8400-e29b-41d4-a716-446655440022', '550e8400-e29b-41d4-a716-446655440001', 21.4235, 39.8250, 'active', NOW(), NULL)
ON CONFLICT (id) DO NOTHING;

-- Add Hotel Info
INSERT INTO hotel_info (org_id, hotel_name, address, latitude, longitude, room_info, check_in_date, check_out_date, hotel_phone, driver_name, driver_phone, bus_number)
VALUES ('550e8400-e29b-41d4-a716-446655440001', 'Hilton Makkah', 'King Fahd St, Makkah', 21.4200, 39.8250, '30 rooms, AC, WiFi', '2026-06-01', '2026-06-08', '+966-12-5555555', 'Ahmed', '+966-50-1234567', 'BUS-001')
ON CONFLICT (org_id) DO NOTHING;

-- Add sample messages
INSERT INTO group_messages (group_id, leader_id, message_type, message_text, sent_at)
VALUES
  ('550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440010', 'text', 'Please gather at the meeting point by 4 PM', NOW() - interval '30 minutes'),
  ('550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440011', 'text', 'Remind everyone to drink water and stay hydrated', NOW() - interval '15 minutes')
ON CONFLICT DO NOTHING;

-- Update agency counters
UPDATE agencies a SET
  member_count = (SELECT count(*) FROM users_table u WHERE u.agency_id = a.id AND u.role IN ('leader', 'pilgrim')),
  online_count = (SELECT count(DISTINCT l.pilgrim_id) FROM pilgrim_locations l WHERE l.group_id = a.id AND l.is_online = true AND l.recorded_at >= timezone('utc'::text, now()) - interval '10 minutes')
WHERE a.id = '550e8400-e29b-41d4-a716-446655440001';

-- Pilgrim Groups Table & Security
CREATE TABLE IF NOT EXISTS pilgrim_groups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_name text NOT NULL,
  agency_id uuid REFERENCES agencies(id) ON DELETE CASCADE,
  leader_id uuid REFERENCES users_table(id) ON DELETE SET NULL,
  pilgrim_id uuid REFERENCES users_table(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  UNIQUE (pilgrim_id) -- A pilgrim can belong to only one group
);

-- Enable Row Level Security (RLS)
ALTER TABLE pilgrim_groups ENABLE ROW LEVEL SECURITY;

-- Create open policy (auth is handled at application level)
DROP POLICY IF EXISTS pilgrim_groups_service_all ON pilgrim_groups;
CREATE POLICY pilgrim_groups_service_all ON pilgrim_groups FOR ALL USING (true) WITH CHECK (true);

-- Create index for faster lookup by agency and group
CREATE INDEX IF NOT EXISTS idx_pilgrim_groups_agency ON pilgrim_groups(agency_id);
CREATE INDEX IF NOT EXISTS idx_pilgrim_groups_name ON pilgrim_groups(group_name);

-- 1. Add group_code column to pilgrim_groups table
ALTER TABLE pilgrim_groups ADD COLUMN IF NOT EXISTS group_code text;

-- 2. Populate existing rows with a registration code
UPDATE pilgrim_groups 
SET group_code = 'AG123-334'
WHERE group_code IS NULL;
