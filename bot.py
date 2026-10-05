import os
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SERVER_URL = os.environ["SERVER_URL"].rstrip("/")

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    return requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
        params=params,
        timeout=40
    ).json()

def main():
    offset = None

    while True:
        data = get_updates(offset)

        for update in data.get("result", []):
            offset = update["update_id"] + 1

            msg = update.get("message", {})
            chat = msg.get("chat", {})
            text = msg.get("text", "")
            telegram_id = str(chat.get("id", ""))

            if text == "/start":
                try:
                    r = requests.post(
                        SERVER_URL + "/telegram/start",
                        json={"telegram_id": telegram_id},
                        timeout=10
                    )

                    if r.status_code == 200:
                        requests.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": telegram_id,
                                "text": "Your activation request was accepted. Check the activation-code message."
                            },
                            timeout=10
                        )
                    else:
                        requests.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": telegram_id,
                                "text": "Access denied."
                            },
                            timeout=10
                        )

                except Exception:
                    pass

if __name__ == "__main__":
    main()
