import sqlite3
from datetime import datetime
import threading
import os

class DetectionDatabase:
    def __init__(self, db_path='data/detections.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Veritabanını ve tabloları oluştur"""
        # Klasör yoksa oluştur
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ana kayıt tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    person_count INTEGER NOT NULL,
                    confidence_avg REAL,
                    source TEXT
                )
            ''')
            
            # Saatlik özet tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hourly_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour_start DATETIME,
                    total_detections INTEGER,
                    avg_person_count REAL,
                    max_person_count INTEGER,
                    min_person_count INTEGER
                )
            ''')
            
            # Günlük özet tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    total_detections INTEGER,
                    avg_person_count REAL,
                    max_person_count INTEGER,
                    peak_hour TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
    
    def add_detection(self, person_count, confidence_avg=None, source='camera'):
        """Yeni tespit kaydı ekle"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO detections (person_count, confidence_avg, source)
                VALUES (?, ?, ?)
            ''', (person_count, confidence_avg, source))
            
            conn.commit()
            detection_id = cursor.lastrowid
            conn.close()
            
            return detection_id
    
    def get_recent_detections(self, limit=100):
        """Son N kaydı getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, person_count, confidence_avg, source
            FROM detections
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_statistics(self, hours=24):
        """İstatistikleri getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_detections,
                AVG(person_count) as avg_persons,
                MAX(person_count) as max_persons,
                MIN(person_count) as min_persons
            FROM detections
            WHERE person_count > 0 AND timestamp >= datetime('now', '-' || ? || ' hours')
        ''', (hours,))
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            'total_detections': stats[0],
            'avg_persons': round(stats[1], 2) if stats[1] else 0,
            'max_persons': stats[2] if stats[2] else 0,
            'min_persons': stats[3] if stats[3] else 0
        }
    
    def get_hourly_data(self, hours=24):
        """Saatlik grafik verisi"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                AVG(person_count) as avg_count,
                MAX(person_count) as max_count,
                COUNT(*) as detection_count
            FROM detections
            WHERE timestamp >= datetime('now', '-' || ? || ' hours')
            GROUP BY hour
            ORDER BY hour
        ''', (hours,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def clear_old_data(self, days=30):
        """Eski kayıtları temizle"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM detections
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            ''', (days,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count

    def export_data(self, period='all'):
        """Verileri dışa aktar (CSV için)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT id, timestamp, person_count, confidence_avg, source FROM detections"
        params = ()
        
        if period == '24hours':
            query += " WHERE timestamp >= datetime('now', '-24 hours')"
        elif period == '7days':
            query += " WHERE timestamp >= datetime('now', '-7 days')"
        elif period == '30days':
            query += " WHERE timestamp >= datetime('now', '-30 days')"
            
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results