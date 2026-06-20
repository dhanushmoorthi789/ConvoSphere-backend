import os
import django

from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatapp.settings')

django.setup()   # ✅ VERY IMPORTANT

import chat.routing

application = ProtocolTypeRouter({
    "websocket": URLRouter(
        chat.routing.websocket_urlpatterns
    ),
})