from opcua import Server
import time

server = Server()
server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")

objects = server.get_objects_node()
temp = objects.add_variable("ns=2;s=Temperature", "Temperature", 20.0)
temp.set_writable()

server.start()
print("Server started at opc.tcp://localhost:4840")

try:
    while True:
        new_val = temp.get_value() + 0.1
        temp.set_value(new_val)
        time.sleep(1)
finally:
    server.stop()
