-- Pilgrim360 Supabase PostgreSQL Schema

-- 1. Profiles Table (Pilgrims, Leaders, Admins)
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('pilgrim', 'leader', 'super_admin')),
    phone TEXT,
    group_code TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Agencies Table
CREATE TABLE public.agencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    contact_email TEXT,
    contact_phone TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Groups Table
CREATE TABLE public.groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_code TEXT UNIQUE NOT NULL,
    agency_id UUID REFERENCES public.agencies(id) ON DELETE CASCADE,
    leader_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    journey_type TEXT CHECK (journey_type IN ('hajj', 'umrah')),
    hotel_name TEXT,
    hotel_address TEXT,
    hotel_lat NUMERIC,
    hotel_lon NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. SOS Alarms Table
CREATE TABLE public.sos_alarms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pilgrim_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    group_code TEXT NOT NULL,
    lat NUMERIC NOT NULL,
    lon NUMERIC NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'resolved')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Locations/Milestones Table
CREATE TABLE public.locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pilgrim_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    lat NUMERIC NOT NULL,
    lon NUMERIC NOT NULL,
    type TEXT DEFAULT 'custom' CHECK (type IN ('tent', 'hotel', 'kaaba', 'custom')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sos_alarms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.locations ENABLE ROW LEVEL SECURITY;

-- Examples of Policies (can be expanded based on specific auth flow)
CREATE POLICY "Users can read their own profile" 
ON public.profiles FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Leaders can read their group's profiles" 
ON public.profiles FOR SELECT USING (
    group_code = (SELECT group_code FROM public.profiles WHERE id = auth.uid() AND role = 'leader')
);
