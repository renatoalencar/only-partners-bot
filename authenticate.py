from telethon import TelegramClient, errors
import asyncio

telegram = TelegramClient('[REDACTED]', '[REDACTED]', '[REDACTED}')


async def main():
    await telegram.connect()

    phone = input('Phone: ')

    sent = await telegram.send_code_request(phone)
    print(sent)

    code = input('Code: ')
    password = input('Password: ')

    try:
        auth = await telegram.sign_in(phone, code)
    except errors.SessionPasswordNeededError:
        auth = await telegram.sign_in(phone, None, password=password)

    print(auth)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
