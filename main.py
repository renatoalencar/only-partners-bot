from itertools import groupby
import asyncio
import re

from google.cloud.firestore_v1 import DocumentSnapshot
from telethon import TelegramClient
# from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest
from firebase_admin import credentials
from firebase_admin import firestore
import firebase_admin


class Listener:
    def __init__(self, reference, loop):
        self.reference = reference
        self.loop = loop

        self.queue = asyncio.Queue()

    def listen(self):
        self.reference.on_snapshot(self.handle_snapshot)

    def handle_snapshot(self, doc_snapshot, _, __):
        self.loop.call_soon_threadsafe(self.queue.put_nowait, doc_snapshot)

    def get(self):
        return self.queue.get()

    def done(self):
        return self.queue.task_done()


class Worker:
    def __init__(self, listener, telegram):
        self.listener = listener
        self.telegram = telegram

    async def start(self):
        while True:
            try:
                doc_snapshot = await self.listener.get()

                for group, user, doc in self.get_entity_pairs(doc_snapshot):
                    group = await group
                    user = await user

                    await self.telegram(AddChatUserRequest(
                        group,
                        user,
                        fwd_limit=10
                    ))

                    doc.reference.update({ ':status': ':done' })

                self.listener.done()
            except Exception as exception:
                print("Error: ", exception)

                doc.reference.update({ ':status': ':failure' })

    def get_entity(self, entity):
        return self.telegram.get_entity(entity)

    def get_entity_pairs(self, docs):
        groups = groupby(docs, lambda x: x.to_dict().get(':telegram-group-id', None))

        for group_id, users in groups:
            group = self.get_entity(group_id)

            for user in users:
                yield group, self.get_entity(user.to_dict()[':telegram-user-id']), user


def get_db():
    cred = credentials.Certificate('./certificate.json')
    firebase_admin.initialize_app(cred, {
        'projectId': '[REDACTED]'
    })

    return firestore.client()


async def get_telegram():
    telegram = TelegramClient('[REDACTED]', 00000, '[REDACTED]')

    await telegram.connect()
    await telegram.get_dialogs()

    return telegram


async def main():
    db = get_db()
    telegram = await get_telegram()

    ref = db.collection('subscriptions').where('`:status`', '==', ':pending')
    listener = Listener(ref, asyncio.get_running_loop())
    worker = Worker(listener, telegram)

    listener.listen()
    await worker.start()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
