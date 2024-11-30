# Meshtastic MQTT Parser

A lightweight Python library for parsing Meshtastic MQTT messages into JSON format. This tool makes it easy to build applications that interact with Meshtastic mesh networks via MQTT.

## Overview

This library connects to a Meshtastic MQTT broker and decodes various message types into JSON format, making it simple to process Meshtastic mesh network data in your Python applications.

## Features

- Connects to any Meshtastic MQTT broker
- Decrypts encrypted messages
- Parses all standard Meshtastic message types
- Outputs clean JSON format
- Message type filtering support
- Simple command-line interface

## Installation 
```bash
pip install cryptography protobuf meshtastic paho-mqtt
```

## usage
```bash
python meshtastic_mqtt.py [options]
```


### Command Line Options

- `--broker`: MQTT broker address (default: mqtt.meshtastic.org)
- `--port`: MQTT broker port (default: 1883)
- `--root`: Root topic (default: msh/US/2/e/)
- `--channel`: Channel name (default: LongFast)
- `--username`: MQTT username (default: meshdev)
- `--password`: MQTT password (default: large4cats)
- `--key`: Encryption key (default: AQ==)
- `--filter`: Filter specific message types (comma-separated)

### Filter Example
```bash
python meshtastic_mqtt.py --filter "NODEINFO,POSITION,TEXT_MESSAGE"
```


## Supported Message Types

The library supports parsing of the following Meshtastic message types:

1. **ADMIN_APP**: Administrative messages
2. **ATAK_FORWARDER**: ATAK forwarding messages
3. **ATAK_PLUGIN**: ATAK plugin messages
4. **AUDIO_APP**: Audio messages
5. **DETECTION_SENSOR_APP**: Sensor detection data
6. **IP_TUNNEL_APP**: IP tunneling messages
7. **NEIGHBORINFO_APP**: Neighbor information
8. **NODEINFO_APP**: Node information and details
9. **PAXCOUNTER_APP**: People counter data
10. **POSITION_APP**: GPS position updates
11. **PRIVATE_APP**: Private messages
12. **RANGE_TEST_APP**: Range testing data
13. **REMOTE_HARDWARE_APP**: Remote hardware control
14. **REPLY_APP**: Reply messages
15. **ROUTING_APP**: Routing information
16. **SERIAL_APP**: Serial communication
17. **SIMULATOR_APP**: Simulator messages
18. **STORE_FORWARD_APP**: Store and forward messages
19. **TELEMETRY_APP**: Device telemetry data
20. **TEXT_MESSAGE_APP**: Plain text messages
21. **TEXT_MESSAGE_COMPRESSED_APP**: Compressed text messages
22. **TRACEROUTE_APP**: Network route tracing
23. **WAYPOINT_APP**: Waypoint information
24. **ZPS_APP**: Zone/Position System messages


## Building Applications

This library serves as a foundation for building more complex Meshtastic applications. Some possible uses:

- Message logging systems
- Position tracking applications
- Network monitoring tools
- Chat applications
- Telemetry data collection
- Mesh network analysis tools