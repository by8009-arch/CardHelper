#!/usr/bin/env python3
"""
自動將 CardHelper 完整連接至 Hermes Agent 與 Telegram Bot 的安裝腳本
"""
import os
import shutil
import subprocess
import time

PROJECT_DIR = "/Users/arraymac/Desktop/project/CardHelper"
HERMES_DIR = os.path.expanduser("~/.hermes")
SKILL_SRC = os.path.join(PROJECT_DIR, "hermes_skill", "SKILL.md")
BOT_SRC = os.path.join(PROJECT_DIR, "telegram_cardhelper_bot.py")
BOT_DST = os.path.expanduser("~/telegram_bot.py")


def main():
    # 1. 安裝 Skill 到 ~/.hermes/skills/cardhelper/SKILL.md 與 ~/.hermes/skills/productivity/cardhelper/SKILL.md
    for rel_dir in ["cardhelper", os.path.join("productivity", "cardhelper")]:
        target_dir = os.path.join(HERMES_DIR, "skills", rel_dir)
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy2(SKILL_SRC, os.path.join(target_dir, "SKILL.md"))
        print(f"[OK] Installed SKILL.md -> {target_dir}/SKILL.md")

    # 2. 清除 Hermes 舊的 .skills_prompt_snapshot.json 快取，強制重新索引 Skill
    snapshot_path = os.path.join(HERMES_DIR, ".skills_prompt_snapshot.json")
    if os.path.exists(snapshot_path):
        os.remove(snapshot_path)
        print(f"[OK] Cleared stale skill snapshot: {snapshot_path}")

    # 3. 更新 ~/.hermes/config.yaml (設定預設模型為 google/gemma-4-e4b 並掛載 cardhelper MCP server)
    config_path = os.path.join(HERMES_DIR, "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 將無法載入的 26b 模型改為可正常運行的 google/gemma-4-e4b
        content = content.replace(
            'default: "google/gemma-4-26b-a4b-qat"',
            'default: "google/gemma-4-e4b"',
        )
        if "mcp_servers:" not in content:
            content += (
                "\nmcp_servers:\n"
                "  cardhelper:\n"
                "    command: \"/usr/bin/python3\"\n"
                f"    args:\n      - \"{PROJECT_DIR}/cardhelper_mcp.py\"\n"
            )
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Updated {config_path} (model.default + mcp_servers.cardhelper)")

    # 4. 重啟 CardHelper server.py (確保釋放 8765 port)
    try:
        pids = subprocess.check_output(
            ["/usr/sbin/lsof", "-t", "-i", ":8765", "-sTCP:LISTEN"],
            text=True
        ).strip().splitlines()
        for pid in pids:
            if pid.strip():
                subprocess.run(["kill", "-9", pid.strip()], check=False)
    except Exception:
        pass
    subprocess.run(["pkill", "-9", "-f", "server.py"], check=False)
    time.sleep(0.5)
    srv_log = open(os.path.join(PROJECT_DIR, "server.log"), "w", encoding="utf-8")
    srv_proc = subprocess.Popen(
        ["/usr/bin/python3", "-u", os.path.join(PROJECT_DIR, "server.py")],
        cwd=PROJECT_DIR,
        stdout=srv_log,
        stderr=srv_log,
        start_new_session=True,
    )
    print(f"[OK] Restarted CardHelper server.py (PID={srv_proc.pid})")

    # 5. 更新 /Users/arraymac/telegram_bot.py 並重啟 Telegram Bot
    shutil.copy2(BOT_SRC, BOT_DST)
    print(f"[OK] Updated Telegram bot script -> {BOT_DST}")

    subprocess.run(["pkill", "-f", "telegram_bot.py"], check=False)
    subprocess.run(["pkill", "-f", "telegram_cardhelper_bot.py"], check=False)
    time.sleep(1.0)

    log_path = os.path.join(PROJECT_DIR, "telegram_bot.log")
    out_f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["/usr/bin/python3", BOT_DST],
        cwd=PROJECT_DIR,
        stdout=out_f,
        stderr=out_f,
        start_new_session=True,
    )
    time.sleep(2.0)
    print(f"[OK] Started Telegram Bot (PID={proc.pid}), log={log_path}")


if __name__ == "__main__":
    main()
