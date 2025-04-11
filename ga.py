import cv2

import numpy as np

from collections import defaultdict

from ultralytics import YOLO

import time

import json

import requests

from datetime import datetime, timedelta

from function import *

import paho.mqtt.client as mqtt

import json

import threading

import socket

from dotenv import load_dotenv

import os

import shutil  # Importing shutil to handle file operations



load_dotenv(".env", override=True) 

mqtt_broker = os.getenv('MQTT_BROKER') 

mqtt_port = int(os.getenv('MQTT_PORT')) 

mqtt_user = os.getenv('MQTT_USER') 

mqtt_pass = os.getenv('MQTT_PASS') 

Device_ID = os.getenv('DEVICE_ID') 

authorization_token = os.getenv('AUTHORIZATION_TOKEN') 



file_log = datetime.now().strftime('%d.%m.%Y') + '.txt'

# rb_file_path = r"/home/inovasi/Downloads/HeatMap_3/dynamic/RB_Value.txt"

# br_file_path = r"/home/inovasi/Downloads/HeatMap_3/dynamic/BR_Value.txt"

# count_ss_file_path = 'dynamic/screenshoot/count/Screenshoot.png'

# square_ss_file_path = 'dynamic/screenshoot/heat_map/Screenshoot.png'



rb_file_path = r"/home/inovasi/Downloads/car_drop_off/dynamic/RB_Value.txt"

br_file_path = r"/home/inovasi/Downloads/car_drop_off/dynamic/BR_Value.txt"

dwelingtime_area_file_path = r"/home/inovasi/Downloads/car_drop_off/dynamic/dwelingtime.json"

count_ss_file_path = '/home/inovasi/Downloads/car_drop_off/dynamic/screenshoot/count/Screenshoot.png'

square_ss_file_path = '/home/inovasi/Downloads/car_drop_off/dynamic/screenshoot/square/Screenshoot.png'





save_data_RB_Path = r"/home/inovasi/Downloads/car_drop_off/save_data/last_data_count_RB.json"

save_data_BR_Path = r"/home/inovasi/Downloads/car_drop_off/save_data/last_data_count_BR.json"

save_data_DropOff_Path = r"/home/inovasi/Downloads/car_drop_off/save_data/last_data_dropoff.json"



# rec_vidio_file_path = 'recording_20_20250123_132059.mp4'

rec_vidio_file_path = None





def write_log(file_log, message):

    os.makedirs(os.path.dirname(f'log/{file_log}'), exist_ok=True)

    with open(f'log/{file_log}', 'a') as log_file:

        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")



def send_screenshot(url, image_path, device_id):

    cv2.imwrite(image_path, ImageSS_Square if 'square' in image_path else ImageSS_Count)

    print(" /")

    print(image_path)



    print(url)



    headers = {

        "Authorization": authorization_token

    }

    files = {

        "file": open(image_path, "rb"),

    }

    data = {

        "id": device_id

    }

    try:

        response = requests.post(url, headers=headers, files=files, data=data)

        print(response.status_code)

        print(response.json())

    except socket.gaierror as e:

        print(f"Network error occurred while sending: {e}")

    except requests.exceptions.RequestException as e:

        print(f"Request failed: {e}")

    except Exception as e:

        print(f"An unexpected error occurred: {e}")



def send_video(url, video_path, device_id, schedule_id):

    print(url)



    headers = {

        "Authorization": authorization_token

    }

    files = {

        "file": open(video_path, "rb"),

    }

    data = {

        "id": device_id,

        "schedule_id": schedule_id

    }

    try:

        response = requests.post(url, headers=headers, files=files, data=data)

        print(response.status_code)

        print(response.json())

    except socket.gaierror as e:

        print(f"Network error occurred while sending: {e}")

    except requests.exceptions.RequestException as e:

        print(f"Request failed: {e}")

    except Exception as e:

        print(f"An unexpected error occurred: {e}")



def send_video_threaded(url, video_path, device_id, schedule_id):

    threading.Thread(target=send_video, args=(url, video_path, device_id, schedule_id)).start()



def update_counter(data_dict, prefix, counter_array, max_iteration):

    for key, value in data_dict.items():

        index = int(key.replace(prefix, ''))

        if index < max_iteration:

            counter_array[index] = value



def load_schedules():

    """Load recording schedules from file"""

    try:

        with open('dynamic/schedules.json', 'r') as f:

            return json.load(f)

    except FileNotFoundError:

        return []



def save_schedules(schedules):

    """Save recording schedules to file"""

    os.makedirs('dynamic', exist_ok=True)

    with open('dynamic/schedules.json', 'w') as f:

        json.dump(schedules, f, indent=2)





FlagRecord = False

save_schedule = None

duration = None

datetime_str = None

schedule_id_record = None

out = None

# UrlScreenshoot_Square

UrlSendVidioRecord = None



####################--MQTT--########################################--MQTT--########################################--MQTT--####################



FlagSendRowData = False

last_Write_Time_SendMqtt_DeviceInfo = datetime.now()

last_Write_Time_SendMqtt_Count = datetime.now()

imp_data = {}

target_datetime_str = None

Recording_Start_Time = None



class VideoCaptureThreading:

    def __init__(self, url):

        self.url = url  # Store URL for reconnection

        self.connect()

        self.stopped = False



    def connect(self):

        """Attempt to connect to the camera"""

        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)

        self.grabbed, self.frame = self.cap.read()

        if not self.grabbed:

            print("Camera tidak terdeteksi")

            return False

        return True



    def start(self):

        threading.Thread(target=self.update, args=()).start()

        return self



    def update(self):

        while not self.stopped:

            if not self.grabbed:

                print("Connection lost. Attempting to reconnect...")

                self.cap.release()

                time.sleep(1)  # Wait 1 second before reconnecting

                if self.connect():

                    print("Successfully reconnected to camera")

            else:

                self.grabbed, self.frame = self.cap.read()



    def read(self):

        return self.grabbed, self.frame



    def stop(self):

        self.stopped = True

        try:

            self.cap.release()

        except Exception as e:

            print(f"VideoCaptureThreading::stop - {e}")

            print("Restart by code")

    def get(self, propId):

        return self.cap.get(propId)

    

def send_device_info():

    new_cv_data = {

        "action": "new_carcamera",

        "data": {

            "id": Device_ID,

            "connection": "LAN"

        }

    }

    if client:

        try:

            client.publish("carcamera/publish", json.dumps(new_cv_data), qos=1)

            print("Camera Register request.")

        except Exception as e:

            print(f"Failed to send new computer vision MQTT message: {e}")



def send_device_status_online(timestamp):

    new_cv_data = {

        "action": "device_status",

        "data": {

            "id": Device_ID,

            "timestamp": timestamp

        }

    }

    if client:

        try:

            client.publish("carcamera/publish", json.dumps(new_cv_data), qos=1)

            # print("Camera Send Status Device")

        except Exception as e:

            print(f"Failed to send device_status MQTT message: {e}")



def send_device_camera_not_detect(timestamp):

    desc = f"Camera {Device_ID} is not available"

    new_cv_data = {

        "action": "alert",

        "data": {

            "id": Device_ID,

            "timestamp": timestamp,

            "description" : desc

        }

    }

    if client:

        try:

            client.publish("carcamera/publish", json.dumps(new_cv_data), qos=1)

            print("Send Alert Camera Not Detect")

        except Exception as e:

            print(f"Failed to send device_status MQTT message: {e}")





def on_publish(client, userdata, mid):

    print(f"Message {mid} published.")



def on_connect(client, userdata, flags, rc):

    if rc == 0:

        print("Connected to MQTT broker.")

        client.subscribe(f"carcamera/subscribe/{Device_ID}", qos=1)

        client.subscribe(f"carcamera/{Device_ID}/screenshoot", qos=1)

    else:

        print(f"Failed to connect with return code {rc}")



def on_message(client, userdata, message):

    print(f"Received message with QoS: {message.qos}")

    print(f"Message payload: {message.payload.decode()}")

    global FlagSendRowData, FlagSendImage_Square, FlagSendImage_Count, FlagSendImage_ConfigLine, UrlScreenshoot_Square, UrlScreenshoot_Count, UrlScreenshoot_ConfigLine, file_log, Recording_Duration, FlagRecording, Recording_Start_Time, target_datetime_str, schedules, schedule_exists, UrlScreenshoot_ConfigArea, FlagSendImage_ConfigArea, Dwelingtime_DropOff



    payload = json.loads(message.payload.decode())

    topic = message.topic



    if topic == f"carcamera/subscribe/{Device_ID}": 

        if payload.get("action") == "carcamera_registered":

            write_log(file_log, f"Camera registered: ID={payload['id']}, Connection={payload['connection']}, Name={payload['name']}") 

            print(f"Camera registered: ID={payload['id']}, Connection={payload['connection']}, Name={payload['name']}")

            FlagSendRowData = True

            with open('dynamic/DeviceRegist.txt', 'w') as f:

                f.write("True\n")



        elif payload.get("action") == "carcamera_delete":

            write_log(file_log, f"Camera deleted: ID={payload['id']}, Name={payload['name']}")

            print(f"Camera deleted: ID={payload['id']}, Name={payload['name']}")

            FlagSendRowData = False

            with open('dynamic/DeviceRegist.txt', 'w') as f:

                f.write("False\n")

        

        elif payload.get("action") == "config_line":

            write_log(file_log, f"Received config_line action with data: {payload['data']}")

            print(f"Received config_line action with data: {payload['data']}")

            with open('dynamic/LineValue.txt', 'w') as file:  # Open the file in write mode

                for line in payload['data']:

                    # Extract points from the new format

                    point1, point2 = line['points']

                    x1, y1 = point1

                    x2, y2 = point2

                    file.write(f"{int(x1)},{int(y1)} {int(x2)},{int(y2)}\n") 

            print(f"Url: {payload['url']}")

            UrlScreenshoot_ConfigLine = payload['url']

            time.sleep(3)

            FlagSendImage_ConfigLine = True 



        elif payload.get("action") == "config_area":

            temp_dwelingtime = []

            write_log(file_log, f"Received config_area action with data: {payload['data']}")

            print(f"Received config_area action with data: {payload['data']}")

            with open('dynamic/SquareValue.txt', 'w') as file:

                for area_number in payload['data']:

                    # Extract points from the nested array format

                    points = area_number['points']

                    # Convert points to tuple format and write to file

                    point_str = " ".join(f"({int(x)},{int(y)})" for [x, y] in points)

                    file.write(f"{point_str}\n")



                    dwelingtime = area_number['dwelingtime']

                    temp_dwelingtime.append(dwelingtime)



            print(f"temp_dwelingtime {temp_dwelingtime}")

            Dwelingtime_DropOff = temp_dwelingtime



            data_json_dwelingtime_area = {

                "dwelingtime" : temp_dwelingtime

            } 





            save_data_to_json_file(data_json_dwelingtime_area, dwelingtime_area_file_path)

            print(f"Url: {payload['url']}")

            UrlScreenshoot_ConfigArea = payload['url']

            time.sleep(3)

            FlagSendImage_ConfigArea = True

        



        elif payload.get("action") == "config_input":

            write_log(file_log, f"Received config_input in or out action with data: {payload['data']}")

            print(f"Received config_input action with data: {payload['data']}")

            with open(rb_file_path, 'w') as rb_file, \

                 open(br_file_path, 'w') as br_file:

                for line in payload['data']:

                    line_number = line['line_number']

                    # Write directly to files without using br_value and rb_value

                    br_file.write(f"{line_number}: {line['br']}\n")

                    rb_file.write(f"{line_number}: {line['rb']}\n")

                    print(f"Line {line_number}: BR={line['br']}, RB={line['rb']}")



        elif payload.get("action") == "record":

            schedules = load_schedules()



            new_schedule = {

                "schedule_id": payload["schedule_id"],

                "datetime": payload["datetime"],

                "duration": payload["duration"],

                "url": payload["url"]

            }



            schedule_exists = False

            for i, schedule in enumerate(schedules):

                if schedule["schedule_id"] == new_schedule["schedule_id"]:

                    schedules[i] = new_schedule  # Update existing schedule

                    schedule_exists = True

                    break



            if not schedule_exists:

                schedules.append(new_schedule)  # Add new schedule



            # Save updated schedules

            save_schedules(schedules)

            write_log(file_log, f"Added recording schedule: {new_schedule}")

            print(f"Added recording schedule: {new_schedule}")



        elif payload.get("action") == "update_record":

            schedules = load_schedules()



            new_schedule = {

                "schedule_id": payload["schedule_id"],

                "datetime": payload["datetime"],

                "duration": payload["duration"],

                "url": payload["url"]

            }



            schedule_exists = False

            for i, schedule in enumerate(schedules):

                if schedule["schedule_id"] == new_schedule["schedule_id"]:

                    schedules[i] = new_schedule  # Update existing schedule

                    schedule_exists = True

                    break



            if not schedule_exists:

                schedules.append(new_schedule)  # Add new schedule



            # Save updated schedules

            save_schedules(schedules)

            write_log(file_log, f"updated recording schedule: {new_schedule}")

            print(f"updated recording schedule: {new_schedule}")



        # elif payload.get("action") == "delete_record":

        #     schedules = load_schedules()



        #     del_schedule = {

        #         "schedule_id": payload["schedule_id"],

        #         "datetime": payload["datetime"],

        #         "duration": payload["duration"],

        #         "url": payload["url"]

        #     }



        #     schedules.remove(del_schedule)

        #     save_schedules(schedules)



    elif topic == f"carcamera/{Device_ID}/screenshoot": 



        if payload.get("action") == "screenshoot_area":

            write_log(file_log, f"Camera Screenshoot Heatmap: ID={payload['id']}, Url={payload['url']}")

            print(f"Camera Screenshoot: ID={payload['id']}, Url={payload['url']}")

            UrlScreenshoot_Square = payload['url']       

            time.sleep(1)

            FlagSendImage_Square = True



        elif payload.get("action") == "screenshoot_line":

            write_log(file_log, f"Camera Screenshoot Count: ID={payload['id']}, Url={payload['url']}")

            print(f"Camera Screenshoot Count: ID={payload['id']}, Url={payload['url']}")

            UrlScreenshoot_Count = payload['url']      

            time.sleep(1)

            FlagSendImage_Count = True



loop_running = False



def connect_to_mqtt(client, mqtt_broker, mqtt_port, mqtt_user, mqtt_pass, Device_ID, max_retries=10): 

    """

    Connect to MQTT broker with retry mechanism.

    """

    client.username_pw_set(mqtt_user, mqtt_pass)

    count_connect = 0



    while count_connect < max_retries:

        try:

            print(f"Attempting to connect to MQTT broker ({count_connect + 1}/{max_retries})...")

            client.connect(mqtt_broker, mqtt_port)

            print("Successfully connected to MQTT broker.")

            return True

        

        except (socket.gaierror, ConnectionRefusedError) as e:

            print(f"Connection failed: {e}. Retrying in 5 seconds...")

            write_log(file_log, "Connection failed to MQTT. Retrying in 5 seconds...")

            count_connect += 1

            time.sleep(5)



    print("Failed to connect after maximum retries.")

    return False



def reconnect_mqtt(client, mqtt_broker, mqtt_port, mqtt_user, mqtt_pass, Device_ID):

    """ 

    Handle MQTT reconnection in a separate thread. 

    """ 

    global loop_running 

    while True: 

        if not client.is_connected(): 

            print("MQTT client is not connected. Attempting to reconnect...") 

            if connect_to_mqtt(client, mqtt_broker, mqtt_port, mqtt_user, mqtt_pass, Device_ID): 

                print("Reconnected successfully!") 

                # Start the loop if it's not already running 

                if not loop_running: 

                    client.loop_start() 

                    loop_running = True 

            else: 

                print("Reconnection failed. Retrying...") 

        time.sleep(10) 

 

client = mqtt.Client() 

client.on_connect = on_connect 

client.on_message = on_message 

 

# Initial connection 

if connect_to_mqtt(client, mqtt_broker, mqtt_port, mqtt_user, mqtt_pass, Device_ID): 

    client.loop_start() 



    write_log(file_log, "Successfully connected to MQTT broker.")

    loop_running = True 

else: 

    print("Initial connection failed. Starting reconnect mechanism...") 

 

reconnect_thread = threading.Thread( 

    target=reconnect_mqtt, 

    args=(client, mqtt_broker, mqtt_port, mqtt_user, mqtt_pass, Device_ID), 

    daemon=True 

) 

reconnect_thread.start() 

 

####################--MQTT--########################################--MQTT--########################################--MQTT--#################### 





# model = YOLO("models/yolo11n.pt") 

# model.to("cuda") 



model_ori = YOLO("yolo11n.pt")

model_ori.export(format="ncnn")

model = YOLO("yolo11n_ncnn_model")



# url = "rtsp://inovasiadiwarna:IAWXGTN@2@192.168.248.174:554/Streaming/tracks/201?starttime=20241224t154800z&endtime=20241224t160000z"

# url = "rtsp://inovasiadiwarna:IAWXGTN1301@192.168.248.174:554/ISAPI/Streaming/Channels/401"

# cap = VideoCaptureThreading(url).start()

# video_path = "ch01_00000000300000000_20241129230624_20241129230712.mov" 

# video_path = "WhatsApp Video 2025-02-07 at 08.50.53_a9e8216a.mp4" 

# video_path = 0

# cap = cv2.VideoCapture(video_path)





url = "rtsp://admin:12Password@192.168.1.64:554/Streaming/channels/101"

cap = VideoCaptureThreading(url).start()



x1, y1 = None, None

x2, y2 = None, None

Last_Hour_ResetDataCrossingLine = None



MaxIteration = 5   

start_time = time.time()    

frame_count = 0 

fps = 0.0   



# DropOff_Value = 0 

DropOff_Value = [0] * MaxIteration 

Dwelingtime_DropOff = [0] * MaxIteration



person_counter_RB, person_counter_BR, square_points, SquareDuration, EntryTime = [[0] * MaxIteration for _ in range(5)] 

 

LastTime_CountSquare = defaultdict(lambda: defaultdict(lambda: None)) 

LastTime_CountDropOff = defaultdict(lambda: defaultdict(lambda: None)) 

# TimeArrayDropOff = defaultdict(lambda: defaultdict(lambda: None)) 



TimeArrayDropOff = defaultdict(lambda: defaultdict(int))



counted_persons_RB = [set() for _ in range(MaxIteration)]      

counted_persons_BR = [set() for _ in range(MaxIteration)]  

image_coordinates_list = [[] for _ in range(MaxIteration)]  



position_history = defaultdict(lambda: defaultdict(set))

current_position = defaultdict(lambda: defaultdict(lambda: None))



position_history_car = defaultdict(lambda: defaultdict(list))

current_position_car = defaultdict(lambda: defaultdict(lambda: None))



# flag_id_drop_off = [{} for _ in range(MaxIteration)]

flag_id_drop_off = defaultdict(lambda: defaultdict(bool)) 

flag_id_drop_off = defaultdict(lambda: defaultdict(bool))



active_track_ids, active_track_ids_before, executed_times_heatmap, executed_times_count = (set() for _ in range(4))

TimeArray, Last_Write_Times_CountTimePerson, image_coordinates, time_intervals_heatmap, time_intervals_count = [[] for _ in range(5)]

FlagPersonIntoSquare, x_positions, y_positions, last_two_positions = (defaultdict(list) for _ in range(4))

FlagSendImage_Square, FlagSendImage_Count, FlagSendImage_ConfigLine, FlagSendImage_ConfigArea,  FlagRecording = [False] * 5

UrlScreenshoot_Square, UrlScreenshoot_Count, UrlScreenshoot_ConfigLine, UrlScreenshoot_ConfigArea, Recording_Start_Time, Recording_Duration, last_day = [None] * 7

br_value_set_from_frontend, rb_value_set_from_frontend, Json_Count_Save_Data_BR, Json_Count_Save_Data_RB, Json_Heatmap_Save_Data,last_update_times = [{} for _ in range(6)]

In_Line, Out_Line, before_total_line_count = [0] * 3



Load_data_count_BR = load_data_from_json_file(save_data_BR_Path)

Load_data_count_RB = load_data_from_json_file(save_data_RB_Path)

Load_data_dropoff = load_data_from_json_file(save_data_DropOff_Path)

Load_data_dwelingtime = load_data_from_json_file(dwelingtime_area_file_path)



update_counter(Load_data_count_RB, 'RB', person_counter_RB, MaxIteration)

update_counter(Load_data_count_BR, 'BR', person_counter_BR, MaxIteration)



print(f"Load_data_dropoff{Load_data_dropoff}")

print(f"Load_data_dwelingtime{Load_data_dwelingtime}")



DropOff_Value = Load_data_dropoff['Dropoff_Value']

print(f"load {DropOff_Value}")



Dwelingtime_DropOff = Load_data_dwelingtime['dwelingtime']

print(f"Dwelingtime_DropOff{Dwelingtime_DropOff}")



print("person_counter_RB:", person_counter_RB)

print("person_counter_BR:", person_counter_BR)



TIMEOUT_THRESHOLD_DISAPPEARED_DROP_OFF = 5 



# for hour_heatmap in range(24): 

#     for minute_heatmap in [0, 15, 30, 45]: 

#         time_intervals_heatmap.append(f"{hour_heatmap:02d}:{minute_heatmap:02d}")

# time_intervals_heatmap.append("24:00")  



for hour_count in range(24): 

    # for minute_count in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59]: 

    for minute_count in [59]:     

        time_intervals_count.append(f"{hour_count:02d}:{minute_count:02d}")

time_intervals_count.append("24:00")  



try:

    with open('dynamic/DeviceRegist.txt', 'r') as f:

        content = f.read().strip()

        FlagSendRowData = True if content == "True" else False

except FileNotFoundError:

    FlagSendRowData = False 





crop_coordinates = [(180,50), (440,50), (180,230), (440,230)]

x_coords = [p[0] for p in crop_coordinates]

y_coords = [p[1] for p in crop_coordinates]

crop_x1, crop_x2 = min(x_coords), max(x_coords)

crop_y1, crop_y2 = min(y_coords), max(y_coords)





while True:

    success, Frame = cap.read()

    if not success:

        print("Frame tidak terdeteksi")

        current_time = datetime.now()

        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")

        send_device_camera_not_detect(timestamp)

        cap = VideoCaptureThreading(url).start()

        time.sleep(1)  # Wait 1 second before trying next frame

        continue

        





    Frame = cv2.resize(Frame, (640, 480))

    Frame = Frame[crop_y1:crop_y2, crop_x1:crop_x2]

    ImageSS_Square = Frame.copy()

    ImageSS_Count = Frame.copy()

    # ImageSS_Square = cv2.resize(ImageSS_Square, (640, 480))

    # ImageSS_Count = cv2.resize(ImageSS_Count, (640, 480))



    (H, W) = Frame.shape[:2]



    frame_count += 1

    current_time = time.time()

    elapsed_time = current_time - start_time

    

    if elapsed_time >= 1.0: 

        fps = frame_count / elapsed_time 

        frame_count = 0 

        start_time = current_time 



    cv2.putText(Frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    square_points = load_square_points("dynamic/SquareValue.txt", MaxIteration)



    # print(Dwelingtime_DropOff)



    try:

        with open(br_file_path, 'r') as br_file:

            for line in br_file:

                line_number, value = line.strip().split(': ')

                br_value_set_from_frontend[int(line_number)-1] = value

    except FileNotFoundError:

        print("BR_Value.txt not found.")



    try:

        with open(rb_file_path, 'r') as rb_file:

            for line in rb_file:

                line_number, value = line.strip().split(': ')

                rb_value_set_from_frontend[int(line_number)-1] = value

    except FileNotFoundError:

        print("RB_Value.txt not found.")



    # print(DropOff_Value)



    # DropOff_Value = [9,9] #-------------------dummy-------------------dummy-------------------dummy-------------------dummy-------------------dummy-------------------dummy

    for i, value in enumerate(DropOff_Value, start=1):

        if value == 0:

            continue

        imp_data[str(i)] = value



    # print(imp_data)

    current_day = datetime.now().day  



    if current_day != last_day:  

        # executed_times_heatmap.clear()  

        executed_times_count.clear()

        last_day = current_day  



    current_time = datetime.now().strftime("%H:%M")



    try:

        with open(rb_file_path, 'r') as rb_file:

            TotalLineValue = len(rb_file.readlines())

    except FileNotFoundError:

        print("RB_Value.txt not found.")

        TotalLineValue = 0  



    if TotalLineValue != 0:

        #save value RB. BR rach i

        for i in range(TotalLineValue):

            Json_Count_Save_Data_RB[f"RB{i}"] = person_counter_RB[i]

            Json_Count_Save_Data_BR[f"BR{i}"] = person_counter_BR[i]



        save_data_to_json_file(Json_Count_Save_Data_BR, save_data_BR_Path)

        save_data_to_json_file(Json_Count_Save_Data_RB, save_data_RB_Path)



        for current_time_count in time_intervals_count: 



            

            if current_time == current_time_count and current_time_count not in executed_times_count:

                executed_times_count.add(current_time_count)  

                print(TotalLineValue)

                print(br_value_set_from_frontend)

                print(rb_value_set_from_frontend)

                print("---")

            

                

                for i in range(TotalLineValue):  

                    if i in br_value_set_from_frontend:  

                        if br_value_set_from_frontend[i] == "in":  

                            In_Line += person_counter_BR[i]

                        elif br_value_set_from_frontend[i] == "out":  

                            Out_Line += person_counter_BR[i]



                    if i in rb_value_set_from_frontend:  

                        if rb_value_set_from_frontend[i] == "in":  

                            In_Line += person_counter_RB[i]

                        elif rb_value_set_from_frontend[i] == "out":  

                            Out_Line += person_counter_RB[i]



                print("in-out")

                print(In_Line)

                # In_Line = 9 #-------------------dummy-------------------dummy-------------------dummy-------------------dummy-------------------dummy-------------------dummy

                # Out_Line = 9 #-------------------dummy-------------------dummy-------------------dummy-------------------dummy-------------------dummy-------------------dummy

                print(Out_Line)



                write_log(file_log, f"in {In_Line} - out {Out_Line}.")

                write_log(file_log, f"person_counter_RB {person_counter_RB}.")

                write_log(file_log, f"person_counter_BR {person_counter_BR}.")

                print(FlagSendRowData)

                                    

                if FlagSendRowData:

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    payloadDevice = {

                        "action": "send_data",

                        "data": {

                            "id": Device_ID,

                            "timestamp": timestamp,

                            "in": In_Line,

                            "out": Out_Line

                        }

                    }

                    payload_jsonDevice = json.dumps(payloadDevice)

                    resultDevice = client.publish(f"carcamera/publish", payload_jsonDevice, qos=1) 

                    write_log(file_log, f"dropoff value {imp_data}.")



                    payloadDevice = {

                        "action": "send_data_dropoff",

                        "data": {

                            "id": Device_ID,

                            "timestamp": timestamp,

                            "imp": imp_data

                        }

                    }

                    payload_jsonDevice = json.dumps(payloadDevice)

                    resultDevice = client.publish(f"carcamera/publish", payload_jsonDevice, qos=1) 



                    if resultDevice.rc == mqtt.MQTT_ERR_SUCCESS:

                        print("Count Data sent successfully.")

                    else:

                        print("Failed to send carcamera data.")   



                In_Line = 0 

                Out_Line = 0 

                person_counter_RB = [0] * MaxIteration    

                person_counter_BR = [0] * MaxIteration  

                DropOff_Value = [0] * MaxIteration  

                imp_data = {}

                clear_json_file(save_data_BR_Path)

                clear_json_file(save_data_RB_Path)

                clear_json_file(save_data_DropOff_Path)

                break



    image_coordinates_list = [[] for _ in range(MaxIteration)]



    with open('dynamic/LineValue.txt', 'r') as file:

        lines = file.readlines()  

        for i, line in enumerate(lines):

            if i >= MaxIteration: 

                break

            coord_strings = line.strip().split(' ')

            for coord_string in coord_strings:

                x, y = map(int, coord_string.split(','))

                image_coordinates_list[i].append((x, y))



    # results = model.track(Frame, persist=True, classes=[0])  



    with open('dynamic/LineValue.txt', 'r') as file:

        num_lines = len(file.readlines())

        total_line_count = num_lines

        num_lines = min(num_lines, MaxIteration)

    if total_line_count != before_total_line_count:

        for i in range(MaxIteration):

            for track_id in active_track_ids:

                position_history[i][track_id] = []

                

        before_total_line_count = total_line_count



    active_track_ids.clear() 



    # results = model.track(Frame, persist=True, classes=[2], device="cuda")

    results = model.track(Frame, persist=True, classes=[2,5,7])



    m_list, c_list = draw_line_and_regions(Frame, image_coordinates_list)



    draw_line_and_regions(ImageSS_Count, image_coordinates_list)



    if results and len(results) > 0:

        for r in results:

            boxes = r.boxes

            for box in boxes:

                x1, y1, x2, y2 = box.xyxy[0]

                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                conf = float(box.conf)

                cls = int(box.cls)

                track_id = int(box.id) if box.id is not None else None



                if track_id is not None and conf > 0.50:

                    active_track_ids.add(track_id) 



                    centroid = ((x1 + x2) // 2, (y1 + y2) // 2)

                    class_name = model.names[cls]

                    text_class_prob = f"{class_name}: {conf:.2f}"



                    

                    x_positions[track_id].append(centroid[0])

                    y_positions[track_id].append(centroid[1])



                    cv2.circle(Frame, centroid, 4, (0, 0, 255), -1)



                    cv2.putText(Frame, f"ID: {track_id}", (centroid[0], centroid[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

                    cv2.putText(Frame, f"{text_class_prob}", (centroid[0], centroid[1] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

                    

                    while len(TimeArray) <= track_id:

                        TimeArray.append(0)

                        Last_Write_Times_CountTimePerson.append(None)



                    if len(y_positions[track_id]) >= 2:     

                        for i in range(MaxIteration):       



                            if centroid[1] >= (m_list[i] * centroid[0] + c_list[i]):

                                current_position[i][track_id] = "red"

                            elif centroid[1] <= (m_list[i] * centroid[0] + c_list[i]):

                                current_position[i][track_id] = "blue"



                            if not position_history[i][track_id] or position_history[i][track_id][-1] != current_position[i][track_id]:

                                # Change from set to list

                                position_history[i][track_id] = list(position_history[i][track_id])  

                                position_history[i][track_id].append(current_position[i][track_id])



                            if len(position_history[i][track_id]) >= 2:  



                                if track_id not in counted_persons_RB and track_id not in counted_persons_BR:

                                    # print(f"ID {track_id} - {position_history[i][track_id]}")



                                    if "red" in position_history[i][track_id] and "blue" in position_history[i][track_id] and position_history[i][track_id].index("red") < position_history[i][track_id].index("blue"):

                                        person_counter_RB[i] += 0

                                        counted_persons_RB[i].add(track_id) 

                                        # person_counter_BR[i] += 1

                                        # print(f"{person_counter_BR}{datetime.now() }") 

                                        # counted_persons_BR[i].add(track_id) 



                                    elif "blue" in position_history[i][track_id] and "red" in position_history[i][track_id] and position_history[i][track_id].index("blue") < position_history[i][track_id].index("red"):

                                        person_counter_BR[i] += 1 

                                        counted_persons_BR[i].add(track_id) 

                                        # person_counter_RB[i] += 1

                                        print(f"{person_counter_BR}{datetime.now()}") 

                                        # counted_persons_RB[i].add(track_id) 



                            if (track_id in counted_persons_RB[i] or track_id in counted_persons_BR[i]) and len(position_history[i][track_id]) >= 2 and (position_history[i][track_id][-2:] == ["red", "blue"] or position_history[i][track_id][-2:] == ["blue", "red"]):

                                if track_id in counted_persons_RB[i]: 

                                    counted_persons_RB[i].remove(track_id)   

                                if track_id in counted_persons_BR[i]: 

                                    counted_persons_BR[i].remove(track_id)  

                                position_history[i][track_id] = []                         



                            if FlagSendRowData:  

                                if square_points[i] and len(square_points[i]) == 4: 

                                    result = is_point_in_square(square_points[i], centroid) 

                                    current_time = datetime.now() 



                                    if result:

                                        current_position_car[i][track_id] = "out"

                                    elif not result:

                                        current_position_car[i][track_id] = "in"

                                        # if position_history_car[i][track_id][-2:] == ["in", "out"] and flag_id_drop_off[i][track_id] == True :

                                        if position_history_car[i][track_id][-2:] == ["in", "out"] or flag_id_drop_off[i][track_id] == True :

                                            position_history_car[i][track_id] = []

                                            TimeArrayDropOff[i][track_id] = 0

                                            flag_id_drop_off[i][track_id] = False



                                        elif position_history_car[i][track_id][-2:] == ["out", "in"] :

                                            position_history_car[i][track_id] = []

                                            flag_id_drop_off[i][track_id] = False

                                    

                                    if not position_history_car[i][track_id] or position_history_car[i][track_id][-1] != current_position_car[i][track_id]:

                                        position_history_car[i][track_id].append(current_position_car[i][track_id])



                                    if len(position_history_car[i][track_id]) >= 2:

                                        if (LastTime_CountDropOff[i][track_id] is None or (current_time - LastTime_CountDropOff[i][track_id]).total_seconds() >= 1) and position_history_car[i][track_id][-2:] == ["in", "out"]:

                                            TimeArrayDropOff[i][track_id] += 1

                                            LastTime_CountDropOff[i][track_id] = current_time             

                           

                                            if TimeArrayDropOff[i][track_id] == Dwelingtime_DropOff[i] and flag_id_drop_off[i][track_id] == False:

                                                flag_id_drop_off[i][track_id] = True

                                                DropOff_Value[i] += 1 

                                                                 

    data_json_dropoff = {

        "Dropoff_Value": DropOff_Value

    }



    save_data_to_json_file(data_json_dropoff, save_data_DropOff_Path)



    cv2.putText(Frame, f"Drop OFF Car: {DropOff_Value}", (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                            

                                        

    # with open('dynamic/LineValue.txt', 'r') as file:

    #     num_lines = len(file.readlines())

    #     total_line_count = num_lines

    #     num_lines = min(num_lines, MaxIteration)



    draw_square(Frame, square_points, (0, 255, 0), MaxIteration)

    draw_square(ImageSS_Square, square_points, (0, 255, 0), MaxIteration)

        

    for i in range(num_lines):

        cv2.putText(Frame, f"Line {i+1} R-B: {person_counter_RB[i]}", (10, 120 + i*40), 

                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        cv2.putText(Frame, f"Line {i+1} B-R: {person_counter_BR[i]}", (10, 140 + i*40), 

                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        

    # cv2.putText(Frame, f"Active track_ids: {active_track_ids}", (10, 50), 

    #             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)



    current_time = time.time()



    if FlagSendRowData == False:

        SquareDuration = [0] * MaxIteration

        current_time = datetime.now()

        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")

        if (current_time - last_Write_Time_SendMqtt_DeviceInfo).total_seconds() > 1:

            send_device_info()

            # print("Send New Camera")

            last_Write_Time_SendMqtt_DeviceInfo = current_time



    elif FlagSendRowData == True:

        current_time = datetime.now()

        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")

        if (current_time - last_Write_Time_SendMqtt_DeviceInfo).total_seconds() > 60:

            send_device_status_online(timestamp)

            # print("Send Status Online")

            last_Write_Time_SendMqtt_DeviceInfo = current_time



    cv2.imshow("Image", Frame)



    if FlagSendImage_Square:

        send_screenshot(UrlScreenshoot_Square, square_ss_file_path, Device_ID)

        FlagSendImage_Square = False



    if FlagSendImage_Count:

        send_screenshot(UrlScreenshoot_Count, count_ss_file_path, Device_ID)

        print(count_ss_file_path)

        FlagSendImage_Count = False



    if FlagSendImage_ConfigLine:

        send_screenshot(UrlScreenshoot_ConfigLine, count_ss_file_path, Device_ID)

        FlagSendImage_ConfigLine = False



    if FlagSendImage_ConfigArea:

        send_screenshot(UrlScreenshoot_ConfigArea, square_ss_file_path, Device_ID)

        FlagSendImage_ConfigArea = False

        

    key = cv2.waitKey(1) & 0xFF



    current_datetime = datetime.now()

    schedules = load_schedules()

    tolerance = timedelta(seconds=1)



    for schedule in schedules[:]:  # Create a copy to iterate while modifying

        schedule_time = datetime.strptime(schedule["datetime"], '%Y-%m-%d %H:%M:%S')

        

        if schedule_time - tolerance <= current_datetime <= schedule_time + tolerance:

            print(f"Starting scheduled recording {schedule['schedule_id']}")

            write_log(file_log, f"Starting scheduled recording {schedule['schedule_id']}")



            # Save data needed

            duration = schedule["duration"]

            datetime_str = schedule["datetime"]

            UrlSendVidioRecord = schedule["url"]

            schedule_id_record = schedule["schedule_id"]

            print(UrlSendVidioRecord)

            print(schedule_id_record)



            schedule_time = datetime.strptime(schedule["datetime"], '%Y-%m-%d %H:%M:%S')

            duration = schedule["duration"]

            save_schedule = schedule_time + timedelta(seconds=duration) 



            schedules.remove(schedule) 

            save_schedules(schedules)



            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            valid_datetime_str = datetime_str.replace(":", "-")

            filename = f"{schedule_id_record}_{valid_datetime_str}.mp4"

            out = cv2.VideoWriter(filename, fourcc, 8.0, (640, 480))

            print(out)



    try:



        if save_schedule: 

            if current_datetime < save_schedule:

                FlagRecord = True

                out.write(Frame)

            elif current_datetime > save_schedule:

                save_schedule = None

                FlagRecord = False

                datetime_str = None

                duration = None

                out.release()

                

                rec_vidio_file_path = filename



                if not out.isOpened():

                    time.sleep(1)

                    # send_video(UrlSendVidioRecord, rec_vidio_file_path, Device_ID, schedule_id_record)

                    send_video_threaded(UrlSendVidioRecord, rec_vidio_file_path, Device_ID, schedule_id_record)

                    print("done")



                out = None

                rec_vidio_file_path = None



        else:

            pass

    except Exception as e:

        print(f"An error occurred: {e}")



    if key == ord('q'):

        break



cap.release()

cv2.destroyAllWindows()

client.loop_stop()

client.disconnect()