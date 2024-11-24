import time
from datetime import datetime

import mqtt_util
import optolinkvs2
import settings_ini
import utils


# datapoint addrs
#addr_heattoday = 0x9000
addr_heatprevday = 0x9004
#addr_dhwtoday = 0x9134
addr_dhwprevday = 0x9138


last_hour = 25

def do_daycount(ser):
    global last_hour

    #print("do_daycount called")
    now = datetime.now()
    if(last_hour == now.hour):
        return

    #print("do_daycount H1")

    if(mqtt_util.mqtt_client):
        if(last_hour > now.hour):
            # new day or firt time
            #print("do_daycount H2", addr_heatprevday)
            buff = optolinkvs2.read_datapoint(addr_heatprevday, 4, ser)
            mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/dailyHeat", utils.bytesval(buff))
            time.sleep(0.1)
            #print("do_daycount H2", addr_dhwprevday)
            buff = optolinkvs2.read_datapoint(addr_dhwprevday, 4, ser)
            mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/dailyDhw", utils.bytesval(buff))
            time.sleep(0.1)
        #     mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/GasHeatToday", 0)
        #     mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/GasDhwToday", 0)
        # else:
        #     buff = optolinkvs2.read_datapoint(addr_heattoday, 4, ser)
        #     mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/GasHeatToday", utils.bytesval(buff))
        #     time.sleep(0.1)
        #     buff = optolinkvs2.read_datapoint(addr_dhwtoday, 4, ser)
        #     mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/GasDhwToday", utils.bytesval(buff))
        #     time.sleep(0.1) 
        last_hour = now.hour

