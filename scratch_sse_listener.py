import urllib.request, time
try:
    r = urllib.request.urlopen('http://localhost:4444/api/events', timeout=25)
    print('CONNECTED status', r.status, 'type', r.headers.get('content-type'), flush=True)
    end = time.time() + 22
    while time.time() < end:
        line = r.readline().decode('utf-8','replace').strip()
        if line.startswith('data:'):
            print('RECV:', line, flush=True)
except Exception as e:
    print('LISTENER_ERR:', repr(e), flush=True)
