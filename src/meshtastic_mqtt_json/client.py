#!/usr/bin/env python
# Meshtastic MQTT Interface - Developed by acidvegas in Python (https://acid.vegas/meshtastic_mqtt_json)

import argparse
import base64
import json

try:
	from cryptography.hazmat.backends           import default_backend
	from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except ImportError:
	raise ImportError('missing the cryptography module (pip install cryptography)')

try:
	from google.protobuf.json_format import MessageToJson
except ImportError:
	raise ImportError('missing the google protobuf module (pip install protobuf)')

try:
	from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2, telemetry_pb2
except ImportError:
	raise ImportError('missing the meshtastic module (pip install meshtastic)')

try:
	import paho.mqtt.client as mqtt
except ImportError:
	raise ImportError('missing the paho-mqtt module (pip install paho-mqtt)')


class MeshtasticMQTT(object):
	def __init__(self):
		'''Initialize the Meshtastic MQTT client'''

		self.broadcast_id = 4294967295 # Our channel ID
		self.key          = None
		self.names        = {}
		self.filters      = None


	def connect(self, broker: str, port: int, root: str, channel: str, username: str, password: str, key: str):
		'''
		Connect to the MQTT broker

		:param broker:   The MQTT broker address
		:param port:     The MQTT broker port
		:param root:     The root topic
		:param channel:  The channel name
		:param username: The MQTT username
		:param password: The MQTT password
		:param key:      The encryption key
		'''

		# Initialize the MQTT client
		client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='', clean_session=True, userdata=None)

		# Set the username and password for the MQTT broker
		client.username_pw_set(username=username, password=password)

		# Set the encryption key
		self.key = '1PG7OiApB1nwvP+rz05pAQ==' if key == 'AQ==' else key

		# Prepare the key for decryption
		try:
			padded_key = self.key.ljust(len(self.key) + ((4 - (len(self.key) % 4)) % 4), '=')
			replaced_key = padded_key.replace('-', '+').replace('_', '/')
			self.key_bytes = base64.b64decode(replaced_key.encode('ascii'))
		except Exception as e:
			print(f'Error decoding key: {e}')
			raise

		# Set the MQTT callbacks
		client.on_connect = self.event_mqtt_connect
		client.on_message = self.event_mqtt_recv

		# Connect to the MQTT broker
		client.connect(broker, port, 60)

		# Set the subscribe topic
		self.subscribe_topic = f'{root}{channel}/#'

		# Keep-alive loop
		client.loop_forever()


	def decrypt_message_packet(self, mp):
		'''
		Decrypt an encrypted message packet.

		:param mp: The message packet to decrypt
		'''

		try:
			# Extract the nonce from the packet
			nonce_packet_id = getattr(mp, 'id').to_bytes(8, 'little')
			nonce_from_node = getattr(mp, 'from').to_bytes(8, 'little')
			nonce = nonce_packet_id + nonce_from_node

			# Decrypt the message
			cipher          = Cipher(algorithms.AES(self.key_bytes), modes.CTR(nonce), backend=default_backend())
			decryptor       = cipher.decryptor()
			decrypted_bytes = decryptor.update(getattr(mp, 'encrypted')) + decryptor.finalize()

			# Parse the decrypted message
			data = mesh_pb2.Data()
			data.ParseFromString(decrypted_bytes)
			mp.decoded.CopyFrom(data)
			return mp
		except Exception as e:
			print(f'Error decrypting message: {e}')
			print(mp)
			return None



	def event_mqtt_connect(self, client, userdata, flags, rc, properties):
		'''
		Callback for when the client receives a CONNACK response from the server.

		:param client:     The client instance for this callback
		:param userdata:   The private user data as set in Client() or user_data_set()
		:param flags:      Response flags sent by the broker
		:param rc:         The connection result
		:param properties: The properties returned by the broker
		'''

		if rc == 0:
			client.subscribe(self.subscribe_topic)
		else:
			print(f'Failed to connect to MQTT broker: {rc}')


	def event_mqtt_recv(self, client, userdata, msg):
		'''
		Callback for when a message is received from the server.

		:param client:   The client instance for this callback
		:param userdata: The private user data as set in Client() or user_data_set()
		:param msg:      An instance of MQTTMessage
		'''
		
		try:
			# Define the service envelope
			service_envelope = mqtt_pb2.ServiceEnvelope()

			try:
				# Parse the message payload
				service_envelope.ParseFromString(msg.payload)
			except Exception as e:
				print(f'Error parsing service envelope: {e}')
				print(f'Raw payload: {msg.payload}')
				return

			# Extract the message packet from the service envelope
			mp = service_envelope.packet

			# Check if the message is encrypted before decrypting it
			if mp.HasField('encrypted'):
				decrypted_mp = self.decrypt_message_packet(mp)
				if decrypted_mp:
					mp = decrypted_mp
				else:
					return

			portnum_name = portnums_pb2.PortNum.Name(mp.decoded.portnum)

			# Skip if message type doesn't match filter
			if self.filters and portnum_name not in self.filters:
				return

			# Convert to JSON and handle NaN values in one shot
			json_packet = json.loads(MessageToJson(mp))

			# Replace all NaN values with null before any further processing
			def replace_nan(obj):
				'''
				Replace all NaN values with null before any further processing

				:param obj: The object to replace NaN values in
				'''
				if isinstance(obj, dict):
					return {k: replace_nan(v) for k, v in obj.items()}
				elif isinstance(obj, list):
					return [replace_nan(x) for x in obj]
				elif isinstance(obj, float) and str(obj).lower() == 'nan':
					return None
				elif isinstance(obj, str) and obj.lower() == 'nan':
					return None
				
				return obj

			json_packet = replace_nan(json_packet)

			# Process the message based on its type
			if mp.decoded.portnum == portnums_pb2.ADMIN_APP:
				data = mesh_pb2.Admin()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.ATAK_FORWARDER:
				data = mesh_pb2.AtakForwarder()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.ATAK_PLUGIN:
				data = mesh_pb2.AtakPlugin()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.AUDIO_APP:
				data = mesh_pb2.Audio()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.DETECTION_SENSOR_APP:
				data = mesh_pb2.DetectionSensor()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.IP_TUNNEL_APP:
				data = mesh_pb2.IPTunnel()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.NEIGHBORINFO_APP:
				neighborInfo = mesh_pb2.NeighborInfo()
				neighborInfo.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = json.loads(MessageToJson(neighborInfo))
				print(json.dumps(json_packet))

			elif mp.decoded.portnum == portnums_pb2.NODEINFO_APP:
				from_id = getattr(mp, 'from')
				node_info = mesh_pb2.User()
				node_info.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = json.loads(MessageToJson(node_info))
				print(json.dumps(json_packet))
				self.names[from_id] = node_info.long_name

			elif mp.decoded.portnum == portnums_pb2.PAXCOUNTER_APP:
				data = mesh_pb2.Paxcounter()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.POSITION_APP:
				position = mesh_pb2.Position()
				position.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = json.loads(MessageToJson(position))
				print(json.dumps(json_packet))

			elif mp.decoded.portnum == portnums_pb2.PRIVATE_APP:
				data = mesh_pb2.Private()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.RANGE_TEST_APP:
				data = mesh_pb2.RangeTest()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = json.loads(MessageToJson(data))
				print(json.dumps(json_packet))

			elif mp.decoded.portnum == portnums_pb2.REMOTE_HARDWARE_APP:
				data = mesh_pb2.RemoteHardware()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.REPLY_APP:
				data = mesh_pb2.Reply()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.ROUTING_APP:
				routing = mesh_pb2.Routing()
				routing.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = json.loads(MessageToJson(routing))
				print(json.dumps(json_packet))

			elif mp.decoded.portnum == portnums_pb2.SERIAL_APP:
				data = mesh_pb2.Serial()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.SIMULATOR_APP:
				data = mesh_pb2.Simulator()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.STORE_FORWARD_APP:
				print(f'{MessageToJson(mp)}')
				print(f'{mp.decoded.payload}')

			elif mp.decoded.portnum == portnums_pb2.TELEMETRY_APP:
				telemetry = telemetry_pb2.Telemetry()
				telemetry.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = json.loads(MessageToJson(telemetry))
				print(json.dumps(json_packet))

			elif mp.decoded.portnum == portnums_pb2.TEXT_MESSAGE_APP:
				text_payload = mp.decoded.payload.decode('utf-8')
				json_packet['decoded']['payload'] = text_payload
				print(json.dumps(json_packet))

			elif mp.decoded.portnum == portnums_pb2.TEXT_MESSAGE_COMPRESSED_APP:
				data = mesh_pb2.TextMessageCompressed()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.TRACEROUTE_APP:
					routeDiscovery = mesh_pb2.RouteDiscovery()
					routeDiscovery.ParseFromString(mp.decoded.payload)
					json_packet['decoded']['payload'] = json.loads(MessageToJson(routeDiscovery))
					print(json.dumps(json_packet))

			elif mp.decoded.portnum == portnums_pb2.WAYPOINT_APP:
				data = mesh_pb2.Waypoint()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			elif mp.decoded.portnum == portnums_pb2.ZPS_APP:
				data = mesh_pb2.Zps()
				data.ParseFromString(mp.decoded.payload)
				print(f'{MessageToJson(data)}')

			else:
				print(f'UNKNOWN: Received Portnum name: {portnum_name}')
				print(f'UNKNOWN: {MessageToJson(mp)}')

		except Exception as e:
			print(f'Error processing message: {e}')
			print(f'Topic: {msg.topic}')
			print(f'Payload: {msg.payload}')


def main():
    parser = argparse.ArgumentParser(description='Meshtastic MQTT Interface')
    parser.add_argument('--broker', default='mqtt.meshtastic.org', help='MQTT broker address')
    parser.add_argument('--port', default=1883, type=int, help='MQTT broker port')
    parser.add_argument('--root', default='msh/US/2/e/', help='Root topic')
    parser.add_argument('--channel', default='LongFast', help='Channel name')
    parser.add_argument('--username', default='meshdev', help='MQTT username')
    parser.add_argument('--password', default='large4cats', help='MQTT password')
    parser.add_argument('--key', default='AQ==', help='Encryption key')
    parser.add_argument('--filter', help='Filter message types (comma-separated). Example: NODEINFO,POSITION,TEXT_MESSAGE')
    args = parser.parse_args()

    client = MeshtasticMQTT()
    if args.filter:
        client.filters = [f'{f.strip()}_APP' for f in args.filter.upper().split(',')]
    else:
        client.filters = None
    client.connect(args.broker, args.port, args.root, args.channel, args.username, args.password, args.key)



if __name__ == '__main__':
    main() 