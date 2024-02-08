import json
from pathlib import Path

assembly_ai_key = None
mongo_port = None
mongo_host = None


# noinspection SpellCheckingInspection
def init():
    global mongo_host, mongo_port
    global assembly_ai_key

    if assembly_ai_key:
        return

    settings = Path(__file__).parent.parent / 'settings.json'
    if not settings.exists():
        raise Exception('Settings file `settings.json` not found, please copy and fill out settings_template.json')

    data = json.loads(settings.read_text())
    assembly_ai_key = data['assemblyai_key']
    mongo_host = data['mongo_host']
    mongo_port = data['mongo_port']

    print('Located access_key, secrets initialized.')


init()
