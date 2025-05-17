# BalanceManager Module

A Python module for managing the `balance.json` file in a Discord Bot economy system. Supports real-time reading/writing, command monitoring, automatic backups, and data change tracking—ideal for high-control economic data management.

## Features

* 📖 Real-time reading and writing of `balance.json`
* 🔐 Write-lock protection to ensure data consistency
* 🗂 Automatic backup before writing new data
* 🧠 Support for comparing and logging data changes
* 🧩 Decorator to monitor if commands modify the data

## Requirements

* Compatible with both `discord.py` and `py-cord`

* Python 3.8+

* aiofiles

* discord.py or py-cord 2.x

## Usage

### 1. Initialize BalanceManager

```python
from balance_manager import BalanceManager

balance = BalanceManager("balance.json")  # Optional, defaults to balance.json
```

### 2. Read and Write

```python
data = await balance.read()

data["123456789"] = {"money": 500}
await balance.write(data, actor="admin", reason="manual update")
```

### 3. Use Updater for Automatic Updates

```python
async def add_money(user_id: str, amount: int):
    async def updater(data):
        data.setdefault(user_id, {"money": 0})
        data[user_id]["money"] += amount
        return data

    await balance.update(updater, actor=user_id, reason=f"add {amount} coins")
```

### 4. Monitor Command Changes with Decorator

```python
from balance_manager import track_balance_command

@bot.tree.command()
@track_balance_command(balance)
async def balance_add(interaction: discord.Interaction, amount: int):
    # Modify balance.json here
    ...
```

## Log Example

```
📅 balance.json update successful by 123456789 for add 100 coins
🔄 balance.json changes: {'123456789': {'before': {'money': 400}, 'after': {'money': 500}}}
```

## License

MIT
