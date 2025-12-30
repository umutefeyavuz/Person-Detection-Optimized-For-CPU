# Lunet AI – CPU-Optimized Person Detection System

Lunet AI is a real-time person detection and counting system engineered for CPU-only environments. It is designed to deliver stable performance on low-power or edge devices such as Raspberry Pi, mini PCs, and standard desktop systems without requiring GPU acceleration.

The system combines a lightweight inference pipeline with a web-based monitoring dashboard, enabling reliable deployment in production and enterprise environments.

## Overview

Lunet AI provides real-time video processing, person detection, statistical logging, and monitoring through a unified, cross-platform architecture. It is suitable for surveillance, analytics, access monitoring, and smart facility use cases where GPU resources are unavailable or undesirable.

## Key Features

### CPU-Optimized Inference
Efficient detection pipeline optimized for OpenCV DNN to maintain high FPS on standard processors.

### Real-Time Video Streaming
Live MJPEG stream with bounding boxes, detection status indicators, and overlay information.

### Detection Analytics & Persistence
Automatic logging of detections into a thread-safe SQLite database with:
- Time-based statistics
- Hourly and daily summaries
- Confidence aggregation

### Web-Based Dashboard
Responsive dashboard built with Flask and Socket.IO, providing live updates without page refresh.

### Cross-Platform Support
Runs natively on:
- Linux (including ARM / Raspberry Pi)
- Windows (desktop and packaged executable)

### Standalone Deployment
Can be packaged into a single executable for environments where Python is not installed.

## Technology Stack

- **Backend**: Python 3.11, Flask, Flask-SocketIO (Eventlet)
- **Computer Vision**: OpenCV (DNN module), NumPy
- **Database**: SQLite (thread-safe access)
- **Frontend**: HTML5, Vanilla JavaScript, CSS

## Installation (Development Environment)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Person-Detection-Optimized-For-CPU.git
   cd Person-Detection-Optimized-For-CPU
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / macOS
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

The web dashboard will be available at: `http://localhost:5000`

## Camera Support

- Supports USB cameras via V4L2 (Linux) and DirectShow (Windows)
- Automatic camera reconnection on disconnect
- Multiple `/dev/video*` devices supported on Linux
- Designed for long-running, unattended operation

## Enterprise & Production Deployment

### Windows – Standalone Executable
Lunet AI can be packaged into a standalone executable using PyInstaller, enabling zero-dependency deployment on Windows systems.

```bash
python -m PyInstaller \
  --name "LunetAI_PersonDetection" \
  --add-data "templates;templates" \
  --add-data "static;static" \
  --add-data "models;models" \
  --hidden-import "eventlet" \
  --hidden-import "eventlet.hubs.epolls" \
  --hidden-import "eventlet.hubs.kqueue" \
  --hidden-import "eventlet.hubs.selects" \
  --hidden-import "engineio.async_drivers.eventlet" \
  --hidden-import "flask_socketio" \
  --hidden-import "greenlet._greenlet" \
  --collect-submodules "dns" \
  --exclude-module "onnxruntime" \
  --exclude-module "tensorflow" \
  --noconfirm \
  --clean \
  app.py
```

### Linux / Raspberry Pi
- Fully compatible with Debian Bookworm
- ARM64 supported
- Can be deployed as a systemd service for automatic startup and crash recovery

## Performance Characteristics

- Designed for CPU-only inference
- Stable memory usage during long runtimes
- Suitable for edge devices and low-resource systems
- Tested on Raspberry Pi and Windows desktop environments

## Use Cases

- Smart building occupancy monitoring
- Access control analytics
- Security and surveillance systems
- Edge AI deployments
- Educational and research projects

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

Developed by **Lunet AI**
*Focused on efficient, deployable, and production-ready AI systems.*
