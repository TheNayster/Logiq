-- =============================================================================
-- StoatMod / Logiq  —  Supabase PostgreSQL Schema
-- Mirrors every feature MEE6 tracks + Stoat-native extras
-- Run this once against your project via the Supabase SQL editor or CLI.
-- All statements use parameterised DDL so they are safe to re-run (IF NOT EXISTS).
-- =============================================================================

-- ── EXTENSIONS ────────────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ── HELPER: auto-update updated_at ────────────────────────────────────────────
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- =============================================================================
-- TABLE: servers
-- One row per Stoat server (guild) that has added the bot.
-- Equivalent to MEE6's "server settings" object.
-- =============================================================================
create table if not exists servers (
  id                  text        primary key,          -- Stoat server ID (ULID string)
  name                text        not null default '',
  owner_id            text        not null default '',
  prefix              text        not null default '!',
  locale              text        not null default 'en',
  icon_url            text,
  -- feature toggles (MEE6-parity)
  moderation_enabled  boolean     not null default true,
  leveling_enabled    boolean     not null default true,
  economy_enabled     boolean     not null default true,
  music_enabled       boolean     not null default false,
  welcome_enabled     boolean     not null default true,
  goodbye_enabled     boolean     not null default true,
  automod_enabled     boolean     not null default true,
  tickets_enabled     boolean     not null default true,
  giveaways_enabled   boolean     not null default true,
  reaction_roles_enabled boolean  not null default true,
  -- channels
  log_channel_id      text,
  welcome_channel_id  text,
  goodbye_channel_id  text,
  mod_log_channel_id  text,
  -- welcome / goodbye messages
  welcome_message     text        default 'Welcome {user} to {server}!',
  goodbye_message     text        default 'Goodbye {user}!',
  -- timestamps
  bot_joined_at       timestamptz not null default now(),
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create or replace trigger trg_servers_updated_at
  before update on servers
  for each row execute function set_updated_at();

-- =============================================================================
-- TABLE: server_members
-- One row per (server, user) pair.  Tracks join/leave, roles, mod state.
-- MEE6 equivalent: member profile inside a server.
-- =============================================================================
create table if not exists server_members (
  id                  uuid        primary key default uuid_generate_v4(),
  server_id           text        not null references servers(id) on delete cascade,
  user_id             text        not null,
  -- profile
  display_name        text,
  avatar_url          text,
  -- roles stored as text array of Stoat role IDs
  roles               text[]      not null default '{}',
  -- permissions
  is_owner            boolean     not null default false,
  is_admin            boolean     not null default false,
  is_mod              boolean     not null default false,
  is_muted            boolean     not null default false,
  is_banned           boolean     not null default false,
  -- MEE6 leveling
  xp                  bigint      not null default 0,
  level               int         not null default 0,
  total_messages      bigint      not null default 0,
  last_xp_at          timestamptz,
  -- economy
  balance             bigint      not null default 1000,
  last_daily_at       timestamptz,
  -- join / leave tracking
  joined_at           timestamptz not null default now(),
  left_at             timestamptz,
  rejoin_count        int         not null default 0,
  -- timestamps
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (server_id, user_id)
);

create index if not exists idx_server_members_server   on server_members(server_id);
create index if not exists idx_server_members_user     on server_members(user_id);
create index if not exists idx_server_members_xp       on server_members(server_id, xp desc);
create index if not exists idx_server_members_balance  on server_members(server_id, balance desc);

create or replace trigger trg_server_members_updated_at
  before update on server_members
  for each row execute function set_updated_at();

-- =============================================================================
-- TABLE: users
-- Global user profile — exists once per Stoat user ID regardless of servers.
-- Populated on first interaction; auth.users row created via Supabase Auth.
-- =============================================================================
create table if not exists users (
  id                  text        primary key,   -- Stoat user ID (matches auth.users.id when linked)
  username            text        not null default '',
  discriminator       text        not null default '0000',
  display_name        text,
  avatar_url          text,
  email               text,                      -- only set when user links account via dashboard
  auth_uid            uuid        references auth.users(id) on delete set null,
  -- global stats
  total_servers       int         not null default 0,
  -- account state
  is_verified         boolean     not null default false,
  is_bot              boolean     not null default false,
  is_banned_global    boolean     not null default false,
  -- timestamps
  first_seen_at       timestamptz not null default now(),
  last_seen_at        timestamptz not null default now(),
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create or replace trigger trg_users_updated_at
  before update on users
  for each row execute function set_updated_at();

-- =============================================================================
-- TABLE: mod_actions
-- Full audit log of every moderation event.
-- MEE6 equivalent: infractions / moderation log.
-- =============================================================================
create table if not exists mod_actions (
  id              uuid        primary key default uuid_generate_v4(),
  server_id       text        not null references servers(id) on delete cascade,
  target_id       text        not null,   -- Stoat user ID of the person actioned
  moderator_id    text        not null,   -- Stoat user ID of the mod
  action_type     text        not null,   -- warn | kick | ban | unban | mute | unmute | timeout | note
  reason          text        not null default 'No reason provided',
  duration_secs   bigint,                 -- for mute/timeout; null = permanent
  expires_at      timestamptz,
  active          boolean     not null default true,
  -- internal case number per server (1, 2, 3…)
  case_number     int,
  created_at      timestamptz not null default now()
);

create index if not exists idx_mod_actions_server     on mod_actions(server_id);
create index if not exists idx_mod_actions_target     on mod_actions(target_id);
create index if not exists idx_mod_actions_moderator  on mod_actions(moderator_id);
create index if not exists idx_mod_actions_type       on mod_actions(action_type);

-- auto-increment case number per server
create or replace function assign_case_number()
returns trigger language plpgsql as $$
declare
  next_case int;
begin
  select coalesce(max(case_number), 0) + 1
    into next_case
    from mod_actions
   where server_id = new.server_id;
  new.case_number = next_case;
  return new;
end $$;

create or replace trigger trg_mod_actions_case
  before insert on mod_actions
  for each row execute function assign_case_number();

-- =============================================================================
-- TABLE: warnings
-- Separate warning counter per member (MEE6 !warn system).
-- =============================================================================
create table if not exists warnings (
  id              uuid        primary key default uuid_generate_v4(),
  server_id       text        not null references servers(id) on delete cascade,
  user_id         text        not null,
  moderator_id    text        not null,
  reason          text        not null default 'No reason provided',
  active          boolean     not null default true,
  created_at      timestamptz not null default now()
);

create index if not exists idx_warnings_server_user on warnings(server_id, user_id);

-- =============================================================================
-- TABLE: level_rewards
-- Roles awarded automatically when a member reaches a level (MEE6 role rewards).
-- =============================================================================
create table if not exists level_rewards (
  id          uuid  primary key default uuid_generate_v4(),
  server_id   text  not null references servers(id) on delete cascade,
  level       int   not null,
  role_id     text  not null,
  created_at  timestamptz not null default now(),
  unique (server_id, level, role_id)
);

-- =============================================================================
-- TABLE: automod_rules
-- Per-server automod configuration (MEE6 automod plugin).
-- =============================================================================
create table if not exists automod_rules (
  id              uuid    primary key default uuid_generate_v4(),
  server_id       text    not null references servers(id) on delete cascade,
  rule_type       text    not null,  -- spam | banned_words | caps | links | mentions | invites | zalgo
  enabled         boolean not null default true,
  -- action to take: delete | warn | mute | kick | ban
  action          text    not null default 'delete',
  -- rule-specific config stored as jsonb
  config          jsonb   not null default '{}',
  -- e.g. {"threshold": 5, "interval_secs": 5} for spam
  --      {"words": ["badword1"], "wildcards": true} for banned_words
  --      {"max_percent": 70} for caps
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create or replace trigger trg_automod_rules_updated_at
  before update on automod_rules
  for each row execute function set_updated_at();

-- =============================================================================
-- TABLE: custom_commands
-- Server-defined !trigger → response pairs (MEE6 custom commands plugin).
-- =============================================================================
create table if not exists custom_commands (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    not null references servers(id) on delete cascade,
  trigger     text    not null,
  response    text    not null,
  enabled     boolean not null default true,
  -- permissions: null = everyone
  required_role_id  text,
  cooldown_secs     int  not null default 0,
  use_count         bigint not null default 0,
  created_by        text  not null default '',
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  unique (server_id, trigger)
);

create or replace trigger trg_custom_commands_updated_at
  before update on custom_commands
  for each row execute function set_updated_at();

-- =============================================================================
-- TABLE: tickets
-- Support ticket system.
-- =============================================================================
create table if not exists tickets (
  id              uuid    primary key default uuid_generate_v4(),
  server_id       text    not null references servers(id) on delete cascade,
  creator_id      text    not null,
  channel_id      text,               -- Stoat channel created for this ticket
  category        text    not null default 'General Support',
  subject         text,
  status          text    not null default 'open',  -- open | closed | resolved
  claimed_by      text,               -- mod who claimed it
  transcript_url  text,
  created_at      timestamptz not null default now(),
  closed_at       timestamptz,
  updated_at      timestamptz not null default now()
);

create index if not exists idx_tickets_server   on tickets(server_id);
create index if not exists idx_tickets_creator  on tickets(creator_id);
create index if not exists idx_tickets_status   on tickets(status);

create or replace trigger trg_tickets_updated_at
  before update on tickets
  for each row execute function set_updated_at();

-- =============================================================================
-- TABLE: ticket_messages
-- Individual messages within a ticket for transcript storage.
-- =============================================================================
create table if not exists ticket_messages (
  id          uuid    primary key default uuid_generate_v4(),
  ticket_id   uuid    not null references tickets(id) on delete cascade,
  author_id   text    not null,
  content     text    not null,
  created_at  timestamptz not null default now()
);

create index if not exists idx_ticket_messages_ticket on ticket_messages(ticket_id);

-- =============================================================================
-- TABLE: giveaways
-- Giveaway state (MEE6 giveaway plugin).
-- =============================================================================
create table if not exists giveaways (
  id              uuid    primary key default uuid_generate_v4(),
  server_id       text    not null references servers(id) on delete cascade,
  channel_id      text    not null,
  message_id      text,               -- Stoat message containing the giveaway embed
  host_id         text    not null,
  prize           text    not null,
  winner_count    int     not null default 1,
  required_role_id text,
  required_level  int,
  status          text    not null default 'active',  -- active | ended | cancelled
  winners         text[]  not null default '{}',
  ends_at         timestamptz not null,
  created_at      timestamptz not null default now(),
  ended_at        timestamptz
);

create index if not exists idx_giveaways_server  on giveaways(server_id);
create index if not exists idx_giveaways_status  on giveaways(status);

-- =============================================================================
-- TABLE: giveaway_entries
-- Who entered a giveaway.
-- =============================================================================
create table if not exists giveaway_entries (
  id            uuid  primary key default uuid_generate_v4(),
  giveaway_id   uuid  not null references giveaways(id) on delete cascade,
  user_id       text  not null,
  entered_at    timestamptz not null default now(),
  unique (giveaway_id, user_id)
);

-- =============================================================================
-- TABLE: reaction_roles
-- Emoji → role mappings (MEE6 reaction roles plugin).
-- =============================================================================
create table if not exists reaction_roles (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    not null references servers(id) on delete cascade,
  channel_id  text    not null,
  message_id  text    not null,
  emoji       text    not null,
  role_id     text    not null,
  -- mode: single (remove other roles in group), multiple, verify (one-time)
  mode        text    not null default 'multiple',
  group_id    text,               -- for single-mode grouping
  created_at  timestamptz not null default now(),
  unique (server_id, message_id, emoji)
);

-- =============================================================================
-- TABLE: economy_inventory
-- Per-member item ownership.
-- =============================================================================
create table if not exists economy_inventory (
  id          uuid  primary key default uuid_generate_v4(),
  server_id   text  not null references servers(id) on delete cascade,
  user_id     text  not null,
  item_id     text  not null,
  item_name   text  not null,
  quantity    int   not null default 1,
  acquired_at timestamptz not null default now()
);

create index if not exists idx_inventory_member on economy_inventory(server_id, user_id);

-- =============================================================================
-- TABLE: economy_shop
-- Per-server shop items.
-- =============================================================================
create table if not exists economy_shop (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    not null references servers(id) on delete cascade,
  name        text    not null,
  description text,
  price       bigint  not null,
  role_id     text,               -- role granted on purchase (null = virtual item)
  stock       int     not null default -1,  -- -1 = unlimited
  enabled     boolean not null default true,
  created_at  timestamptz not null default now()
);

-- =============================================================================
-- TABLE: economy_transactions
-- Full ledger of balance changes.
-- =============================================================================
create table if not exists economy_transactions (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    not null references servers(id) on delete cascade,
  user_id     text    not null,
  amount      bigint  not null,      -- positive = credit, negative = debit
  balance_after bigint not null,
  type        text    not null,      -- daily | transfer | shop | gamble | admin | xp_reward
  description text,
  ref_id      text,                  -- ticket_id / giveaway_id / etc.
  created_at  timestamptz not null default now()
);

create index if not exists idx_transactions_member on economy_transactions(server_id, user_id);

-- =============================================================================
-- TABLE: reminders
-- Per-user timed reminders (!remind).
-- =============================================================================
create table if not exists reminders (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    not null references servers(id) on delete cascade,
  user_id     text    not null,
  channel_id  text    not null,
  message     text    not null,
  remind_at   timestamptz not null,
  completed   boolean not null default false,
  created_at  timestamptz not null default now()
);

create index if not exists idx_reminders_pending on reminders(remind_at) where completed = false;

-- =============================================================================
-- TABLE: social_alerts
-- Twitch / YouTube / Twitter feed subscriptions.
-- =============================================================================
create table if not exists social_alerts (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    not null references servers(id) on delete cascade,
  channel_id  text    not null,
  platform    text    not null,   -- twitch | youtube | twitter
  account     text    not null,
  last_post_id text,
  enabled     boolean not null default true,
  created_by  text    not null default '',
  created_at  timestamptz not null default now(),
  unique (server_id, platform, account)
);

-- =============================================================================
-- TABLE: analytics_events
-- Lightweight event stream for Discover ranking and dashboards.
-- =============================================================================
create table if not exists analytics_events (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    not null references servers(id) on delete cascade,
  user_id     text,
  event_type  text    not null,   -- message | command | join | leave | level_up | ban | etc.
  data        jsonb   not null default '{}',
  created_at  timestamptz not null default now()
);

create index if not exists idx_analytics_server_time on analytics_events(server_id, created_at desc);

-- =============================================================================
-- TABLE: audit_log
-- Bot-level audit trail (separate from Stoat's built-in audit log).
-- =============================================================================
create table if not exists audit_log (
  id          uuid    primary key default uuid_generate_v4(),
  server_id   text    references servers(id) on delete cascade,
  actor_id    text,               -- user or 'system'
  action      text    not null,
  target_type text,               -- user | server | channel | role | command
  target_id   text,
  old_value   jsonb,
  new_value   jsonb,
  ip_hash     text,               -- hashed, never raw
  created_at  timestamptz not null default now()
);

create index if not exists idx_audit_server on audit_log(server_id, created_at desc);

-- =============================================================================
-- ROW-LEVEL SECURITY (RLS)
-- Enabled on every table. Bot uses service-role key (bypasses RLS).
-- Dashboard users only see their own server's data.
-- =============================================================================
alter table servers             enable row level security;
alter table server_members      enable row level security;
alter table users               enable row level security;
alter table mod_actions         enable row level security;
alter table warnings            enable row level security;
alter table level_rewards       enable row level security;
alter table automod_rules       enable row level security;
alter table custom_commands     enable row level security;
alter table tickets             enable row level security;
alter table ticket_messages     enable row level security;
alter table giveaways           enable row level security;
alter table giveaway_entries    enable row level security;
alter table reaction_roles      enable row level security;
alter table economy_inventory   enable row level security;
alter table economy_shop        enable row level security;
alter table economy_transactions enable row level security;
alter table reminders           enable row level security;
alter table social_alerts       enable row level security;
alter table analytics_events    enable row level security;
alter table audit_log           enable row level security;

-- Policy: authenticated dashboard users may only read their own server's rows.
-- The bot uses the service_role key which bypasses RLS entirely.
create policy "server_owner_read" on servers
  for select using (auth.uid()::text = owner_id);

create policy "member_read_own_server" on server_members
  for select using (
    server_id in (select id from servers where owner_id = auth.uid()::text)
  );
