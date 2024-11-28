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


last_hour = -1
do_publ = False


def do_daycount(ser):
    global last_hour
    global do_publ

    #print("do_daycount called")
    now = datetime.now()
    if(last_hour > now.hour):
        # new day or firt time
        do_publ = True

    last_hour = now.hour
    
    if(do_publ and now.hour == 1 and now.minute == 30):
        alldone = False 
        if(mqtt_util.mqtt_client):
            #print("do_daycount H2", addr_heatprevday)
            rcode,addr,buff = optolinkvs2.read_datapoint_ext(addr_heatprevday, 4, ser)
            print(rcode, buff)
            if(rcode == 1):
                val = float(utils.bytesval(buff))
                mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/dailyHeat", val)
                print("published", settings_ini.mqtt_topic + "/dailyHeat", f"{val:.1f}")
                alldone = True
            time.sleep(0.1)
            #print("do_daycount H2", addr_dhwprevday)
            rcode,addr,buff = optolinkvs2.read_datapoint_ext(addr_dhwprevday, 4, ser)
            if(rcode == 1):
                val = float(utils.bytesval(buff))
                mqtt_util.mqtt_client.publish(settings_ini.mqtt_topic + "/dailyDhw",  f"{val:.1f}")
                alldone &= True
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
        do_publ = not alldone

