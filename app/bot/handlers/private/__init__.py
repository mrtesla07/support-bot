from . import admin_greeting
from . import admin_resolution
from . import callback_query
from . import command
from . import message
from . import my_chat_member

routers = [
    command.router,
    admin_greeting.router,
    admin_resolution.router,
    message.router,
    callback_query.router,
    my_chat_member.router,
]
