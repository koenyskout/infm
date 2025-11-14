import os
import time
import json
import random 
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('/tmp/sensor_simulator.log')  # Also save to file
    ]
)
logger = logging.getLogger(__name__)

class SensorSimulator:
    def __init__(self):
        # MQTT Setup
        self.broker = os.getenv('MQTT_Broker', 'mosquitto')
        self.port = int(os.getenv('MQTT_PORT', '1883'))

        # MQTT Client
        self.client = mqtt.Client(client_id='sensor_simulator', clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish  # Add publish callback for logging

        self.is_connected = False
        self.publish_count = 0  # Track number of publishes

        # Environmental sensor baseline values
        self.oxygen_level = 21.0  # Normal oxygen percentage
        self.temperature = 22.0   # Celsius
        self.pressure = 101.3     # kPa
        
        # Aircraft/Spacecraft sensor baselines
        # Flight dynamics
        self.altitude = 35000     # feet (cruising altitude)
        self.airspeed = 450       # knots
        self.groundspeed = 440    # knots
        self.vertical_speed = 0   # feet/min
        self.mach = 0.78         # Mach number
        
        # Navigation
        self.heading = 90         # degrees (East)
        self.track = 92          # degrees (actual track over ground)
        self.latitude = 40.7128   # degrees
        self.longitude = -74.0060 # degrees
        
        # Attitude
        self.pitch = 0           # degrees
        self.roll = 0            # degrees
        self.yaw_rate = 0        # degrees/sec
        
        # Engine parameters
        self.engine1_rpm = 2400   # RPM
        self.engine2_rpm = 2395   # RPM
        self.engine1_egt = 1450   # Exhaust Gas Temperature (F)
        self.engine2_egt = 1445   # EGT (F)
        self.fuel_flow_left = 120  # gallons/hour
        self.fuel_flow_right = 118 # gallons/hour
        self.fuel_quantity = 8500  # gallons total
        
        # System pressures and temperatures
        self.oil_pressure_1 = 75   # PSI
        self.oil_pressure_2 = 74   # PSI
        self.oil_temp_1 = 180      # Fahrenheit
        self.oil_temp_2 = 178      # Fahrenheit
        self.hydraulic_pressure_a = 3000  # PSI
        self.hydraulic_pressure_b = 2950  # PSI
        
        # Electrical system
        self.battery_voltage = 28.0      # Volts (aircraft standard)
        self.generator_1_current = 120   # Amps
        self.generator_2_current = 115   # Amps
        self.bus_voltage = 28.2         # Volts
        
        # Environmental control
        self.cabin_pressure_altitude = 8000  # feet
        self.cabin_temp = 22              # Celsius
        self.cabin_humidity = 45          # percent
        
        # Star Trek specific (for fun!)
        self.warp_core_temp = 2000        # Kelvin
        self.shield_strength = 100        # percent
        self.phaser_charge = 100          # percent
        self.antimatter_flow = 0.85       # kg/s
        
        # Simulation parameters
        self.update_interval = 1  # seconds
        self.deck_name = "Deck 5"
        
        logger.info("="*60)
        logger.info("Advanced Sensor Simulator Initialized")
        logger.info("Aircraft + Spacecraft Mode")
        logger.info(f"MQTT Broker: {self.broker}:{self.port}")
        logger.info("="*60)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            logger.info(f"MQTT CONNECTED to {self.broker}:{self.port}")
            logger.info(f"Client ID: {client._client_id.decode()}")
        else:
            self.is_connected = False
            logger.error(f"MQTT CONNECTION FAILED - Error code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code: {rc})")
        else:
            logger.info("Clean MQTT disconnection")
    
    def _on_publish(self, client, userdata, mid):
        """Log successful publishes"""
        logger.debug(f"Message published (mid: {mid})")
        self.publish_count += 1
    
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
    
    # Original environmental sensors
    def generate_oxygen_data(self):
        change = random.uniform(-0.3, 0.3)
        self.oxygen_level += change
        self.oxygen_level = max(18.0, min(23.0, self.oxygen_level))
        if random.random() < 0.05:
            self.oxygen_level += random.uniform(-1.5, 1.5)
        return round(self.oxygen_level, 2)
    
    def generate_temperature_data(self):
        change = random.uniform(-0.5, 0.5)
        self.temperature += change
        self.temperature = max(18.0, min(26.0, self.temperature))
        if random.random() < 0.03:
            self.temperature += random.uniform(-2.0, 2.0)
        return round(self.temperature, 1)
    
    def generate_pressure_data(self):
        change = random.uniform(-0.2, 0.2)
        self.pressure += change
        self.pressure = max(98.0, min(104.0, self.pressure))
        if random.random() < 0.04:
            self.pressure += random.uniform(-1.0, 1.0)
        return round(self.pressure, 1)
    
    # Aircraft flight dynamics sensors
    def generate_altitude_data(self):
        # Simulate minor altitude changes
        change = random.uniform(-50, 50)
        self.altitude += change
        self.altitude = max(30000, min(41000, self.altitude))
        return round(self.altitude)
    
    def generate_airspeed_data(self):
        change = random.uniform(-5, 5)
        self.airspeed += change
        self.airspeed = max(400, min(500, self.airspeed))
        self.groundspeed = self.airspeed + random.uniform(-15, 15)  # Wind effect
        self.mach = round(self.airspeed / 667.0, 2)  # Approximate Mach calculation
        return round(self.airspeed)
    
    def generate_attitude_data(self):
        # Small random changes to simulate turbulence
        self.pitch += random.uniform(-0.5, 0.5)
        self.roll += random.uniform(-1.0, 1.0)
        self.pitch = max(-5, min(5, self.pitch))
        self.roll = max(-30, min(30, self.roll))
        
        # Occasionally return to level flight
        if random.random() < 0.1:
            self.pitch *= 0.8
            self.roll *= 0.8
        
        return round(self.pitch, 1), round(self.roll, 1)
    
    def generate_engine_data(self):
        # Engine RPM with slight variations
        self.engine1_rpm += random.uniform(-20, 20)
        self.engine2_rpm += random.uniform(-20, 20)
        self.engine1_rpm = max(2300, min(2500, self.engine1_rpm))
        self.engine2_rpm = max(2300, min(2500, self.engine2_rpm))
        
        # EGT variations
        self.engine1_egt += random.uniform(-10, 10)
        self.engine2_egt += random.uniform(-10, 10)
        self.engine1_egt = max(1400, min(1500, self.engine1_egt))
        self.engine2_egt = max(1400, min(1500, self.engine2_egt))
        
        # Fuel consumption
        self.fuel_quantity -= (self.fuel_flow_left + self.fuel_flow_right) / 3600  # per second
        self.fuel_quantity = max(0, self.fuel_quantity)
        
        return {
            "engine1_rpm": round(self.engine1_rpm),
            "engine2_rpm": round(self.engine2_rpm),
            "engine1_egt": round(self.engine1_egt),
            "engine2_egt": round(self.engine2_egt),
            "fuel_remaining": round(self.fuel_quantity)
        }
    
    def generate_electrical_data(self):
        # Electrical system variations
        self.battery_voltage += random.uniform(-0.1, 0.1)
        self.battery_voltage = max(27.5, min(28.5, self.battery_voltage))
        
        self.generator_1_current += random.uniform(-5, 5)
        self.generator_2_current += random.uniform(-5, 5)
        
        return {
            "battery_voltage": round(self.battery_voltage, 1),
            "gen1_current": round(self.generator_1_current),
            "gen2_current": round(self.generator_2_current),
            "bus_voltage": round(self.bus_voltage, 1)
        }
    
    def generate_starship_data(self):
        # Fun Star Trek sensors
        self.warp_core_temp += random.uniform(-50, 50)
        self.warp_core_temp = max(1800, min(2200, self.warp_core_temp))
        
        self.shield_strength += random.uniform(-2, 1)
        self.shield_strength = max(0, min(100, self.shield_strength))
        
        self.antimatter_flow += random.uniform(-0.05, 0.05)
        self.antimatter_flow = max(0.5, min(1.0, self.antimatter_flow))
        
        return {
            "warp_core_temp": round(self.warp_core_temp),
            "shield_strength": round(self.shield_strength),
            "antimatter_flow": round(self.antimatter_flow, 2)
        }
    
    def mqtt_publish_with_logging(self, topic, payload, qos=0):
        """Helper function to publish with detailed logging"""
        result = self.client.publish(topic, payload, qos)
        status = "SUCCESS" if result.rc == mqtt.MQTT_ERR_SUCCESS else f"FAILED (rc={result.rc})"
        logger.info(f"MQTT PUBLISH [{status}] {topic} = {payload}")
        return result.rc == mqtt.MQTT_ERR_SUCCESS
    
    def publish_sensor_data(self):
        """Publish all sensor data to MQTT with detailed logging"""
        if not self.is_connected:
            logger.warning("Not connected to MQTT broker, skipping publish")
            return False
        
        try:
            timestamp = datetime.now().isoformat()
            logger.info(f"\n{'='*60}")
            logger.info(f"PUBLISHING SENSOR DATA - {timestamp}")
            logger.info(f"{'='*60}")
            
            successful_publishes = 0
            
            # Environmental sensors (original)
            logger.info("\nENVIRONMENTAL SENSORS:")
            oxygen = self.generate_oxygen_data()
            temperature = self.generate_temperature_data()
            pressure = self.generate_pressure_data()
            
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/oxygen", str(oxygen)):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/temperature", str(temperature)):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/pressure", str(pressure)):
                successful_publishes += 1
            
            # Flight dynamics
            logger.info("\nFLIGHT DYNAMICS:")
            altitude = self.generate_altitude_data()
            airspeed = self.generate_airspeed_data()
            pitch, roll = self.generate_attitude_data()
            
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/flight/altitude", str(altitude)):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/flight/airspeed", str(airspeed)):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/flight/groundspeed", str(round(self.groundspeed))):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/flight/mach", str(self.mach)):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/flight/pitch", str(pitch)):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/flight/roll", str(roll)):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/flight/heading", str(round(self.heading))):
                successful_publishes += 1
            
            # Engine data
            logger.info("\nENGINE SYSTEMS:")
            engine_data = self.generate_engine_data()
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/engine/rpm1", str(engine_data["engine1_rpm"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/engine/rpm2", str(engine_data["engine2_rpm"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/engine/egt1", str(engine_data["engine1_egt"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/engine/egt2", str(engine_data["engine2_egt"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/engine/fuel", str(engine_data["fuel_remaining"])):
                successful_publishes += 1
            
            # Electrical system
            logger.info("\nELECTRICAL SYSTEMS:")
            electrical_data = self.generate_electrical_data()
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/electrical/battery", str(electrical_data["battery_voltage"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/electrical/gen1", str(electrical_data["gen1_current"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/electrical/gen2", str(electrical_data["gen2_current"])):
                successful_publishes += 1
            
            # Star Trek sensors
            logger.info("\nSTARSHIP SYSTEMS:")
            starship_data = self.generate_starship_data()
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/starship/warp_temp", str(starship_data["warp_core_temp"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/starship/shields", str(starship_data["shield_strength"])):
                successful_publishes += 1
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/starship/antimatter", str(starship_data["antimatter_flow"])):
                successful_publishes += 1
            
            # Publish combined data as JSON
            logger.info("\nCOMBINED JSON DATA:")
            combined_data = {
                "deck": self.deck_name,
                "timestamp": timestamp,
                "environmental": {
                    "oxygen": oxygen,
                    "temperature": temperature,
                    "pressure": pressure
                },
                "flight": {
                    "altitude": altitude,
                    "airspeed": airspeed,
                    "groundspeed": round(self.groundspeed),
                    "mach": self.mach,
                    "pitch": pitch,
                    "roll": roll,
                    "heading": round(self.heading)
                },
                "engines": engine_data,
                "electrical": electrical_data,
                "starship": starship_data
            }
            if self.mqtt_publish_with_logging("silentfrikandel/deck5/all", json.dumps(combined_data)):
                successful_publishes += 1
            
            # Summary
            total_topics = 21  # Total number of topics we publish to
            logger.info(f"\nPUBLISH SUMMARY:")
            logger.info(f"   Total topics published: {successful_publishes}/{total_topics}")
            logger.info(f"   Success rate: {(successful_publishes/total_topics)*100:.1f}%")
            logger.info(f"   Total publishes since start: {self.publish_count}")
            logger.info(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing sensor data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_simulation(self):
        """Main simulation loop"""
        logger.info("\n" + "="*60)
        logger.info("STARTING ADVANCED SENSOR SIMULATION")
        logger.info("Simulating: Environmental, Flight, Engine, Electrical, and Starship sensors")
        logger.info("="*60 + "\n")
        
        # Connect to MQTT broker
        if not self.connect_mqtt():
            logger.error("Failed to connect to MQTT broker. Exiting.")
            return
        
        logger.info(f"\nSimulation running!")
        logger.info(f"Publishing every {self.update_interval} second(s)")
        logger.info(f"Broadcasting to: silentfrikandel/deck5/*")
        logger.info(f"Log file: /tmp/sensor_simulator.log")
        logger.info(f"\nPress Ctrl+C to stop\n")
        
        try:
            cycle = 0
            while True:
                cycle += 1
                logger.info(f"\n=== CYCLE {cycle} ===")
                
                # Publish sensor data
                self.publish_sensor_data()
                
                # Wait before next update
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            logger.info("\nSimulation stopped by user")
        except Exception as e:
            logger.error(f"\nSimulation error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            logger.info("\nCleaning up...")
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Sensor simulator stopped cleanly")
            logger.info(f"Total messages published: {self.publish_count}")

def main():
    """Entry point for the sensor simulator"""
    print("\n" + "="*60)
    print("USS SilentFrikandel - Advanced Sensor Simulator")
    print("Environmental + Aircraft + Starship Systems")
    print("="*60 + "\n")
    
    simulator = SensorSimulator()
    simulator.run_simulation()

if __name__ == "__main__":
    main()