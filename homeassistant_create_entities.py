# This script is designed to make Optolink-Splitter datapoints available in Home Assistant by publishing them via MQTT. 
# The configuration is defined in the homeassistant_entities.json file.
#
# MQTT publishing in Homeassistant:
# --------------------------------------------------
#  Home Assistance MQTT discovery description: https://www.home-assistant.io/integrations/mqtt#mqtt-discovery
#   Topic: 
#    {mqtt_ha_discovery_prefix}/[component (e.g. sensor)]/{mqtt_ha_node_id} (OPTIONAL}/{mqtt_optolink_base_topic}/config
#   Value:
#    {"object_id": "{dp_prefix}{name}", "unique_id": "{dp_prefix}[name(converted)]", "device": [...] , "availability_topic": "{mqtt_optolink_base_topic}/LWT", "state_topic": "{mqtt_optolink_base_topic}/[name(converted)]", "name": "[name]", [...]}
#
# homeassistant_entities.json file values
# --------------------------------------------------
#  "mqtt_optolink_base_topic": Topic read from the optolink-splitter. The value must end with a "/", e.g. "vitocal/".
#  "mqtt_ha_discovery_prefix": Topic Home Assistant listens to for MQTT discovery. Home Assistants default is "homeassistant".
#  "mqtt_ha_node_id" (optional): Not necessarily needed by Home Assistant. Can be used to structure the MQTT topic, see the example of publishing above. The value must end with a "/" or be empty if not used. 
#  "dp_prefix": Added to "object_id" and "unique_id" in the value of the entity configuration. The value should end with an "_", e.g., "vitocal_".

import json
import re
import time
import sys
import paho.mqtt.client as paho
import settings_ini

# Global MQTT Client
mqtt_client = None

def connect_mqtt():
    # Connects to the MQTT broker using credentials from settings_ini.py
    global mqtt_client

    if mqtt_client is None:
        print(f"\nInitializing MQTT Client for Home Assistant entity creation...")
        mqtt_client = paho.Client(paho.CallbackAPIVersion.VERSION2, "ha_entities_" + str(int(time.time()*1000)))  # Unique ID

    if mqtt_client.is_connected():
        print(f" MQTT client is already connected. Skipping reconnection.")
        return

    try:
        mqtt_credentials = settings_ini.mqtt.split(':')
        if len(mqtt_credentials) != 2:
            raise ValueError(" MQTT settings must be in the format 'host:port'")
        MQTT_BROKER, MQTT_PORT = mqtt_credentials[0], int(mqtt_credentials[1])

        # Extract username and password
        mqtt_user_pass = settings_ini.mqtt_user
        if mqtt_user_pass and mqtt_user_pass.lower() != "none":
            mqtt_user, mqtt_password = mqtt_user_pass.split(":")
            mqtt_client.username_pw_set(mqtt_user, mqtt_password)
            print(f" Connecting as {mqtt_user} to MQTT broker {MQTT_BROKER} on port {MQTT_PORT} for Home Assistant entity creation...")
        else:
            print(f" Connecting anonymously to MQTT broker {MQTT_BROKER} on port {MQTT_PORT} for Home Assistant entity creation...")

        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print(f" MQTT connected successfully.")
        
    except Exception as e:
        print(f" Error connecting to MQTT broker: {e}")
        return False

def verify_mqtt_optolink_lwt(timeout=10):
    # Checks the availability of the Optolink-Splitter by subscribing to the Last Will and Testament (LWT) topic.
    with open("homeassistant_entities.json") as json_file:
        ha_ent = json.load(json_file)

    mqtt_optolink_base_topic = ha_ent.get("mqtt_optolink_base_topic", "")
    LWT_TOPIC = f"{mqtt_optolink_base_topic}LWT"

    try:
        mqtt_credentials = settings_ini.mqtt.split(":")
        if len(mqtt_credentials) != 2:
            raise ValueError("MQTT settings must be in the format 'host:port'")
        MQTT_BROKER, MQTT_PORT = mqtt_credentials[0], int(mqtt_credentials[1])
    except Exception as e:
        print(f"Error in MQTT settings: {e}")
        return False

    def on_message(client, userdata, message):
        if message.payload.decode() == "online":
            print(f" MQTT is connected. Optolink-Splitter LWT reports 'online'. Publishing entities now...\n")
            client.loop_stop()
            client.disconnect()
            userdata["status"] = True

    mqtt_lwt_client = paho.Client(paho.CallbackAPIVersion.VERSION2)
    mqtt_lwt_client.user_data_set({"status": False})
    
    print(f"Subscribing to {LWT_TOPIC} to check Optolink-Splitter state and MQTT connection.")
    mqtt_lwt_client.on_message = on_message
    mqtt_lwt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
    mqtt_lwt_client.subscribe(LWT_TOPIC)
    mqtt_lwt_client.loop_start()

    start_time = time.time()
    while time.time() - start_time < timeout:
        if mqtt_lwt_client._userdata["status"]:
            return True
        time.sleep(3)

    print(f" Error: Optolink-Splitter LWT did not report 'online'. Ensure that optolinkvs2_switch.py (or the corresponding service) is running and retry.")
    mqtt_lwt_client.loop_stop()
    mqtt_lwt_client.disconnect()
    return False

def publish_homeassistant_entities():
    # Reads entity definitions from homeassistant_entities.json and publishes MQTT discovery messages to Home Assistant.
    with open("homeassistant_entities.json") as json_file:
        ha_ent = json.load(json_file)

    if "datapoints" not in ha_ent:
        print("Error: 'datapoints' missing in homeassistant_entities.json")
        return

    # Ensure MQTT connection is established before publishing
    connect_mqtt()

    mqtt_optolink_base_topic = ha_ent.get("mqtt_optolink_base_topic", "")
    mqtt_ha_discovery_prefix = ha_ent.get("mqtt_ha_discovery_prefix", "")
    mqtt_ha_node_id = ha_ent.get("mqtt_ha_node_id", "")
    dp_prefix = ha_ent.get("dp_prefix", "")

    print(f"\nPrefix information \n  mqtt_optolink_base_topic: {mqtt_optolink_base_topic} \n  mqtt_ha_discovery_prefix: {mqtt_ha_discovery_prefix} \n  mqtt_ha_node_id: {mqtt_ha_node_id} \n  dp_prefix: {dp_prefix}")

    print("\nAll generated IDs from Entities")
    for entity in ha_ent["datapoints"]:
        entity_id = re.sub(r"[^0-9a-zA-Z]+", "_", entity["name"]).lower()
        print(f"  ID: {entity_id} / Entity: {entity['name']}")
    print("\n")

    # Check if Optolink-Splitter is online
    if not verify_mqtt_optolink_lwt():
        print("WARNING: Optolink-Splitter is not online. Proceeding without publishing.")
        return

    for entity in ha_ent["datapoints"]:
        entity_id = re.sub(r"[^0-9a-zA-Z]+", "_", entity["name"]).lower()
        config = {
            "object_id": ha_ent["dp_prefix"] + entity_id,
            "unique_id": ha_ent["dp_prefix"] + entity_id,
            "device": ha_ent["device"],
            "availability_topic": ha_ent['mqtt_optolink_base_topic'] + "LWT"
        }

        if entity["domain"] != "climate":
            config["state_topic"] = ha_ent["mqtt_optolink_base_topic"] + entity_id

        for key, value in entity.items():
            if key != "domain":
                if key.endswith("_topic"):
                    config[key] = ha_ent["mqtt_optolink_base_topic"] + value
                else:
                    config[key] = value

        mqtt_client.publish(
            f"{mqtt_ha_discovery_prefix}/{entity['domain']}/{ha_ent['mqtt_ha_node_id']}{entity_id}/config",
            json.dumps(config),
            retain=True,
        )
        time.sleep(0.5) # Processing time for Home Assistant Discovery
                
        # The following printouts are for debugging of the published discovery messages. Please feel free to comment out.
        print(f"Processed entity: {entity['name']}")
        print(f"   {mqtt_ha_discovery_prefix}/{entity['domain']}/{ha_ent['mqtt_ha_node_id']}{id}/config")
        print(json.dumps(config) + "\n")

if __name__ == "__main__":
    print("\nStarting Home Assistant Entity Creation...\n")
    publish_homeassistant_entities()
