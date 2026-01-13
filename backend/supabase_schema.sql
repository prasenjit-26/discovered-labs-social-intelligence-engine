-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Communities
create table if not exists communities (
    id text primary key,
    name text not null,
    url text,
    platform text,
    subscribers int,
    active_users int,
    description text,
    relevance_score float,
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Posts
create table if not exists posts (
    id text primary key,
    platform text,
    content text,
    author_id text,
    author_username text,
    community_id text references communities(id),
    timestamp timestamp with time zone,
    engagement_score float,
    url text,
    sentiment float,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Entities (Canonical)
create table if not exists entities (
    name text primary key,
    label text,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Entity Variations (Map 'open ai' -> 'OpenAI')
create table if not exists entity_variations (
    variation text primary key,
    canonical_name text references entities(name),
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Relationships (Graph Edges)
create table if not exists relationships (
    id uuid default uuid_generate_v4() primary key,
    company_domain text not null,
    source text references entities(name),
    target text references entities(name),
    relation text not null,
    confidence float default 1.0,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    unique(company_domain, source, target, relation)
);

-- Company -> Communities (Discovery results per company)
create table if not exists company_communities (
    company_domain text not null,
    community_id text not null references communities(id),
    relevance_score float,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now()),
    primary key (company_domain, community_id)
);
