"""
The logged-in user's own profile.

context.user_data["agent"] must ALWAYS be the profile of the Telegram user who is
talking to the bot. Earlier the edit button stored the order owner's profile there,
so an admin editing an agent's order suddenly got the agent menu (and the other way).
Order data now lives only in "order"/"edit_order_id"; the profile comes from the backend.
"""
from services.api import get_me, getting_one_agent


def remember_profile(context, agent: dict):
    if agent:
        context.user_data["agent"] = agent
        context.user_data["agent_id"] = agent.get("id")


async def get_profile(update, context, refresh: bool = False):
    """Own profile: from the backend when possible (role changes are picked up), else the cached one."""
    telegram_id = update.effective_user.id if update.effective_user else None
    cached = context.user_data.get("agent")
    # a cached profile that belongs to someone else (old bug) is never trusted
    if cached and cached.get("telegram_id") not in (None, telegram_id):
        cached = None
        context.user_data.pop("agent", None)
        context.user_data.pop("agent_id", None)

    if telegram_id and (refresh or not cached):
        me = get_me(telegram_id)
        if me is None and context.user_data.get("agent_id"):
            # older backend without /agents/me
            me = getting_one_agent(telegram_id, context.user_data["agent_id"])
            if me and me.get("telegram_id") not in (None, telegram_id):
                me = None
        if me:
            remember_profile(context, me)
            return me
    return cached
