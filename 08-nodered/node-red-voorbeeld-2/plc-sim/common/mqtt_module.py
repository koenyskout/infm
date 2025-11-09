from abc import abstractmethod
import threading
from typing import override
from common.PLC import IOModule, PLC_State, Tag

import paho.mqtt.client as mqtt
import time

# class to connect a PLC Tag to an MQTT topic


class MQTTTagMapping:
    """
    Represents an MQTT topic that is linked to a PLC tag.
    Can be read-only (tag values only published) or writable (tag values can also be set from MQTT messages).
    """

    def __init__(self, mqtt_topic: str, tag: Tag, writable: bool = False):
        self.topic = mqtt_topic
        self.tag = tag
        self.writable = writable
        self.last_value = None

    def set_tag_from_payload(self, payload: str):
        """
         Set the PLC tag value from the MQTT payload.
         Only works if this mapping is writable.
        """
        if not self.writable:
            return
        # convert payload to tag datatype
        if self.tag.datatype == float:
            value = float(payload)
        elif self.tag.datatype == int:
            value = int(payload)
        elif self.tag.datatype == bool:
            value = payload.lower() in ("true", "1", "yes")
        elif self.tag.datatype == str:
            value = str(payload)
        else:
            raise ValueError(
                f"Unsupported tag datatype for MQTT topic: {self.tag.datatype}")
        self.tag.set(value)

    def get_payload_to_send(self, only_if_changed: bool = True) -> mqtt.PayloadType | None:
        value = self.tag.get()
        if not only_if_changed or value != self.last_value:
            self.last_value = value
            return str(value)
        return None


class MQTT_IO_Module[PLCState: PLC_State](IOModule[PLCState]):
    """
    Base class for an MQTT IO module for publishing PLC tags.

    Only sends changed values, and limits publish rate to avoid flooding the broker.
    """

    def __init__(self,
                 broker: str,
                 port: int,
                 topic_prefix: str = "",
                 publish_interval: float = 5.0,
                 only_send_changed: bool = True):
        """
         :param broker: MQTT broker hostname or IP address
         :param port: MQTT broker port
         :param topic_prefix: Prefix to add to all topics
         :param publish_interval: Minimum interval between publishes in seconds
        """
        self.broker = broker
        self.port = port
        self.only_send_changed = only_send_changed
        self.pending_inputs = {}  # to store pending inputs
        self.pending_inputs_lock = threading.Lock()
        self.topic_prefix = topic_prefix
        self.publish_interval = publish_interval
        self._next_publish_time = 0

    @staticmethod
    def join_topic(prefix: str, topic: str) -> str:
        while prefix.endswith("/"):
            prefix = prefix[:-1]
        while topic.startswith("/"):
            topic = topic[1:]
        return f"{prefix}/{topic}"

    @override
    def start_module(self, plc_state):
        print(f"Starting MQTT client to {self.broker}:{self.port}...")
        # open MQTT connection to server
        self.topic_mappings = self._create_mappings(plc_state)
        for topic_mapping in self.topic_mappings:
            topic_mapping.topic = self.join_topic(
                self.topic_prefix, topic_mapping.topic)

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2)  # type: ignore
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        print(f"Started MQTT client to {self.broker}:{self.port}")

    @abstractmethod
    def _create_mappings(self, plc_state) -> list[MQTTTagMapping]:
        ...

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        print(
            f"Connected to MQTT broker at {self.broker}:{self.port} with result code {reason_code}")
        for mqtt_topic in self.topic_mappings:
            self.client.subscribe(mqtt_topic.topic)

    def _on_message(self, client, userdata, message):
        # save message so it can later be processed in read_inputs
        # don't immediately set the tag (must be done from the PLC thread)
        topic = message.topic
        payload = message.payload.decode()
        for mqtt_topic in self.topic_mappings:
            if mqtt_topic.writable and mqtt_topic.topic == topic:
                mqtt_topic.set_tag_from_payload(payload)
                # Instead, we store the topic and payload for later processing
                # pending_inputs should be thread-safe as MQTT callbacks run in a separate thread
                with self.pending_inputs_lock:
                    self.pending_inputs[mqtt_topic.tag] = payload

    @override
    def stop_module(self, plc_state):
        # close MQTT connection
        self.client.disconnect()
        self.client.loop_stop()
        print(f"Stopped MQTT client to {self.broker}:{self.port}")

    @override
    def read_inputs(self, plc_state):
        # update PLC state with values from MQTT subscriptions (stored in pending_inputs)
        with self.pending_inputs_lock:
            for tag, payload in self.pending_inputs.items():
                for mqtt_topic in self.topic_mappings:
                    if mqtt_topic.tag == tag:
                        mqtt_topic.set_tag_from_payload(payload)
            self.pending_inputs.clear()

    @override
    def write_outputs(self, plc_state):
        """
        Publish PLC state to MQTT topics according to the topic mappings.
        """
        if self._prepare_to_publish():
            for tag in plc_state.tags():
                self._publish_tag(tag)

    def _publish_tag(self, tag: Tag):
        mapping = self._find_mapping_for_tag(tag)
        if mapping is not None:
            payload = mapping.get_payload_to_send(self.only_send_changed)
            if payload is not None:
                self.client.publish(mapping.topic, payload)

    def _prepare_to_publish(self) -> bool:
        """
        Check time since last publish
        """
        now = time.monotonic()
        if now < self._next_publish_time:
            return False
        self._next_publish_time = now + self.publish_interval
        return True

    def _find_mapping_for_tag(self, tag: Tag) -> MQTTTagMapping | None:
        for mapping in self.topic_mappings:
            if mapping.tag == tag:
                return mapping
        return None
