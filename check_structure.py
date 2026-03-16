import os
base = "/media/Main Files/tenbytes/livekit-call"
for root, dirs, files in os.walk(base):
    # skip venv, __pycache__, .git
    dirs[:] = [d for d in dirs if d not in ('venv', '__pycache__', '.git', 'node_modules')]
    level = root.replace(base, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        fpath = os.path.join(root, file)
        print(f'{subindent}{file} ({os.path.getsize(fpath)} bytes)')
