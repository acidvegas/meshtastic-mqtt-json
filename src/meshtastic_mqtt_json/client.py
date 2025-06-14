#!/usr/bin/env python
# Meshtastic MQTT Interface - Developed by acidvegas in Python (https://acid.vegas/meshtastic_mqtt_json)

import argparse
import base64
import json
import time

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


def clean_json(data) -> dict:
	'''
	Clean the JSON data by replacing NaN values with null

	:param data: The JSON data to clean
	'''
	# Handle protobuf messages
	if hasattr(data, 'DESCRIPTOR'):
		data = json.loads(MessageToJson(data))

	# Remove empty and NaN values from the JSON data
	if isinstance(data, dict):
		return {k: v for k, v in ((k, clean_json(v)) for k, v in data.items()) if str(v) not in ('None', 'nan', '')}
	elif isinstance(data, list):
		return [v for v in (clean_json(v) for v in data) if str(v) not in ('None', 'nan', '')]

	# Return primitive types as-is
	return data


class MeshtasticMQTT(object):
	def __init__(self):
		'''Initialize the Meshtastic MQTT client'''

		self.broadcast_id = 4294967295 # Our channel ID
		self.key          = None
		self.names        = {}
		self.filters      = None
		self.callbacks    = {}  # Dictionary to store message type callbacks


	def register_callback(self, message_type: str, callback: callable):
		'''
		Register a callback function for a specific message type

		:param message_type: The message type to register for (e.g. 'TEXT_MESSAGE_APP', 'POSITION_APP')
		:param callback:     The callback function to call when a message of this type is received
		'''
		if not message_type.endswith('_APP'):
			message_type = f'{message_type}_APP'
		self.callbacks[message_type] = callback


	def unregister_callback(self, message_type: str):
		'''
		Unregister a callback function for a specific message type

		:param message_type: The message type to unregister
		'''
		if not message_type.endswith('_APP'):
			message_type = f'{message_type}_APP'
		if message_type in self.callbacks:
			del self.callbacks[message_type]


	def _handle_message(self, mp, json_packet: dict, portnum_name: str):
		'''
		Handle a message by calling registered callbacks

		:param mp:           The message packet
		:param json_packet:  The JSON representation of the packet
		:param portnum_name: The name of the port number
		'''
		# Call registered callback if one exists
		if portnum_name in self.callbacks:
			self.callbacks[portnum_name](json_packet)
		else:
			# Default behavior - print to console
			print(f'{json.dumps(json_packet)}')


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
		client.connect_timeout = 10

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
		client.on_connect    = self.event_mqtt_connect
		client.on_message    = self.event_mqtt_recv
		client.on_disconnect = self.event_mqtt_disconnect

		# Connect to the MQTT broker
		try:
			client.connect(broker, port, 60)
		except Exception as e:
			print(f'Error connecting to MQTT broker: {e}')
			self.event_mqtt_disconnect(client, '', 1, None)

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
			cipher = Cipher(algorithms.AES(self.key_bytes), modes.CTR(nonce), backend=default_backend())
			decryptor = cipher.decryptor()
			decrypted_bytes = decryptor.update(getattr(mp, 'encrypted')) + decryptor.finalize()

			# Parse the decrypted message
			data = mesh_pb2.Data()
			try:
				data.ParseFromString(decrypted_bytes)
			except:
				# Ignore this as the message does not need to be decrypted
				return None

			mp.decoded.CopyFrom(data)

			return mp

		except Exception as e:
			print(f'Error decrypting message: {e}')
			print(f'Message packet details:')
			print(f'- From: {getattr(mp, "from", "unknown")}')
			print(f'- To: {getattr(mp, "to", "unknown")}')
			print(f'- Channel: {getattr(mp, "channel", "unknown")}')
			print(f'- ID: {getattr(mp, "id", "unknown")}')
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
			json_packet = clean_json(mp)

			# Process the message based on its type
			if mp.decoded.portnum == portnums_pb2.ADMIN_APP:
				data = mesh_pb2.Admin()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.ATAK_FORWARDER:
				data = mesh_pb2.AtakForwarder()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.ATAK_PLUGIN:
				data = mesh_pb2.AtakPlugin()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.AUDIO_APP:
				data = mesh_pb2.Audio()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.DETECTION_SENSOR_APP:
				data = mesh_pb2.DetectionSensor()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.IP_TUNNEL_APP:
				data = mesh_pb2.IPTunnel()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.MAP_REPORT_APP:
				map_report = mesh_pb2.MapReport()
				map_report.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(map_report)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.NEIGHBORINFO_APP:
				neighborInfo = mesh_pb2.NeighborInfo()
				neighborInfo.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(neighborInfo)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.NODEINFO_APP:
				from_id = getattr(mp, 'from')
				node_info = mesh_pb2.User()
				node_info.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(node_info)
				self._handle_message(mp, json_packet, portnum_name)
				self.names[from_id] = node_info.long_name

			elif mp.decoded.portnum == portnums_pb2.PAXCOUNTER_APP:
				data = mesh_pb2.Paxcounter()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.POSITION_APP:
				position = mesh_pb2.Position()
				position.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(position)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.PRIVATE_APP:
				data = mesh_pb2.Private()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.RANGE_TEST_APP:
				data = mesh_pb2.RangeTest()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.REMOTE_HARDWARE_APP:
				data = mesh_pb2.RemoteHardware()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.REPLY_APP:
				data = mesh_pb2.Reply()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.ROUTING_APP:
				routing = mesh_pb2.Routing()
				routing.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(routing)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.SERIAL_APP:
				data = mesh_pb2.Serial()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.SIMULATOR_APP:
				data = mesh_pb2.Simulator()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.STORE_FORWARD_APP:
				json_packet['decoded']['payload'] = mp.decoded.payload
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.TELEMETRY_APP:
				telemetry = telemetry_pb2.Telemetry()
				telemetry.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(telemetry)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.TEXT_MESSAGE_APP:
				text_payload = mp.decoded.payload.decode('utf-8')
				json_packet['decoded']['payload'] = text_payload
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.TEXT_MESSAGE_COMPRESSED_APP:
				data = mesh_pb2.TextMessageCompressed()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.TRACEROUTE_APP:
				routeDiscovery = mesh_pb2.RouteDiscovery()
				routeDiscovery.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(routeDiscovery)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.UNKNOWN_APP:
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.WAYPOINT_APP:
				data = mesh_pb2.Waypoint()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			elif mp.decoded.portnum == portnums_pb2.ZPS_APP:
				data = mesh_pb2.Zps()
				data.ParseFromString(mp.decoded.payload)
				json_packet['decoded']['payload'] = clean_json(data)
				self._handle_message(mp, json_packet, portnum_name)

			else:
				print(f'UNKNOWN: Received Portnum name: {portnum_name}')
				self._handle_message(mp, json_packet, portnum_name)

		except Exception as e:
			print(f'Error processing message: {e}')
			print(f'Topic: {msg.topic}')
			print(f'Payload: {msg.payload}')


	def event_mqtt_disconnect(self, client, userdata, rc, packet_from_broker=None, properties=None, reason_code=None):
		'''Callback for when the client disconnects from the server.'''
		print(f'Disconnected with result code: {rc}')
		while True:
			print('Attempting to reconnect...')
			try:
				client.reconnect()
			except Exception as e:
				print(f'Error reconnecting to MQTT broker: {e}')
				time.sleep(5)
			else:
				print('Reconnected to MQTT broker')
				break


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
