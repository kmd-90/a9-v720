import urllib.request, threading, time, socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOURCE_URL = "http://127.0.0.1:80/dev/080d090314D0/live"

frame_cond = threading.Condition()
latest_frame = None
frame_id = 0

def grab_frames():
    global latest_frame, frame_id
    while True:
        try:
            req = urllib.request.urlopen(SOURCE_URL, timeout=5)
            buf = bytearray()
            while True:
                chunk = req.read(8192)
                if not chunk:
                    break
                buf.extend(chunk)
                # Prevent buffer buildup if stream stalls
                if len(buf) > 500000:
                    del buf[:-100000]

                start = buf.find(b"\xff\xd8")
                if start == -1:
                    continue
                # Look for next JPEG start so we always extract a complete frame
                next_start = buf.find(b"\xff\xd8", start + 2)
                if next_start != -1:
                    end = buf.rfind(b"\xff\xd9", start, next_start)
                    if end != -1:
                        jpg = bytes(buf[start:end + 2])
                        with frame_cond:
                            latest_frame = jpg
                            frame_id += 1
                            frame_cond.notify_all()
                    del buf[:next_start]
        except Exception:
            time.sleep(0.5)

class RelayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/live"):
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            last_sent_id = -1
            try:
                while True:
                    with frame_cond:
                        while frame_id == last_sent_id:
                            if not frame_cond.wait(timeout=3.0):
                                break
                        jpg = latest_frame
                        last_sent_id = frame_id

                    if jpg:
                        header = (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n"
                        )
                        self.wfile.write(header + jpg + b"\r\n")
                        self.wfile.flush()
            except Exception:
                pass
        else:
            self.send_response(404)
            self.end_headers()

threading.Thread(target=grab_frames, daemon=True).start()
print("[*] Low-Latency Multi-Viewer Relay active at http://192.168.2.22:8080/live")
ThreadingHTTPServer(("0.0.0.0", 8080), RelayHandler).serve_forever()
