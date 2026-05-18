import os

DEFAULT_PORT = int(os.environ.get('DEFAULT_PORT', 57988))
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', f'http://localhost:{DEFAULT_PORT}')
