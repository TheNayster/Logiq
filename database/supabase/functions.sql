-- =============================================================================
-- StoatMod  —  Supabase RPC Helper Functions
-- Run after schema.sql.  These are called from Python via sb.rpc(...)
-- All parameters are typed; PostgREST passes them as bind variables (safe).
-- =============================================================================

-- increment_xp: atomically add XP and message count to a server_member row.
create or replace function increment_xp(
  p_server_id text,
  p_user_id   text,
  p_xp        int
)
returns void language sql security definer as $$
  update server_members
     set xp             = xp + p_xp,
         total_messages = total_messages + 1,
         last_xp_at     = now(),
         updated_at     = now()
   where server_id = p_server_id
     and user_id   = p_user_id;
$$;

-- increment_command_use: atomically bump custom command counter.
create or replace function increment_command_use(
  p_server_id text,
  p_trigger   text
)
returns void language sql security definer as $$
  update custom_commands
     set use_count  = use_count + 1,
         updated_at = now()
   where server_id = p_server_id
     and trigger   = p_trigger;
$$;

-- get_leaderboard: top N members by XP for a server.
create or replace function get_leaderboard(
  p_server_id text,
  p_limit     int default 10
)
returns table (
  user_id      text,
  display_name text,
  xp           bigint,
  level        int,
  rank         bigint
) language sql security definer as $$
  select user_id,
         display_name,
         xp,
         level,
         row_number() over (order by xp desc) as rank
    from server_members
   where server_id = p_server_id
     and left_at is null
   order by xp desc
   limit p_limit;
$$;

-- get_economy_leaderboard: top N members by balance.
create or replace function get_economy_leaderboard(
  p_server_id text,
  p_limit     int default 10
)
returns table (
  user_id      text,
  display_name text,
  balance      bigint,
  rank         bigint
) language sql security definer as $$
  select user_id,
         display_name,
         balance,
         row_number() over (order by balance desc) as rank
    from server_members
   where server_id = p_server_id
     and left_at is null
   order by balance desc
   limit p_limit;
$$;

-- get_warning_count: active warning count for a user in a server.
create or replace function get_warning_count(
  p_server_id text,
  p_user_id   text
)
returns int language sql security definer as $$
  select count(*)::int
    from warnings
   where server_id = p_server_id
     and user_id   = p_user_id
     and active    = true;
$$;

-- get_pending_reminders: fetch all reminders due now.
create or replace function get_pending_reminders()
returns table (
  id         uuid,
  server_id  text,
  user_id    text,
  channel_id text,
  message    text,
  remind_at  timestamptz
) language sql security definer as $$
  select id, server_id, user_id, channel_id, message, remind_at
    from reminders
   where completed = false
     and remind_at <= now()
   order by remind_at;
$$;
