# ⚠️ WARNING ⚠️

This markdown file was vibe coded.

---

# 🔄 DFU Tools  
### Device Firmware Update (DFU) Host Application for STM32F103

A lightweight **host-side DFU implementation** for programming **STM32F103** microcontrollers.

This tool provides essential bootloader communication features such as flash erase, write, read, RDP control, and more.

---

## ✨ Features

- Communicates with STM32 custom bootloader
- Flash erase / write / read support
- Readout Protection (RDP) control
- Chip identification
- Bootloader version detection
- Modular command structure

---

## 📦 Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Baksi675/dfutools.git
cd dfutools
```

### 2️⃣ Create a Virtual Environment

```bash
python3 -m venv .venv
```

### 3️⃣ Activate the Virtual Environment

```bash
source .venv/bin/activate
```

### 4️⃣ Install in Editable Mode

```bash
pip install -e .
```

---

## 🚀 Usage

### Show All Commands

```bash
dfutools --help
```

### Show Help for a Specific Command

```bash
dfutools <command> --help
```

---

## 🧩 Available Commands

| Command      | Description |
|--------------|------------|
| `get-ver`    | Get bootloader version |
| `get-cmds`   | Get available command list |
| `get-cid`    | Get MCU chip ID |
| `get-rdp`    | Get MCU flash RDP status |
| `set-rdp`    | Set MCU flash RDP status |
| `get-wrp`    | Get MCU flash WRP status |
| `set-wrp`    | Set MCU flash WRP status |
| `erase`      | Erase the flash |
| `write`      | Write to the flash |
| `read`       | Read from the flash |
| `program`    | Erase then writes to the flash |
| `jump`       | Jump to the specified address |
| `rst`        | Reset the MCU |

---

## 🛠 Example

Get bootloader version:

```bash
dfutools get-ver -p /dev/ttyUSB0
```

Set RDP protection:

```bash
dfutools set-rdp -e enable -p /dev/ttyUSB0
```

---

## 📄 License

This project is free to use and modify.  

---

## ⭐ Support

If this project helps you, consider giving it a ⭐ on GitHub!
