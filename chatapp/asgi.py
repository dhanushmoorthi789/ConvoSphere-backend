# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import chat.routing

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatapp.settings')

# application = ProtocolTypeRouter({
#     'http': get_asgi_application(),
#     'websocket': AuthMiddlewareStack(
#         URLRouter(chat.routing.websocket_urlpatterns)
#     ),
# })

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