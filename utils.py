import json
from pathlib import Path

config_path = Path(__file__).parent / "config.json"
with open(config_path, "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
        
TELEGRAM_CHANEL = config["TELEGRAM_CHANEL"]

async def check_subscription(user_id, context):
    try:
        for channel in TELEGRAM_CHANEL:
            chat_member = await context.bot.get_chat_member(channel, user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                return True
        return False
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def push_state(context, state):
    if 'state_stack' not in context.user_data:
        context.user_data['state_stack'] = []
    context.user_data['state_stack'].append(state)

def pop_state(context):
    if 'state_stack' in context.user_data and context.user_data['state_stack']:
        return context.user_data['state_stack'].pop()
    return None

def get_current_state(context):
    if 'state_stack' in context.user_data and context.user_data['state_stack']:
        return context.user_data['state_stack'][-1]
    return None