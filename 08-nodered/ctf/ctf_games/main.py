import os
import time
import json
import logging
from datetime import datetime
from mqtt_handler import MQTTHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuizBachelor_KUL:
    def __init__(self):
        #STATIC FLAGS FOR ALL CHALLENGES:
        self.FLAGS_CHALLENGE_1 = "D15TR1N3T"
        self.FLAGS_CHALLENGE_2 = "KUL3uV3N"
        self.FLAGS_CHALLENGE_3 = "D1EP3NB33K"

        #MQTT Setup - MOSQUITTO
        self.mqtt_handler = MQTTHandler(
            broker=os.getenv('MQTT_Broker', 'mosquitto'),
            port=int(os.getenv('MQTT_PORT', '1883')),
            topic_base = 'DistrinetQuiz'
        )

        #Student Progress
        self.student_progress = {}

        # #Setup Callbacks
        # self.mqtt_handler.on_gate_puzzle = self.handle_gate_puzzle
        # self.mqtt_handler.on_machine_puzzle = self.handle_machine_puzzle

        # Setup Callbacks
        self.mqtt_handler.on_challenge_1 = self.handle_challenge_1
        self.mqtt_handler.on_challenge_2 = self.handle_challenge_2
        self.mqtt_handler.on_challenge_3 = self.handle_challenge_3
        self.mqtt_handler.on_challenge_4 = self.handle_challenge_4
   
    def publish_challenge_status(self, student_id, challenge_number, completed=True):
        status_topic = "quiz/status/" + student_id + "/challenge" + str(challenge_number)
        status_message = {
            'challenge': 'challenge' + str(challenge_number),
            'completed': completed,
            'timestamp': datetime.now().isoformat()
        }
        success = self.mqtt_handler.publish(status_topic, json.dumps(status_message))
        if success:
            logger.info("Published status for " + student_id + " - Challenge " + str(challenge_number) + ": " + str(completed))

    def unlock_next_challenge(self, student_id, completed_challenge):
        next_challenge = completed_challenge + 1
        if next_challenge <= 4:
            # Publish unlock status
            unlock_topic = "quiz/unlock/" + student_id + "/challenge" + str(next_challenge)
            unlock_message = {
                'unlocked': True,
                'challenge': next_challenge,
                'message': 'Challenge ' + str(next_challenge) + ' is now unlocked!',
                'timestamp': datetime.now().isoformat()
            }
            self.mqtt_handler.publish(unlock_topic, json.dumps(unlock_message))
            logger.info("Unlocked Challenge " + str(next_challenge) + " for " + student_id)

    def handle_challenge_1(self, topic, message, student_id):
        try:
            data = json.loads(message)
            submitted_flag = str(data.get('flag', '')).strip()

            logger.info("Student " + student_id + " submitted Challenge 1 flag: " + submitted_flag)

            # Initialize student progress
            if student_id not in self.student_progress:
                self.student_progress[student_id] = {
                    'challenge1_completed': False,
                    'challenge2_completed': False,
                    'challenge3_completed': False,
                    'challenge4_completed': False,
                    'start_time': datetime.now()
                }
                logger.info("New student registered: " + student_id)

            # Check flag
            if submitted_flag == self.FLAGS_CHALLENGE_1:
                self.student_progress[student_id]['challenge1_completed'] = True
                self.publish_challenge_status(student_id, 1, True)
                self.unlock_next_challenge(student_id, 1)

                response = {
                    'success': True,
                    'student_id': student_id,
                    'challenge': 1,
                    'message': 'SUCCESS! Challenge 1 completed.',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info("SUCCESS: Student " + student_id + " completed Challenge 1")
            else:
                response = {
                    'success': False,
                    'student_id': student_id,
                    'challenge': 1,
                    'message': 'INCORRECT flag. Try again.',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info("FAILED: Student " + student_id + " submitted wrong flag for Challenge 1")

            # Send feedback
            feedback_topic = "silentfrikandel/" + student_id + "/challenge1/feedback"
            self.mqtt_handler.publish(feedback_topic, json.dumps(response))

        except Exception as e:
            logger.error("Error handling Challenge 1 from student " + student_id + ": " + str(e))

    def handle_challenge_2(self, topic, message, student_id):
        try:
            data = json.loads(message)
            submitted_flag = str(data.get('flag', '')).strip()

            logger.info("Student " + student_id + " submitted Challenge 2 flag: " + submitted_flag)

            if student_id not in self.student_progress:
                self.student_progress[student_id] = {
                    'challenge1_completed': False,
                    'challenge2_completed': False,
                    'challenge3_completed': False,
                    'challenge4_completed': False,
                    'start_time': datetime.now()
                }

            # Check flag
            if submitted_flag == self.FLAGS_CHALLENGE_2:
                self.student_progress[student_id]['challenge2_completed'] = True
                self.publish_challenge_status(student_id, 2, True)

                self.unlock_next_challenge(student_id, 2)

                response = {
                    'success': True,
                    'student_id': student_id,
                    'challenge': 2,
                    'message': 'SUCCESS! Challenge 2 completed.',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info("SUCCESS: Student " + student_id + " completed Challenge 2")
            else:
                response = {
                    'success': False,
                    'student_id': student_id,
                    'challenge': 2,
                    'message': 'INCORRECT flag. Try again.',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info("FAILED: Student " + student_id + " submitted wrong flag for Challenge 2")

            # Send feedback
            feedback_topic = "silentfrikandel/" + student_id + "/challenge2/feedback"
            self.mqtt_handler.publish(feedback_topic, json.dumps(response))

        except Exception as e:
            logger.error("Error handling Challenge 2 from student " + student_id + ": " + str(e))

    def handle_challenge_3(self, topic, message, student_id):
        try:
            data = json.loads(message)
            submitted_flag = str(data.get('flag', '')).strip()

            logger.info("Student " + student_id + " submitted Challenge 3 flag: " + submitted_flag)

            if student_id not in self.student_progress:
                self.student_progress[student_id] = {
                    'challenge1_completed': False,
                    'challenge2_completed': False,
                    'challenge3_completed': False,
                    'challenge4_completed': False,
                    'start_time': datetime.now()
                }

            # Check flag
            if submitted_flag == self.FLAGS_CHALLENGE_3:
                self.student_progress[student_id]['challenge3_completed'] = True
                self.publish_challenge_status(student_id, 3, True)

                self.unlock_next_challenge(student_id, 3)

                response = {
                    'success': True,
                    'student_id': student_id,
                    'challenge': 3,
                    'message': 'SUCCESS! Challenge 3 completed.',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info("SUCCESS: Student " + student_id + " completed Challenge 3")
            else:
                response = {
                    'success': False,
                    'student_id': student_id,
                    'challenge': 3,
                    'message': 'INCORRECT flag. Try again.',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info("FAILED: Student " + student_id + " submitted wrong flag for Challenge 3")

            # Send feedback
            feedback_topic = "silentfrikandel/" + student_id + "/challenge3/feedback"
            self.mqtt_handler.publish(feedback_topic, json.dumps(response))

        except Exception as e:
            logger.error("Error handling Challenge 3 from student " + student_id + ": " + str(e))

    def handle_challenge_4(self, topic, message, student_id):
        try:
            data = json.loads(message)
            submitted_flag = str(data.get('flag', '')).strip()

            logger.info("Student " + student_id + " submitted Challenge 4 flag: " + submitted_flag)

            if student_id not in self.student_progress:
                self.student_progress[student_id] = {
                    'challenge1_completed': False,
                    'challenge2_completed': False,
                    'challenge3_completed': False,
                    'challenge4_completed': False,
                    'start_time': datetime.now()
                }

            # Check flag
            if submitted_flag == self.FLAGS_CHALLENGE_4:
                self.student_progress[student_id]['challenge4_completed'] = True
                self.publish_challenge_status(student_id, 4, True)

                # Check if all challenges completed
                all_completed = (
                    self.student_progress[student_id]['challenge1_completed'] and
                    self.student_progress[student_id]['challenge2_completed'] and
                    self.student_progress[student_id]['challenge3_completed'] and
                    self.student_progress[student_id]['challenge4_completed']
                )

                if all_completed:
                    total_seconds = (datetime.now() - self.student_progress[student_id]['start_time']).total_seconds()
                    total_minutes = int(total_seconds // 60)
                    remaining_seconds = int(total_seconds % 60)

                    response = {
                        'success': True,
                        'student_id': student_id,
                        'challenge': 4,
                        'message': 'SUCCESS! ALL CHALLENGES COMPLETED! Congratulations!',
                        'total_time': str(total_minutes) + "m " + str(remaining_seconds) + "s",
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info("ALL CHALLENGES COMPLETED: Student " + student_id + " finished in " + str(total_minutes) + "m " + str(remaining_seconds) + "s")
                else:
                    response = {
                        'success': True,
                        'student_id': student_id,
                        'challenge': 4,
                        'message': 'SUCCESS! Challenge 4 completed.',
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info("SUCCESS: Student " + student_id + " completed Challenge 4")
            else:
                response = {
                    'success': False,
                    'student_id': student_id,
                    'challenge': 4,
                    'message': 'INCORRECT flag. Try again.',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info("FAILED: Student " + student_id + " submitted wrong flag for Challenge 4")

            # Send feedback
            feedback_topic = "silentfrikandel/" + student_id + "/challenge4/feedback"
            self.mqtt_handler.publish(feedback_topic, json.dumps(response))

        except Exception as e:
            logger.error("Error handling Challenge 4 from student " + student_id + ": " + str(e))

    def get_active_student_summary(self):
        if not self.student_progress:
            return "No students active"
        
        summary = []
        for student_id, progress in self.student_progress.items():
            completed = sum([
                progress['challenge1_completed'],
                progress['challenge2_completed'],
                progress['challenge3_completed'],
                progress['challenge4_completed']
            ])
            summary.append(student_id + "(" + str(completed) + "/4)")
        
        return "Active students: " + ", ".join(summary)
    
    def run(self):
        logger.info("Starting the quiz system")

        # Connect to MQTT Broker
        if not self.mqtt_handler.connect():
            logger.error("Failed to connect to MQTT Broker - System cannot start")
            return
        
        # Subscribe to flag submission topics
        topics_to_subscribe = [
            "silentfrikandel/+/challenge1/flag",
            "silentfrikandel/+/challenge2/flag",
            "silentfrikandel/+/challenge3/flag",
            "silentfrikandel/+/challenge4/flag"
        ]

        for topic in topics_to_subscribe:
            if self.mqtt_handler.subscribe(topic):
                logger.info("Successfully subscribed to: " + topic)
            else:
                logger.error("Failed to subscribe to: " + topic)
                return
            
        try:
            while True:
                time.sleep(120)
                if self.student_progress:
                    logger.info(self.get_active_student_summary())
                else:
                    logger.info("System running - waiting for students...")
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error("Unexpected error in main loop: " + str(e))
        finally:
            logger.info("Shutting down Quiz System...")
            self.mqtt_handler.disconnect()
            logger.info("System shutdown complete")

if __name__ == "__main__":
    try:
        quiz_system = QuizBachelor_KUL()
        quiz_system.run()
    except Exception as e:
        logger.error("Failed to start quiz system: " + str(e))
        exit(1)