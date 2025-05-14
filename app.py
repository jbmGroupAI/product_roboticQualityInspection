import os
import uuid
import yaml
import time
import threading
import cv2
import atexit
import oxapi
import datetime

from frameGrab import Camera
from plcController import PlcCommunicate
from weldInspector import WeldInspector

def load_config():
    with open("Config/config.yaml", "r") as f:
        return yaml.safe_load(f)

class Acquisition:
    def __init__(self, config):
        self.config = config
        self.plc = PlcCommunicate("127.0.0.1",12345)
        self.camera = Camera(camStr='Nahar_VI')

        c_thread1 = threading.Thread(target=self.camera.initialize)
        c_thread1.start()

        self.position_actions = {
    int(k): [str(action) for action in v]
    for k, v in config["Position_Wise_Actions"].items()
}
        self.registers = config["PLC_Registers"]
        self.inspector = WeldInspector(config)
        self.use_camera = config.get("Use_Camera", True)
        self.exposure_map = config.get("Position_Exposure", {})

        self.last_position = -1
        self.was_home = True
        self.session_id = None
        self.output_dir = None

        self.profiler = None
        self._init_profiler()
        atexit.register(self._disconnect_profiler)
        
    def generate_session_id(self):
        counter_file = "session_counter.txt"
        prefix = "TVS"

        if not os.path.exists(counter_file):
            with open(counter_file, "w") as f:
                f.write("1")

        with open(counter_file, "r+") as f:
            counter = int(f.read().strip())
            session_id = f"{prefix}{counter:04d}"
            f.seek(0)
            f.write(str(counter + 1))
            f.truncate()

        return session_id
        
    def resume_robot(self):
        resume_register = self.registers.get("Robot_Resume")
        if resume_register is not None:
            print("[Robot] Resuming robot operation.")
            self.plc.write(resume_register, 1)
            time.sleep(0.1)
            self.plc.write(resume_register, 0)
        else:
            print("[Robot] Resume register not defined in config.")



    def _init_profiler(self):
        try:
            self.profiler = oxapi.ox("192.168.0.250", 1234)
            self.profiler.Connect()
            self.profiler.Login("admin", "")
            print("[Profiler] Connected and logged in.")
        except Exception as e:
            print(f"[Profiler] Connection failed: {e}")
            self.profiler = None

    def _ensure_profiler_ready(self):
        if self.profiler is None:
            print("[Profiler] Not connected. Reconnecting...")
            self._init_profiler()
        return self.profiler is not None

    def _disconnect_profiler(self):
        if self.profiler:
            print("[Profiler] Disconnecting...")
            self.profiler.Disconnect()

    def take_profiler_center(self, position_no):
        if not self._ensure_profiler_ready():
            return

        stream = self.profiler.CreateStream()
        stream.Start()
        stream.ClearMeasurementQueue()

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        profiler_dir = os.path.join("profiler_centers", f"pos_{position_no}_{timestamp_str}")
        os.makedirs(profiler_dir, exist_ok=True)
        log_path = os.path.join(profiler_dir, "profile_center.txt")

        print(f"[Profiler] Capturing center values for position {position_no} (5 seconds)")

        try:
            start_time = time.time()
            with open(log_path, "w") as f:
                while time.time() - start_time < 5:
                    time.sleep(0.005)

                    if stream.GetProfileCount() > 0:
                        (
                            blockId, confiMode, ntpSync, valid,
                            alarm, quality, timestamp, length,
                            encoder, x, z, i
                        ) = stream.ReadProfile()

                        f.write(f"Timestamp: {timestamp}, Length: {length}\n")
                        f.write("X: " + ",".join(map(str, x)) + "\n")
                        f.write("Z: " + ",".join(map(str, z)) + "\n\n")

        except Exception as e:
            print(f"[Profiler] Error: {e}")

        stream.Stop()
        print(f"[Profiler] Finished center value capture for position {position_no}")

    def collect_profiler_data(self, position_no):
        if not self._ensure_profiler_ready():
            return

        stream = self.profiler.CreateStream()
        stream.Start()
        stream.ClearMeasurementQueue()

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        profiler_dir = os.path.join("profiler_data", f"pos_{position_no}_{timestamp_str}")
        os.makedirs(profiler_dir, exist_ok=True)
        log_path = os.path.join(profiler_dir, "profile_log.txt")

        print(f"[Profiler] Started for position {position_no}")

        try:
            with open(log_path, "w") as f:
                while True:
                    time.sleep(0.005)
                    current_position = self.plc.read_registers(self.registers["Position_No"])
                    robot_home = self.plc.read_registers(self.registers["Robot_Home"])
                    if robot_home == 1 or current_position != position_no:
                        print(f"[Profiler] Ending capture for position {position_no}")
                        break

                    if stream.GetProfileCount() > 0:
                        (
                            blockId, confiMode, ntpSync, valid,
                            alarm, quality, timestamp, length,
                            encoder, x, z, i
                        ) = stream.ReadProfile()

                        f.write(f"Timestamp: {timestamp}, Length: {length}\n")
                        f.write("X: " + ",".join(map(str, x)) + "\n")
                        f.write("Z: " + ",".join(map(str, z)) + "\n\n")

        except Exception as e:
            print(f"[Profiler] Error: {e}")

        stream.Stop()

    def capture_laser_image(self, position_no):
        if not self._ensure_profiler_ready():
            return

        try:
            width, height, maxPixels = self.profiler.GetImageInfo()
            print(f"[LaserImage] Image info: {width}x{height}, Max Pixels: {maxPixels}")

            retries = 2
            success = False
            for attempt in range(retries):
                try:
                    time.sleep(0.2)
                    result = self.profiler.GetImage()
                    success = True
                    break
                except Exception as e:
                    print(f"[LaserImage] Attempt {attempt + 1} failed: {e}")
                    time.sleep(0.2)  

            if not success:
                print("[LaserImage] Failed to acquire image after retries.")
                return

            roiHeight, roiWidth, rowOffset, colOffset, rowBinning, colBinning, pixels, saveImageFunc = result

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join("laser_images")
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, f"laser_pos{position_no}_{timestamp_str}.png")

            saveImageFunc(filename)
            print(f"[LaserImage] Saved: {filename}")

        except Exception as e:
            print(f"[LaserImage] Error during capture: {e}")

    def check_and_acquire(self):
        print("In Acquire")
        if not self.plc.check_connection():
            if not self.plc.reconnect():
                print("PLC not connected. Skipping this cycle.")
                return
            print("PLC reconnected successfully.")
        
        time.sleep(0.5)
        robot_home = self.plc.read_registers(self.registers["Robot_Home"])
        position_no = self.plc.read_registers(self.registers["Position_No"])
        print("Position No:",position_no)
        print("Robot Home:",robot_home)

        if robot_home == 1:
            if not self.was_home:
                print("Robot returned to home. Showing all weld results.")
                self.inspector.show_all_results()
                self.was_home = True
                self.last_position = -1  
            return

        if self.was_home:
            self.session_id = self.generate_session_id()
            self.output_dir = os.path.join("scans", self.session_id)
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"Started new session: {self.session_id}")
            self.was_home = False

        if position_no != None and position_no > 0:
            if position_no == self.last_position:
                print(f"Position {position_no} already processed. Waiting for next position.")
                return

            self.last_position = position_no
            print(f"Robot at position: {position_no}")
            actions = self.position_actions.get(position_no, [])
            print(f"Actions for position {position_no}: {actions}")

            if "Light" in actions:
                self.plc.write(self.registers["Light_Trigger"], 1)
                time.sleep(0.01)

            if "Camera" in actions:
                filename = os.path.join(self.output_dir, f"scan_position_{position_no}.jpg")

                if self.use_camera:
                    exposure = self.exposure_map.get(position_no, None)
                    if exposure is not None:
                        print(f"Setting exposure to {exposure} for position {position_no}")
                        self.camera.expo_control(exposure)

                    frame = self.camera.get_image_mv()
                    if frame is None:
                        print("Primary camera failed. Switching to webcam.")
                        cap = cv2.VideoCapture(0)
                        ret, frame = cap.read()
                        cap.release()
                        if not ret or frame is None:
                            print("Webcam capture failed. Skipping image save.")
                            return

                    cv2.imwrite(filename, frame)
                    print(f"Image saved to {filename}")

                    raw_dir = os.path.join("raw_images")
                    os.makedirs(raw_dir, exist_ok=True)
                    raw_path = os.path.join(raw_dir, f"pos_{position_no}.jpg")
                    cv2.imwrite(raw_path, frame)
                    print(f"Raw image saved to {raw_path}")
                    # self.plc.write(11, 1)
                    # time.sleep(0.8)
                    # self.plc.write(11, 0)
                    # print("DONE")
                    
                else:
                    raw_path = os.path.join("raw_images", f"pos_{position_no}.jpg")
                    if not os.path.exists(raw_path):
                        print(f"Raw image not found: {raw_path}. Skipping inspection.")
                        return
                    frame = cv2.imread(raw_path)
                    if frame is None:
                        print(f"Failed to load raw image: {raw_path}")
                        return
                    cv2.imwrite(filename, frame)
                    print(f"Loaded raw image instead of capturing: {raw_path}")

                threading.Thread(target=self.inspector.inspect, args=(position_no, filename), daemon=True).start()

            if "LaserImage" in actions:
                self.capture_laser_image(position_no)

            if "Profiler" in actions:
                threading.Thread(target=self.collect_profiler_data, args=(position_no,), daemon=True).start()

            if "Profiler_center" in actions:
                threading.Thread(target=self.take_profiler_center, args=(position_no,), daemon=True).start()

            if "Light" in actions:
                self.plc.write(self.registers["Light_Trigger"], 0)

            self.resume_robot()
            print("------------------- [ROBOT] Operations Resumed ------------------------------")
            time.sleep(0.001)

if __name__ == "__main__":
    config = load_config()
    acq = Acquisition(config)

    try:
        while True:
            print("^^^^^^^^^^^^^^^^^^^^^^^^")
            acq.check_and_acquire()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("Graceful shutdown initiated.")


