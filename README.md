# 💬 discord-adbot

A **Discord selfbot** system that uses multiple tokens to advertise messages in public channels (like LFG servers) and respond to direct messages (DMs) — but only once per user.

> ⚠️ **Disclaimer**  
> Automating user accounts (selfbots) is strictly against [Discord’s Terms of Service](https://discord.com/terms). This project is for **educational use only**. Use it at your own risk — you are responsible for any consequences.

---

## ✨ Features

- Mass messaging using **multiple Discord tokens**
- Automatic DM replies (one-time per user)
- Custom cooldowns to bypass post delays (e.g., 2-hour LFG cooldowns)
- Cross-platform support (Windows, Linux, macOS)
- Optional use of `screen` for persistent Linux sessions

---

## 🛠️ Setup Instructions

### 1. Install Python 3.12  
[Download it here](https://www.python.org/downloads/)

---

### 2. Install Dependencies

Install the required development version of `discord.py-self` and `asyncio`:

```bash
git clone https://github.com/dolfies/discord.py-self
cd discord.py-self
python3 -m pip install -U .[voice]
python3 -m pip install asyncio
```

---

### 3. Clone This Repo

```bash
git clone https://github.com/millson1/discord-adbot
cd discord-adbot
```

---

## 🔧 Configuration

### A) `discord_selfbot_script.py`

- **Line 14:** Set your target `CHANNEL_ID`
- **Line 17:** Define your message(s)
- **DM reply message:** Inside the `handle_dm()` function
- **Cooldown timing:** At the bottom (`asyncio.sleep(...)` inside `on_ready()`)

---

### B) `Bots.py` (Auto-starter for multiple tokens)

This script handles launching all your bots with staggered timing.

#### Settings:

- Add your tokens in the `tokens = [...]` list.
- Adjust `launch_delay` to match your channel's cooldown period divided by number of tokens.
  - Example: Channel cooldown is 2 hours (7200 seconds), and you have 3 tokens → use `launch_delay = 2400` (40 minutes).

#### Example:

```python
tokens = ["token1", "token2", "token3"]
launch_delay = 40 * 60  # 40 minutes in seconds
```

#### Run it:

```bash
python Bots.py
```

- On Windows: opens in new terminals
- On Linux/macOS: uses `screen` if available, otherwise `subprocess`

---

## 📌 Notes

- You can change the behavior of DM replies or turn them off completely by removing the `on_message` handler.
- Consider using **virtual machines or containers** if you're running multiple bots long-term.
- Always test on throwaway accounts.

---

## 📞 Support / Questions

This project is community-built and unofficial. Use GitHub Issues for bugs or suggestions.

---

## 🧪 Educational Purpose Only

This repo is meant to demonstrate how automation works with Python + Discord. Abuse of this code could get your account permanently banned — be smart.
