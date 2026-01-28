import time
import os
import struct
import threading
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput
from nacl.signing import SigningKey

# --- CONFIGURATION ---
MQTT_BROKER = "laptop.local"  # <--- CHANGE TO LAPTOP IP
TOPIC = "cam"
RECORD_SECONDS = 60
CHUNK_SIZE = 4096  # Size of data chunks to read/sign

# --- 1. SETUP CRYPTO & MQTT ---
print("Generating Keys...")
signing_key = SigningKey.generate()
verify_key_bytes = signing_key.verify_key.encode()

print("Connecting to MQTT...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, 1883)
client.loop_start()

# --- 2. CREATE A PIPE ---
# r_fd is for reading (Python), w_fd is for writing (Camera)
r_fd, w_fd = os.pipe()

# --- 3. THE SIGNING WORKER ---
# This runs in the background, reading video from the pipe, signing it, and sending it.
def signing_worker(read_file_descriptor):
    frame_count = 0
    print("Worker: Started listening for video data...")
    
    # Wrap the file descriptor in a Python file object for easier reading
    with os.fdopen(read_file_descriptor, 'rb') as pipe_reader:
        while True:
            try:
                # Read a chunk of raw video data
                buf = pipe_reader.read(CHUNK_SIZE)
                if not buf:
                    break # End of stream

                # A. Sign
                start = time.perf_counter()
                signature = signing_key.sign(buf).signature
                duration_us = int((time.perf_counter() - start) * 1_000_000)

                # B. Pack [Data] [Sig] [Pub] [Time]
                time_bytes = struct.pack('<I', duration_us)
                full_payload = buf + signature + verify_key_bytes + time_bytes

                # C. Send
                client.publish(TOPIC, full_payload)
                
                frame_count += 1
                if frame_count % 50 == 0:
                    print(f"Sent Chunk #{frame_count} | Size: {len(buf)} | SignTime: {duration_us}us")
            
            except Exception as e:
                print(f"Worker Error: {e}")
                break
    
    print("Worker: Stopped.")

# Start the worker thread
t = threading.Thread(target=signing_worker, args=(r_fd,))
t.start()

# --- 4. SETUP CAMERA ---
print("Configuring Camera...")
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "YUV420"},
    controls={"FrameDurationLimits": (33333, 33333)}
)
picam2.configure(config)
picam2.start()

encoder = H264Encoder(bitrate=2000000)

# --- 5. SETUP PYAV OUTPUT ---
# We point PyavOutput to our pipe's write end using "pipe:"
# format="h264" keeps it as raw video, which is easier to append together on the receiver
output = PyavOutput(f"pipe:{w_fd}", format="h264")

print(f"Recording for {RECORD_SECONDS} seconds...")
picam2.start_recording(encoder, output)

try:
    time.sleep(RECORD_SECONDS)
except KeyboardInterrupt:
    print("Stopping early...")

# --- CLEANUP ---
picam2.stop_recording()
picam2.stop()

# Close the write end of the pipe to signal the worker to stop
os.close(w_fd)
t.join() # Wait for worker to finish
client.disconnect()
print("Done.")
