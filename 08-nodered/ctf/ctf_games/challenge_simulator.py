import os
import time
import json
import random 
import logging
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
from opcua import Server, ua

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChallengeSimulator:
    def __init__(self):
        # MQTT Setup
        self.broker = os.getenv('MQTT_Broker', 'mosquitto')
        self.port = int(os.getenv('MQTT_PORT', '1883'))

        # MQTT Client
        self.client = mqtt.Client(client_id='challenge_simulator', clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.is_connected = False

        # Door states
        self.doors = {
            1: False,  # False = open, True = closed
            2: False,
            3: False,
            4: False
        }

        # Emergency oxygen state
        self.emergency_oxygen_activated = False
        
        # Defense systems state
        self.shield_activated = False
        self.attack_launched = False

        ### Test

        # Sensor baseline values - Sensor Data via MQTT
        self.oxygen_level = 8.0  # Critical low level (doors open)
        self.temperature = 22.0   # Celsius
        self.pressure = 101.3     # kPa
        
        # Sensor data via OPCUA
        self.aircraft_altitude = 35000.0 # feet
        self.aircraft_speed = 450.0 #knots
        self.engine_rpm = 2400.0 #RPM
        self.fuel_level = 85.0 #percentage

        # Challenge completion tracking
        self.challenge1_flag_sent = False  # Oxygen restoration
        self.challenge2_flag_sent = False  # Gate code verification
        self.challenge3_flag_sent = False  # Shield + Attack combo
        
        # Correct gate code
        self.CORRECT_GATE_CODE = "74287"
        
        # Flags
        self.FLAG_CHALLENGE_1 = "D15TR1N3T"
        self.FLAG_CHALLENGE_2 = "KUL3uV3N" 
        self.FLAG_CHALLENGE_3 = "D1EP3NB33K"
        
        # Simulation parameters
        self.update_interval = 2  # seconds
        self.deck_name = "Deck 4"

        #OPC UA Server setup
        self.opcua_server = None
        self.opcua_running = False
        self.setup_opcua_server()
        
        logger.info("Challenge Simulator Initialized")
        logger.info(f"Publishing to MQTT Broker: {self.broker}:{self.port}")
        logger.info("OPC UA Server endpoint: opc.tcp://0.0.0.0:4840")

    def setup_opcua_server(self):
        try:
            #Create OPC UA Server
            self.opcua_server = Server()
            self.opcua_server.set_endpoint("opc.tcp://0.0.0.0:4840")
            self.opcua_server.set_server_name("SilentFrikandel OPC UA Server")

            #Setup namespace
            uri = "http://silentfrikandel.ctf.opcua"
            self.idx = self.opcua_server.register_namespace(uri)
            logger.info(f"OPC UA namespace registered with index: {self.idx}")

            #get objects node
            objects = self.opcua_server.get_objects_node()

            #Create main folders
            self.aircraft_folder = objects.add_folder(self.idx, "AircraftSystems")

            #Create station sensor variables
            self.opc_oxygen = self.aircraft_folder.add_variable(
                self.idx, "OxygenLevel", self.oxygen_level, ua.VariantType.Float)
            self.opc_temperature = self.aircraft_folder.add_variable(
                self.idx, "Temperature", self.temperature, ua.VariantType.Float)
            self.opc_pressure = self.aircraft_folder.add_variable(
                self.idx, "Pressure", self.pressure, ua.VariantType.Float)
            
            self.opc_altitude = self.aircraft_folder.add_variable(
                self.idx, "Altitude", self.aircraft_altitude, ua.VariantType.Float)
            self.opc_altitude.set_writable() ##Changeable on NodeRED

            self.opc_speed = self.aircraft_folder.add_variable(
                self.idx, "AirSpeed", self.aircraft_speed, ua.VariantType.Float)
            self.opc_speed.set_writable() ##Changeable on NodeRED

            self.opc_engine_rpm = self.aircraft_folder.add_variable(
                self.idx, "EngineRPM", self.engine_rpm, ua.VariantType.Float)

            self.opc_fuel = self.aircraft_folder.add_variable(
                self.idx, "FuelLevel", self.fuel_level, ua.VariantType.Float)

            logger.info("OPC UA Server setup completed")
            logger.info(f"Available nodes in namespace {self.idx}:")
            logger.info("  - AircraftSystems/OxygenLevel")
            logger.info("  - AircraftSystems/Temperature")
            logger.info("  - AircraftSystems/Pressure")
            logger.info("  - AircraftSystems/Altitude (writable)")
            logger.info("  - AircraftSystems/AirSpeed (writable)")
            logger.info("  - AircraftSystems/EngineRPM")
            logger.info("  - AircraftSystems/FuelLevel")
        
        except Exception as e:
            logger.error(f"Failed to setup OPC UA server: {e}")

    def start_opcua_server(self):
        try:
            self.opcua_server.start()
            self.opcua_running = True
            logger.info("OPC UA Server started successfully")

            # Start thread to sync OPC UA values
            self.opcua_sync_thread = threading.Thread(target=self._sync_opcua_values)
            self.opcua_sync_thread.daemon = True
            self.opcua_sync_thread.start()
        
        except Exception as e:
            logger.error(f"Failed to start OPC UA server: {e}")
    
    def _sync_opcua_values(self):
        while self.opcua_running:
            try:
                # Generate new aircraft data
                aircraft_data = self.generate_aircraft_data()
                
                # Update sensor values in OPC UA
                self.opc_pressure.set_value(self.pressure)
                self.opc_oxygen.set_value(self.oxygen_level)
                self.opc_temperature.set_value(self.temperature)
                
                # For writable values, check if they were changed by client
                try:
                    current_altitude = self.opc_altitude.get_value()
                    current_speed = self.opc_speed.get_value()
                    
                    # If values haven't been changed significantly by client, update them
                    if abs(current_altitude - self.aircraft_altitude) < 100:
                        self.opc_altitude.set_value(self.aircraft_altitude)
                    else:
                        # Client changed altitude, use their value
                        self.aircraft_altitude = current_altitude
                        logger.info(f"OPC UA client changed altitude to: {current_altitude}")
                        
                    if abs(current_speed - self.aircraft_speed) < 10:
                        self.opc_speed.set_value(self.aircraft_speed)
                    else:
                        # Client changed speed, use their value
                        self.aircraft_speed = current_speed
                        logger.info(f"OPC UA client changed speed to: {current_speed}")
                        
                except:
                    # If reading fails, just set our values
                    self.opc_altitude.set_value(self.aircraft_altitude)
                    self.opc_speed.set_value(self.aircraft_speed)
                
                # Update read-only values
                self.opc_engine_rpm.set_value(self.engine_rpm)
                self.opc_fuel.set_value(self.fuel_level)

                time.sleep(0.5) # Sync every 500ms

            except Exception as e:
                logger.error(f"Error syncing OPC UA values: {e}")
                time.sleep(1)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            logger.info(f"MQTT connection established to {self.broker}:{self.port}")
            
            # Subscribe to door control topics
            self.client.subscribe("silentfrikandel/deck4/doors/#")
            self.client.subscribe("silentfrikandel/deck4/emergencyOxy")
            self.client.subscribe("silentfrikandel/deck4/shield")
            self.client.subscribe("silentfrikandel/deck4/attack")
            self.client.subscribe("silentfrikandel/deck4/gatecode")
            logger.info("Subscribed to control topics")
        else:
            self.is_connected = False
            logger.error(f"MQTT connection failed with code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code: {rc})")
        else:
            logger.info("Clean MQTT disconnection")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages for door controls and emergency oxygen"""
        try:
            topic = msg.topic
            
            # Handle door closure/open commands (not status messages)
            if "doors/" in topic and not topic.endswith("/status"):
                door_num = int(topic.split('/')[-1])
                payload = json.loads(msg.payload.decode())
                
                if payload.get('status') == 'closed':
                    self.doors[door_num] = True
                    logger.info(f"Door {door_num} CLOSED")
                    
                    # Check if all doors are closed
                    if all(self.doors.values()):
                        logger.info("ALL DOORS SEALED - Oxygen will stabilize")
                
                elif payload.get('status') == 'open':
                    self.doors[door_num] = False
                    self.emergency_oxygen_activated = False
                    self.challenge1_flag_sent = False  # Reset challenge 1
                    self.challenge2_flag_sent = False  # Reset challenge 2
                    self.shield_activated = False
                    self.attack_launched = False
                    self.challenge3_flag_sent = False  # Reset challenge 3
                    logger.info(f"Door {door_num} OPENED - Systems RESET")
                    
                    # Reset oxygen to critical low when any door opens
                    logger.warning("DOOR BREACH - Oxygen levels dropping to critical!")
            
            # Handle emergency oxygen activation
            elif "emergencyOxy" in topic:
                payload = json.loads(msg.payload.decode())
                
                if all(self.doors.values()):
                    self.emergency_oxygen_activated = True
                    logger.info("EMERGENCY OXYGEN ACTIVATED - Oxygen levels increasing")
                else:
                    logger.warning("Emergency oxygen activation attempted but not all doors are closed")
            
            # Handle shield activation
            elif "shield" in topic:
                self.shield_activated = True
                logger.info("SHIELD ACTIVATED")
            
            # Handle counter attack
            elif "attack" in topic:
                self.attack_launched = True
                logger.info("COUNTER ATTACK LAUNCHED")
            
            # Handle gate code submission with unified response
            elif "gatecode" in topic:
                try:
                    payload = json.loads(msg.payload.decode())
                    submitted_code = str(payload.get('code', '')).strip()
                    logger.info(f"Gate code submitted: {submitted_code}")
                    
                    if submitted_code == self.CORRECT_GATE_CODE:
                        if not self.challenge2_flag_sent:
                            self.challenge2_flag_sent = True
                            # Send unified response with flag
                            response = {
                                "status": "success",
                                "message": "Gate code accepted! Access granted.",
                                "flag": self.FLAG_CHALLENGE_2,
                                "challenge": "challenge2",
                                "timestamp": datetime.now().isoformat()
                            }
                            self.client.publish("silentfrikandel/deck4/gatecode/response", json.dumps(response), qos=0)
                            logger.info(f"CHALLENGE 2 FLAG SENT: {self.FLAG_CHALLENGE_2} - Gate code correct!")
                        else:
                            # Code correct but flag already sent
                            response = {
                                "status": "success",
                                "message": "Gate code accepted (already completed)",
                                "challenge": "challenge2",
                                "timestamp": datetime.now().isoformat()
                            }
                            self.client.publish("silentfrikandel/deck4/gatecode/response", json.dumps(response), qos=0)
                    else:
                        # Incorrect code
                        response = {
                            "status": "error",
                            "message": "Incorrect gate code. Access denied.",
                            "submitted_code": submitted_code,
                            "timestamp": datetime.now().isoformat()
                        }
                        self.client.publish("silentfrikandel/deck4/gatecode/response", json.dumps(response), qos=0)
                        logger.warning(f"Incorrect gate code: {submitted_code}")
                except Exception as e:
                    logger.error(f"Error parsing gate code payload: {e}")
                    # Send error response
                    error_response = {
                        "status": "error",
                        "message": "Invalid payload format",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.client.publish("silentfrikandel/deck4/gatecode/response", json.dumps(error_response), qos=0)
                    
        except Exception as e:
            logger.error(f"Error processing message from {msg.topic}: {e}")
    
    def connect_mqtt(self, retry_attempts=5, retry_delay=3):
        logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
        
        for attempt in range(retry_attempts):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{retry_attempts}")
                self.client.connect(self.broker, self.port, keepalive=60)
                self.client.loop_start()
                
                # Wait for connection
                timeout = 10
                while not self.is_connected and timeout > 0:
                    time.sleep(0.5)
                    timeout -= 0.5
                
                if self.is_connected:
                    logger.info("MQTT connection successful!")
                    return True
                else:
                    logger.warning(f"Connection timeout on attempt {attempt + 1}")
                    self.client.loop_stop()
                    
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            
            if attempt < retry_attempts - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        
        logger.error("All connection attempts failed")
        return False
    
    def calculate_oxygen_level(self):
        """Calculate oxygen level based on door states and emergency oxygen"""
        
        # If emergency oxygen is activated and all doors closed
        if self.emergency_oxygen_activated and all(self.doors.values()):
            # Rapidly increase oxygen to safe levels
            if self.oxygen_level < 21.0:
                self.oxygen_level += random.uniform(0.8, 1.5)
                self.oxygen_level = min(21.0, self.oxygen_level)
            else:
                # Maintain normal levels with small variations
                change = random.uniform(-0.2, 0.2)
                self.oxygen_level += change
                self.oxygen_level = max(20.0, min(22.0, self.oxygen_level))
        
        # If all doors closed but emergency oxygen not activated
        elif all(self.doors.values()):
            # Slowly stabilize but stay low
            if self.oxygen_level < 12.0:
                self.oxygen_level += random.uniform(0.1, 0.3)
            else:
                change = random.uniform(-0.2, 0.2)
                self.oxygen_level += change
                self.oxygen_level = max(10.0, min(13.0, self.oxygen_level))
        
        # If any door is open (reset state)
        else:
            # Rapidly drop oxygen to critical levels
            if self.oxygen_level > 8.0:
                # Fast drop when doors open
                self.oxygen_level -= random.uniform(0.5, 1.0)
                self.oxygen_level = max(6.0, self.oxygen_level)
            else:
                # Keep oxygen dangerously low with small variations
                change = random.uniform(-0.3, 0.3)
                self.oxygen_level += change
                self.oxygen_level = max(6.0, min(10.0, self.oxygen_level))
        
        return round(self.oxygen_level, 2)
    
    def generate_temperature_data(self):
        change = random.uniform(-0.3, 0.3)
        self.temperature += change
        
        # Keep within realistic bounds
        self.temperature = max(20.0, min(24.0, self.temperature))
        
        return round(self.temperature, 1)
    
    def generate_pressure_data(self):
        change = random.uniform(-0.1, 0.1)
        self.pressure += change
        
        # Keep within realistic bounds
        self.pressure = max(100.0, min(102.0, self.pressure))
        
        return round(self.pressure, 1)
    
    def generate_aircraft_data(self):
        # Altitude variations (small changes during cruise)
        altitude_change = random.uniform(-50, 50)
        self.aircraft_altitude += altitude_change
        self.aircraft_altitude = max(34000, min(36000, self.aircraft_altitude))
        
        # Speed variations
        speed_change = random.uniform(-5, 5)
        self.aircraft_speed += speed_change
        self.aircraft_speed = max(440, min(460, self.aircraft_speed))
        
        # Engine RPM (correlates somewhat with speed)
        base_rpm = 2300 + (self.aircraft_speed - 440) * 5
        self.engine_rpm = base_rpm + random.uniform(-50, 50)
        self.engine_rpm = max(2200, min(2600, self.engine_rpm))
        
        # Fuel consumption (slowly decreasing)
        self.fuel_level -= random.uniform(0.05, 0.15)
        self.fuel_level = max(0, self.fuel_level)
        
        return {
            'altitude': round(self.aircraft_altitude, 0),
            'speed': round(self.aircraft_speed, 1),
            'engine_rpm': round(self.engine_rpm, 0),
            'fuel': round(self.fuel_level, 1)
        }


    def publish_sensor_data(self):
        if not self.is_connected:
            logger.warning("Not connected to MQTT broker, skipping publish")
            return False
        
        try:
            # Generate sensor readings
            oxygen = self.calculate_oxygen_level()
            temperature = self.generate_temperature_data()
            pressure = self.generate_pressure_data()
            
            # Generate aircraft data (this updates the internal values)
            aircraft_data = self.generate_aircraft_data()
            
            timestamp = datetime.now().isoformat()
            
            # Publish to deck4 topics (matching Node-RED flow)
            self.client.publish("silentfrikandel/deck4/oxygen", str(oxygen), qos=0)
            self.client.publish("silentfrikandel/deck4/temperature", str(temperature), qos=0)
            self.client.publish("silentfrikandel/deck4/pressure", str(pressure), qos=0)
            
            # Publish combined data as JSON
            combined_data = {
                "deck": self.deck_name,
                "timestamp": timestamp,
                "doors_status": {
                    "door1": "closed" if self.doors[1] else "open",
                    "door2": "closed" if self.doors[2] else "open",
                    "door3": "closed" if self.doors[3] else "open",
                    "door4": "closed" if self.doors[4] else "open",
                    "all_sealed": all(self.doors.values())
                },
                "emergency_oxygen": self.emergency_oxygen_activated,
                "sensors": {
                    "oxygen": oxygen,
                    "temperature": temperature,
                    "pressure": pressure
                },
                "aircraft": aircraft_data
            }
            self.client.publish("silentfrikandel/deck4/all", json.dumps(combined_data), qos=0)
            
            # Publish door statuses individually
            for door_num, is_closed in self.doors.items():
                status = "CLOSED" if is_closed else "OPEN"
                self.client.publish(f"silentfrikandel/deck4/doors/{door_num}/status", status, qos=0)
            
            # CHALLENGE 1: Check if oxygen is above 18% and send flag
            if oxygen >= 18.0 and not self.challenge1_flag_sent:
                flag_data = {"flag": self.FLAG_CHALLENGE_1}
                self.client.publish("silentfrikandel/deck4/challenge1/flag", json.dumps(flag_data), qos=0)
                self.challenge1_flag_sent = True
                logger.info(f"CHALLENGE 1 FLAG SENT: {self.FLAG_CHALLENGE_1} - Oxygen restored!")
            
            # CHALLENGE 2 is handled by gate code input
            
            # CHALLENGE 3: Check if BOTH shield activated AND attack launched
            if self.shield_activated and self.attack_launched and not self.challenge3_flag_sent:
                flag_data = {"flag": self.FLAG_CHALLENGE_3}
                self.client.publish("silentfrikandel/deck4/challenge3/flag", json.dumps(flag_data), qos=0)
                self.challenge3_flag_sent = True
                logger.info(f"CHALLENGE 3 FLAG SENT: {self.FLAG_CHALLENGE_3} - Defense systems operational!")
            
            # Log the published data
            all_doors = "ALL SEALED" if all(self.doors.values()) else "DOORS OPEN"
            oxy_status = "ACTIVATED" if self.emergency_oxygen_activated else "standby"
            defense = f"Shield:{self.shield_activated} Attack:{self.attack_launched}"
            flags = f"C1:{self.challenge1_flag_sent} C2:{self.challenge2_flag_sent} C3:{self.challenge3_flag_sent}"
            logger.info(f"O2: {oxygen}% | {all_doors} | Oxy: {oxy_status} | {defense} | Flags: {flags}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing sensor data: {e}")
            return False
    
    def run_simulation(self):
        logger.info("=" * 70)
        logger.info("CHALLENGE SIMULATOR - Deck 4 Life Support Emergency")
        logger.info("=" * 70)
        logger.info("SCENARIO: Doors are OPEN - Oxygen levels CRITICAL!")
        logger.info("MISSION: Complete 3 challenges to save the ship")
        logger.info("=" * 70)
        
        # Start OPC UA Server
        self.start_opcua_server()

        # Connect to MQTT broker
        if not self.connect_mqtt():
            logger.error("Failed to connect to MQTT broker. Exiting.")
            return
        
        logger.info(f"Simulation running. Publishing every {self.update_interval} second(s)")
        logger.info("OPC UA Server running on opc.tcp://0.0.0.0:4840")
        logger.info("Listening for door controls and emergency oxygen commands...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                # Publish sensor data
                self.publish_sensor_data()
                
                # Wait before next update
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            logger.info("Cleaning up...")
            
            # Stop OPC UA server
            if self.opcua_running:
                self.opcua_running = False
                if self.opcua_server:
                    self.opcua_server.stop()
                    logger.info("OPC UA server stopped")
            
            # Disconnect MQTT
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Challenge simulator stopped")

def main():
    """Entry point for the challenge simulator"""
    simulator = ChallengeSimulator()
    simulator.run_simulation()

if __name__ == "__main__":
    main()