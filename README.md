[https://t.me/safos_tgbot](https://t.me/safos_tgbot)

# Safos Telegram Bot

**Telegram bot for managing orders via the Safos Backend**

Safos Telegram Bot is the client-side interface for the **Safos Backend**, allowing **Admins, Agents, and Dostavchiks** to manage orders, track statuses, and interact with the business system directly from Telegram.

> ⚠️ **Important:** Users must be **registered by an Admin** on the backend to use the bot. All actions, buttons, and data are handled through the backend server.

---

## Table of Contents

* [Overview](#overview)
* [Key Features](#key-features)
* [Technology Stack](#technology-stack)
* [Getting Started](#getting-started)

  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Environment Variables](#environment-variables)
  * [Running Locally](#running-locally)
* [Usage](#usage)
* [Contributing](#contributing)

---

## Overview

This bot works as the **user interface** for your order management system. Users can:

* Access the system based on their role (Admin, Agent, Dostavchik)
* Create, update, delete, and complete orders using buttons and Telegram commands
* Track order statuses in real time
* Communicate with the backend server seamlessly

All interactions are **processed via Safos Backend**, ensuring that business logic and data integrity are maintained.

---

## Key Features

* 🔐 **Role-based access**: Admin, Agent, Dostavchik
* 📦 **Order management**: create, update, delete, complete
* 📊 **View performance and order stats** (via backend)
* 📲 **Telegram-friendly interface**: buttons, inline commands, and messages
* ⚙️ **All actions handled by the backend** for consistency and security

---

## Technology Stack

* **Language**: Python
* **Telegram API**: python-telegram-bot
* **HTTP Requests**: httpx, requests
* **Async Handling**: anyio, sniffio, h11
* **Environment Management**: python-dotenv

**Dependencies**:

```
anyio==4.11.0
certifi==2025.10.5
charset-normalizer==3.4.3
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.10
python-dotenv==1.1.1
python-telegram-bot==22.5
requests==2.32.5
sniffio==1.3.1
typing_extensions==4.15.0
urllib3==2.5.0
```

---

## Getting Started

### Prerequisites

* Python 3.9+
* A running instance of **Safos Backend**
* Telegram account with a bot token

---

### Installation

```bash
git clone https://github.com/asliddintursunoff/Safos-Telegram.git
cd Safos-Telegram
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# OR
venv\Scripts\activate      # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

### Environment Variables

Create a `.env` file with your Telegram bot token and backend URL:

```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
BACKEND_URL=https://your-backend-url.com
```

---

### Running Locally

```bash
python bot.py
```

The bot will start and listen for commands from registered users.

---

## Usage

* Only users **registered by Admin** in the backend can interact with the bot.
* The bot interface is fully button-driven: all commands and actions are available via inline keyboards.
* Example workflow:

  1. Admin registers a new Agent
  2. Agent opens Telegram, interacts with the bot, and creates an order
  3. Dostavchik sees the order and completes it

All actions are **automatically synced with the backend**.

---

## Contributing

```bash
1. Fork the repository
2. Create a new branch: git checkout -b feature/NewFeature
3. Commit your changes: git commit -m "Add new feature"
4. Push to your branch: git push origin feature/NewFeature
5. Open a Pull Request
```
