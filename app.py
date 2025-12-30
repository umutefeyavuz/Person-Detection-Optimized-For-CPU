import eventlet
eventlet.monkey_patch()

import sys
import os

# PyInstaller ile paketlendiğinde doğru path'i bul
def get_base_path():
    if getattr(sys, 'frozen', False):
        # exe'nin bulunduğu ana dizin
        return os.path.dirname(sys.executable)
    else:
        # Normal Python ile çalışıyorsa
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

# Klasörleri hem ana dizinde hem de _internal altında ara
def find_data_folder(folder_name):
    # Öncelikli arama klasörleri
    possible_paths = [
        os.path.join(BASE_PATH, folder_name), # Ana dizin
        os.path.join(BASE_PATH, '_internal', folder_name), # PyInstaller dizini
    ]
    
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        possible_paths.append(os.path.join(sys._MEIPASS, folder_name))

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return os.path.join(BASE_PATH, folder_name)

TEMPLATE_PATH = find_data_folder('templates')
STATIC_PATH = find_data_folder('static')
MODELS_PATH = find_data_folder('models')
DATA_PATH = os.path.join(BASE_PATH, 'data')

print(f">>> LUNET AI BAŞLATILIYOR <<<")
print(f"DEBUG: EXE_PATH: {sys.executable}")
print(f"DEBUG: BASE_PATH: {BASE_PATH}")
print(f"DEBUG: TEMPLATES: {TEMPLATE_PATH}")

# Modül importları
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import threading
import time
import base64
from database import DetectionDatabase
from detection import Detector

app = Flask(__name__, template_folder=TEMPLATE_PATH, static_folder=STATIC_PATH)
app.config['SECRET_KEY'] = 'lunet-ai-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Durum yönetimi için sözlük
app_state = {
    'camera': None,
    'detection_active': False,
    'person_count': 0,
    'last_db_update': 0,
    'confidence_threshold': 0.45,
    'auto_record': True
}

db = DetectionDatabase(db_path=os.path.join(DATA_PATH, 'detections.db'))
detector = None

def get_detector():
    global detector
    if detector is None:
        model_path = os.path.join(MODELS_PATH, 'model.onnx')
        try:
            print(f"Model yükleniyor: {model_path}")
            from detection import Detector
            detector = Detector(
                model_path=model_path, 
                input_shape=(192, 192), 
                score_th=app_state['confidence_threshold'], 
                nms_th=0.35,
                num_threads=4
            )
            print("Lunet AI Model Yüklendi Başarıyla!")
        except Exception as e:
            import traceback
            print(f"Model yükleme hatası: {e}")
            traceback.print_exc()
            detector = None
    return detector

def draw_detections(frame, bboxes, scores, class_ids):
    if bboxes is None or len(bboxes) == 0:
        return frame
    
    for i in range(len(bboxes)):
        bbox = bboxes[i]
        score = scores[i]
        x1, y1, x2, y2 = bbox.astype(int)
        
        h, w = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        # Çerçeve çiz (Lunet AI Yeşili)
        color = (94, 197, 34) 
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        label = f"Person: {score:.2f}"
        (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - label_h - 5), (x1 + label_w, y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
    return frame

def generate_frames():
    current_detector = get_detector()
    
    if app_state['camera'] is None:
        app_state['camera'] = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        time.sleep(1)

    while True:
        if app_state['camera'] is None or not app_state['camera'].isOpened():
            time.sleep(1)
            app_state['camera'] = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            continue
            
        success, frame = app_state['camera'].read()
        if not success:
            print("Kamera okuma hatası!")
            time.sleep(0.1)
            continue
        
        # Durum bilgisi
        is_active = app_state['detection_active']
        status_text = "DURUM: AKTIF" if is_active else "DURUM: BEKLEMEDE"
        status_color = (0, 255, 0) if is_active else (0, 0, 255)
        cv2.putText(frame, status_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)

        person_count = 0
        avg_confidence = 0.0
        
        if is_active and current_detector:
            try:
                # Debug log (çok sık olmaması için her 30 karede bir)
                if int(time.time() * 10) % 30 == 0:
                    pass
                    
                bboxes, scores, class_ids = current_detector.inference(frame)
                
                if bboxes is not None and len(bboxes) > 0:
                    person_count = len(bboxes)
                    frame = draw_detections(frame, bboxes, scores, class_ids)
                    
                avg_confidence = float(np.mean(scores)) if len(scores) > 0 else 0.0
                
                # Veritabanına kaydet (her 5 saniyede bir ve auto_record açıksa VE kişi varsa)
                current_time = time.time()
                if app_state['auto_record'] and (current_time - app_state['last_db_update'] >= 5) and person_count > 0:
                    app_state['last_db_update'] = current_time
                    threading.Thread(target=db.add_detection, args=(person_count, avg_confidence)).start()
                
                socketio.emit('detection_update', {
                    'person_count': person_count,
                    'timestamp': current_time
                })
            except Exception as e:
                print(f"Detection hatası: {e}")
        
        try:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"Frame encode hatası: {e}")
            continue
            
        # Eventlet için sleep (Thread yield) - ÇOK ÖNEMLİ
        eventlet.sleep(0.01)

@app.route('/')
def index():
    return render_template('index.html', active_page='index')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html', active_page='analytics')

@app.route('/settings')
def settings():
    return render_template('settings.html', active_page='settings')

# Socket.IO Event Handlers
@socketio.on('connect')
def handle_connect():
    print(f"!!! CLIENT BAGLANDI: {request.sid} !!!")
    # Mevcut durumu gönder
    status = 'started' if app_state['detection_active'] else 'stopped'
    emit('status_response', {'status': status, 'active': app_state['detection_active']})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"!!! CLIENT AYRILDI: {request.sid} !!!")

@socketio.on('start_detection')
def handle_start_detection():
    print(f"!!! SOCKET START ALINDI !!!")
    app_state['detection_active'] = True
    emit('status_response', {'status': 'started', 'active': True}, broadcast=True) # Herkese bildir

@socketio.on('stop_detection')
def handle_stop_detection():
    print(f"!!! SOCKET STOP ALINDI !!!")
    app_state['detection_active'] = False
    emit('status_response', {'status': 'stopped', 'active': False}, broadcast=True) # Herkese bildir

@socketio.on('get_settings')
def handle_get_settings():
    """Ayarları istemciye gönder"""
    emit('settings_update', {
        'confidence_threshold': app_state['confidence_threshold'],
        'auto_record': app_state['auto_record']
    })

@socketio.on('update_settings')
def handle_update_settings(data):
    """Ayarları güncelle"""
    global detector
    print(f"AYAR GÜNCELLEME: {data}")
    
    if 'confidence_threshold' in data:
        new_th = float(data['confidence_threshold'])
        app_state['confidence_threshold'] = new_th
        if detector:
            detector.score_th = new_th
            
    if 'auto_record' in data:
        app_state['auto_record'] = bool(data['auto_record'])
        
    # Herkese yeni ayarları bildir
    emit('settings_update', {
        'confidence_threshold': app_state['confidence_threshold'],
        'auto_record': app_state['auto_record']
    }, broadcast=True)

@app.route('/api/statistics')
def get_statistics():
    hours = request.args.get('hours', 24, type=int)
    stats = db.get_statistics(hours)
    return jsonify(stats)

@app.route('/api/recent_detections')
def get_recent_detections():
    limit = request.args.get('limit', 100, type=int)
    detections = db.get_recent_detections(limit)
    result = []
    for det in detections:
        result.append({
            'id': det[0],
            'timestamp': det[1],
            'person_count': det[2],
            'confidence': det[3],
            'source': det[4]
        })
    return jsonify(result)

@app.route('/api/hourly_data')
def get_hourly_data():
    hours = request.args.get('hours', 24, type=int)
    results = db.get_hourly_data(hours)
    
    # JSON listesi oluştur
    json_results = []
    for r in results:
        json_results.append({
            'hour': r[0],
            'avg_count': round(r[1], 2) if r[1] else 0,
            'max_count': r[2],
            'detection_count': r[3]
        })
    return jsonify(json_results)

@app.route('/api/export_csv')
def export_csv():
    period = request.args.get('period', 'all')
    data = db.export_data(period)
    
    # CSV içeriğini oluştur
    csv_output = "ID,Timestamp,Person Count,Confidence,Source\n"
    for row in data:
        # Confidence değeri None olabilir, kontrol et
        conf = f"{row[3]:.2f}" if row[3] is not None else "0.00"
        csv_output += f"{row[0]},{row[1]},{row[2]},{conf},{row[4]}\n"
        
    filename = f"lunet_detections_{period}_{int(time.time())}.csv"
    
    return Response(
        csv_output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
