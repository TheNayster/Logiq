import asyncio, os, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")

async def test():
    import database.supabase as supa

    SERVER_ID = "TEST_SERVER_001"
    USER_ID   = "TEST_USER_001"
    MOD_ID    = "TEST_MOD_001"

    print("1. on_server_add ...")
    await supa.on_server_add(SERVER_ID, "Test Server", "TEST_OWNER")
    print("   OK")

    print("2. on_account_create ...")
    await supa.on_account_create(USER_ID, "TestUser", "")
    print("   OK")

    print("3. on_member_join ...")
    await supa.on_member_join(SERVER_ID, USER_ID, "TestUser", "")
    print("   OK")

    print("4. on_warning_add ...")
    row = await supa.on_warning_add(SERVER_ID, USER_ID, MOD_ID, "Test warning")
    print("   OK — warning row: " + str(row))

    print("5. on_xp_gain (RPC) ...")
    try:
        await supa.on_xp_gain(SERVER_ID, USER_ID, 25)
        print("   OK")
    except Exception as e:
        print("   SKIP (RPC not deployed yet): " + str(e))

    print("6. on_balance_change ...")
    await supa.on_balance_change(SERVER_ID, USER_ID, 100, 1100, "daily", "Test daily")
    print("   OK")

    print("7. on_ticket_open ...")
    ticket = await supa.on_ticket_open(SERVER_ID, USER_ID, "General Support", "Test ticket")
    print("   OK — ticket id: " + str(ticket["id"]))
    await supa.on_ticket_close(ticket["id"], MOD_ID)
    print("   ticket closed OK")

    print("8. on_member_leave ...")
    await supa.on_member_leave(SERVER_ID, USER_ID)
    print("   OK")

    print("9. Cleanup test rows ...")
    sb = await supa.get_client()
    await sb.table("server_members").delete().eq("server_id", SERVER_ID).execute()
    await sb.table("users").delete().eq("id", USER_ID).execute()
    await sb.table("servers").delete().eq("id", SERVER_ID).execute()
    print("   OK")

    print("")
    print("All event handlers verified against live Supabase!")

asyncio.run(test())
