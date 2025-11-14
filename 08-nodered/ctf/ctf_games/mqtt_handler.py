import paho.mqtt.client as mqtt
import json 
import logging 
import time
import socket

logger = logging.getLogger(__name__)

class MQTTHandler:
    def __init__(self, broker, port, topic_base):
        self.broker = broker
        self.port = port
        self.topic_base = topic_base

        ## Creating MQTT Client with clean session
        self.client = mqtt.Client(clean_session = True)

        #Set up event callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish

        # Connection state tracking
        self.is_connected = False
        self.connection_attempts = 0

        # Message handlers - MAIN.PY
        self.on_challenge_1 = None
        self.on_challenge_2 = None
        self.on_challenge_3 = None
        self.on_challenge_4 = None

        logger.info("MQTT Handler initizalized for broker: " + broker + ":" + str(port))

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0 :
            self.is_connected = True
            self.connection_attempts = 0
            logger.info("MQTT connection established to " + self.broker + ":" + str(self.port))
            logger.info("Connection flags: " + str(flags))
        else:
            self.is_connected = False

            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable", 
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            error_msg = error_messages.get(rc, "Unknown error code: " + str(rc))
            logger.error("MQTT connection failed: " + error_msg)

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            message = msg.payload.decode('utf-8')

            logger.info("MQTT message received - Topic: " + topic + " | Size: " + str(len(message)) + " bytes")
            logger.debug("Message content: " + message)

            ##Parse topic to extract student ID and challenge type
            topic_parts = topic.split('/')
            if len(topic_parts) >= 4 and topic_parts[0] == 'silentfrikandel':
                student_id = topic_parts[1]
                challenge = topic_parts[2]
                action = topic_parts[3]
    
                if not self._validate_student_id(student_id):
                    logger.warning("Invalid student ID format:" + student_id)
                    return
    
                logger.info("Parsed - Challenge: " + challenge + " | Student: " + student_id)
    
                if challenge == 'challenge1' and action == 'flag' and self.on_challenge_1:
                    self.on_challenge_1(topic, message, student_id)
                elif challenge == 'challenge2' and action == 'flag' and self.on_challenge_2:
                    self.on_challenge_2(topic, message, student_id)
                elif challenge == 'challenge3' and action == 'flag' and self.on_challenge_3:
                    self.on_challenge_3(topic, message, student_id)
                elif challenge == 'challenge4' and action == 'flag' and self.on_challenge_4:
                    self.on_challenge_4(topic, message, student_id)
                else:
                    logger.warning("No handler for topic: " + topic)

            else:
                logger.warning("Invalid topic format: " + topic)
                
        except UnicodeDecodeError as e:
            logger.error("Failed to decode MQTT message payload: " + str(e))
        except Exception as e:
            logger.error("Error processing MQTT message from topic " + msg.topic + ": " + str(e))
    
    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection (code: " + str(rc) + ")")
        else:
            logger.info("Clean MQTT disconnection")
    
    def _validate_student_id(self, student_id):
        if len(student_id) < 3 or len(student_id) > 20:
            return False
        
        if not student_id.replace('_', '').isalnum():
            return False
        
        forbidden_patterns = ['admin', 'root', 'system', 'test', '$', '#', '+']
        student_id_lower = student_id.lower()
        for pattern in forbidden_patterns:
            if pattern in student_id_lower:
                return False
        
        return True
    
    def connect(self, retry_attempts=5, retry_delay=3):
        logger.info("Initiating MQTT connection to " + self.broker + ":" + str(self.port))
        
        for attempt in range(retry_attempts):
            self.connection_attempts = attempt + 1
            
            try:
                logger.info("MQTT connection attempt " + str(attempt + 1) + "/" + str(retry_attempts))
                
                self.client.max_inflight_messages_set(20)
                self.client.max_queued_messages_set(0)
                
                connect_result = self.client.connect(self.broker, self.port, keepalive=60)
                
                if connect_result == mqtt.MQTT_ERR_SUCCESS:
                    self.client.loop_start()
                    
                    timeout_seconds = 10
                    while not self.is_connected and timeout_seconds > 0:
                        time.sleep(0.5)
                        timeout_seconds -= 0.5
                    
                    if self.is_connected:
                        logger.info("MQTT connection successful!")
                        return True
                    else:
                        logger.warning("MQTT connection timeout on attempt " + str(attempt + 1))
                        self.client.loop_stop()
                else:
                    logger.error("MQTT connect() failed with result code: " + str(connect_result))
                    
            except Exception as e:
                logger.error("MQTT connection attempt " + str(attempt + 1) + " failed: " + str(e))
            
            if attempt < retry_attempts - 1:
                logger.info("Retrying MQTT connection in " + str(retry_delay) + " seconds...")
                time.sleep(retry_delay)
        
        logger.error("All MQTT connection attempts failed")
        return False
    
    def subscribe(self, topic, qos=0):
        if not self.is_connected:
            logger.error("Cannot subscribe to " + topic + " - not connected to MQTT broker")
            return False
        
        try:
            logger.info("Subscribing to MQTT topic: " + topic + " (QoS: " + str(qos) + ")")
            result, mid = self.client.subscribe(topic, qos)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info("MQTT subscription request sent successfully for: " + topic)
                return True
            else:
                logger.error("MQTT subscription failed for " + topic + " - Error code: " + str(result))
                return False
                
        except Exception as e:
            logger.error("Error subscribing to MQTT topic " + topic + ": " + str(e))
            return False
    
    def publish(self, topic, message, qos=0, retain=False):
        if not self.is_connected:
            logger.error("Cannot publish to " + topic + " - not connected to MQTT broker")
            return False
        
        try:
            if len(message) > 268435455:
                logger.error("Message too large for MQTT publish: " + str(len(message)) + " bytes")
                return False
            
            result = self.client.publish(topic, message, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("MQTT message published successfully to: " + topic)
                return True
            else:
                logger.error("MQTT publish failed to " + topic + " - Error code: " + str(result.rc))
                return False
                
        except Exception as e:
            logger.error("Error publishing MQTT message to " + topic + ": " + str(e))
            return False
    
    def disconnect(self):
        if self.is_connected:
            logger.info("Disconnecting from MQTT broker...")
            try:
                self.client.loop_stop()
                self.client.disconnect()
                self.is_connected = False
                logger.info("MQTT disconnection complete")
            except Exception as e:
                logger.error("Error during MQTT disconnection: " + str(e))
        else:
            logger.info("Already disconnected from MQTT broker")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when MQTT subscription confirmed"""
        logger.info("MQTT subscription confirmed - Message ID: " + str(mid) + " | QoS granted: " + str(granted_qos))

    def _on_publish(self, client, userdata, mid):
        """Callback when MQTT message publish is confirmed"""
        logger.debug("MQTT publish confirmed - Message ID: " + str(mid))