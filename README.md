# xiaomu-firmware

**XiaoMu Main Control Firmware – Motor Control · Sensor Fusion · Multimodal Interaction**

[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-brightgreen)](https://docs.ros.org/en/humble/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)

---

## 📖 Overview

XiaoMu is an AI companion robot developed by **TIMU Technology**. It features an **on-device (offline) AI model**, supporting voice interaction, visual recognition, expressive feedback, and 5-DOF motion control — providing emotional companionship and daily interaction without requiring an internet connection.

This repository contains the open-source **brain (main control) firmware** for XiaoMu. It handles motion coordination, sensor data acquisition, expression display, voice interaction, and multimodal data fusion.

> **Note:** Currently, only the **brain** module is open-sourced. Behavior control, motor control, display control, and other modules will be gradually opened in the future.

---

## ✨ Key Features

- **Native ROS 2 Support** – Built on ROS 2 Humble with a node-based architecture for easy secondary development
- **Multi-DOF Motion Control** – Supports coordinated control of pitch, yaw, and Dock rotation
- **Multi-Sensor Fusion** – Integrates temperature/humidity, gyroscope, touch, vision, audio, and other sensor data
- **Expression & Behavior System** – Supports dynamic expressions, proactive behavior triggers, and personalized interaction
- **Offline AI Interaction** – On-device speech recognition, semantic understanding, and visual processing with local data privacy

---

## 📂 Repository Structure

```
xiaomu-firmware/
├── brain/                    # Main control core code
│   ├── brain/                # Python main control module
│   ├── resource/             # Expression, behavior, and other resource files
│   ├── test/                 # Test cases
│   ├── package.xml           # ROS 2 package dependency declaration
│   ├── setup.py              # Python package configuration
│   └── setup.cfg             # Installation configuration
├── LICENSE
└── README.md
```

---

## 🚀 Quick Start

### Requirements

- Ubuntu 22.04 (recommended)
- ROS 2 Humble
- Python 3.9+
- XiaoMu Programming Edition robot (for deployment)

### Build

```bash
# 1. Clone the repository
git clone https://github.com/TimuTechnology/xiaomu-firmware.git

# 2. Enter the workspace
cd xiaomu-firmware

# 3. Build the ROS 2 package
colcon build --packages-select brain

# 4. Source the environment
source install/setup.bash
```

### Run

```bash
# Launch the main control node
ros2 launch brain brain_launch.py
```

> **Note:** For specific launch commands, please refer to the `package.xml` and launch files under the `brain/` directory. Startup methods may vary slightly between firmware versions.

---

## 🔗 Related Resources

| Resource | Link |
| :--- | :--- |
| **Official Store** | [https://store.timuai.com](https://store.timuai.com) |
| **API Docs & Examples** | [senling-xiaomu-ros2-api-examples](https://github.com/TimuTechnology/senling-xiaomu-ros2-api-examples) |
| **GitHub Organization** | [TimuTechnology](https://github.com/TimuTechnology) |
| **YouTube Channel** | [@timurobot](https://www.youtube.com/@timurobot) |

---

## 🤝 Contributing

We welcome community contributions! Whether it's fixing bugs, adding new features, or improving documentation, you can get involved by:

1. Forking this repository
2. Creating a feature branch (`git checkout -b feature/your-feature`)
3. Committing your changes (`git commit -m 'Add some feature'`)
4. Pushing to the branch (`git push origin feature/your-feature`)
5. Submitting a Pull Request

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)** – see the [LICENSE](LICENSE) file for details.

AGPL-3.0 is a strong copyleft license. In simple terms, you are free to use, modify, and distribute this software, but if you run a modified version on a network server and provide access to others, you must also make the corresponding source code available under the same license. For commercial use that does not comply with AGPL-3.0, please contact us for a separate commercial license.

---

## 📬 Contact

- **Email:** wangjing@timuai.com
- **Website:** https://store.timuai.com

---

*XiaoMu is still young, and so are we. Let's make her better together.* ❤️
