import json
import os

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from flask_mqtt import Mqtt
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)
load_dotenv('.env')

AIO_USERNAME = os.environ.get('AIO_USERNAME')
app.config['MQTT_BROKER_URL'] = os.environ.get('AIO_SERVER')
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = AIO_USERNAME
app.config['MQTT_PASSWORD'] = os.environ.get('AIO_KEY')
app.config['MQTT_KEEPALIVE'] = 30
AIO_FEED_SUBSCRIBE = os.environ.get('AIO_FEED_SUBSCRIBE')
AIO_FEED_SEND = os.environ.get('AIO_FEED_SEND')
SEND_FEED = f"{AIO_USERNAME}/feeds/{AIO_FEED_SEND}"

mqtt_client = Mqtt(app)
current_next_student_id = ""


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to MQTT broker")
        mqtt_client.subscribe(f"{AIO_USERNAME}/feeds/{AIO_FEED_SUBSCRIBE}")
    else:
        print(f"Failed to connect, return code {rc}")


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    message_type = data['messageType']

    if message_type == 'update':
        global current_next_student_id
        queue = data['queue']
        if len(queue) > 0:
            current_next = queue[0]
            if current_next:
                current_next_student_id = current_next['studentNumber']
        socketio.emit('queue_update', data)


@socketio.on('fetch_queue')
def fetch_queue():
    mqtt_client.publish(SEND_FEED, b"{\"messageType\": \"fetch\"}")


@app.route('/')
def dashboard():
    return render_template('page.html')


@app.route('/kick', methods=['POST'])
def kick():
    body = request.get_json()
    student_number = f"{body['studentNumber']}"
    string_to_send = b"{\"messageType\":\"cancel\",\"studentNumber\":\"" + student_number.encode() + b"\"}"
    mqtt_client.publish(SEND_FEED, string_to_send)
    return jsonify({"success": True}), 200


@app.route('/force-next', methods=['POST'])
def force_next():
    body = request.get_json()
    student_number = f"{body['studentNumber']}"
    string_to_send = b"{\"messageType\":\"next\",\"studentNumber\":\"" + student_number.encode() + b"\"}"
    mqtt_client.publish(SEND_FEED, string_to_send)
    return jsonify({"success": True}), 200


@app.route('/away-from-desk', methods=['POST'])
def away_from_desk():
    mqtt_client.publish(SEND_FEED, b"{\"messageType\": \"away\"}")
    return jsonify({"success": True}), 200


@app.route('/finish-current-student', methods=['POST'])
def finish_current_student():
    string_to_send = b"{\"messageType\":\"next\",\"studentNumber\":\"\"}"
    mqtt_client.publish(SEND_FEED, string_to_send)
    return jsonify({"success": True}), 200


@app.route('/call-next-student', methods=['POST'])
def call_next_student():
    student_number = f"{current_next_student_id}"
    string_to_send = b"{\"messageType\":\"next\",\"studentNumber\":\"" + student_number.encode() + b"\"}"
    mqtt_client.publish(SEND_FEED, string_to_send)
    return jsonify({"success": True}), 200


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True)
