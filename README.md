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
| Option       | Description                                          |
| ------------ | ---------------------------------------------------- |
| `--broker`   | MQTT broker address *(default: mqtt.meshtastic.org)* |
| `--port`     | MQTT broker port *(default: 1883)*                   |
| `--root`     | Root topic *(default: msh/US/2/e/)*                  |
| `--channel`  | Channel name *(default: LongFast)*                   |
| `--username` | MQTT username *(default: meshdev)*                   |
| `--password` | MQTT password *(default: large4cats)*                |
| `--key`      | Encryption key *(default: AQ==)*                     |
| `--filter`   | Filter specific message types *(comma-separated)*    |

### Filter Example
```bash
python meshtastic_mqtt.py --filter "NODEINFO,POSITION,TEXT_MESSAGE"
```


## Supported Message Types

The library supports parsing of the following Meshtastic message types:
| Message Type                    | Description                   |
| ------------------------------- | ----------------------------- |
| **ADMIN_APP**                   | Administrative messages       |
| **ATAK_FORWARDER**              | ATAK forwarding messages      |
| **ATAK_PLUGIN**                 | ATAK plugin messages          |
| **AUDIO_APP**                   | Audio messages                |
| **DETECTION_SENSOR_APP**        | Sensor detection data         |
| **IP_TUNNEL_APP**               | IP tunneling messages         |
| **NEIGHBORINFO_APP**            | Neighbor information          |
| **NODEINFO_APP**                | Node information and details  |
| **PAXCOUNTER_APP**              | People counter data           |
| **POSITION_APP**                | GPS position updates          |
| **PRIVATE_APP**                 | Private messages              |
| **RANGE_TEST_APP**              | Range testing data            |
| **REMOTE_HARDWARE_APP**         | Remote hardware control       |
| **REPLY_APP**                   | Reply messages                |
| **ROUTING_APP**                 | Routing information           |
| **SERIAL_APP**                  | Serial communication          |
| **SIMULATOR_APP**               | Simulator messages            |
| **STORE_FORWARD_APP**           | Store and forward messages    |
| **TELEMETRY_APP**               | Device telemetry data         |
| **TEXT_MESSAGE_APP**            | Plain text messages           |
| **TEXT_MESSAGE_COMPRESSED_APP** | Compressed text messages      |
| **TRACEROUTE_APP**              | Network route tracing         |
| **WAYPOINT_APP**                | Waypoint information          |
| **ZPS_APP**                     | Zone/Position System messages |


## Building Applications

This library serves as a foundation for building more complex Meshtastic applications. Some possible uses:

- Message logging systems
- Position tracking applications
- Network monitoring tools
- Chat applications
- Telemetry data collection
- Mesh network analysis tools

___

###### Mirrors for this repository: [acid.vegas](https://git.acid.vegas/meshtastic_mqtt) • [SuperNETs](https://git.supernets.org/acidvegas/meshtastic_mqtt) • [GitHub](https://github.com/acidvegas/meshtastic_mqtt) • [GitLab](https://gitlab.com/acidvegas/meshtastic_mqtt) • [Codeberg](https://codeberg.org/acidvegas/meshtastic_mqtt)
