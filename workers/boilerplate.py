import asyncio
import logging
import signal
import time
from common.redis_client import RedisClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
shutdown_event = asyncio.Event()

WORKER_ID = "placeholder_worker"

redis = RedisClient(loop=loop, worker_id=WORKER_ID)

@redis.listen("event:dummy_in")
async def handle_dummy_event(data):
    logger.info(f"[{WORKER_ID}] Received dummy event: {data}")

async def heartbeat_loop():
    while not shutdown_event.is_set():
        try:
            await redis.heartbeat()
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
        await asyncio.sleep(1)

async def publish_dummy_event():
    message = {
        "worker_id": WORKER_ID,
        "event": "dummy_event",
        "timestamp": time.time()
    }
    try:
        await redis.publish("event:dummy_out", message)
        logger.info(f"[{WORKER_ID}] Sent dummy event: {message}")
    except Exception as e:
        logger.error(f"Publish failed: {e}")

async def worker_job():
    # implement entire worker logic here
    # here we just send a dummy event, this could be replaced with real work
    await publish_dummy_event()

async def main(loop):
    await redis.connect()

    startup_mode = await redis.get_startup_mode()
    logger.info(f"[{WORKER_ID}] Starting in {startup_mode} mode")

    # since this is a dummy worker, we just log the mode
    # but in real worker if theres a different behaviour for recovery mode, tasks[] would be adjusted accordingly
    tasks = [
        loop.create_task(heartbeat_loop()),
        loop.create_task(worker_job())
    ]

    await shutdown_event.wait()

    logger.info(f"[{WORKER_ID}] Shutting down...")
    for task in tasks:
        task.cancel()

    await redis.close()

def handle_shutdown():
    logger.info("Shutdown signal received")
    shutdown_event.set()

def runner():
    # Handle SIGINT / SIGTERM (PM2 compatible)
    # this is commented out to avoid issues on Windows
    # for sig in (signal.SIGINT, signal.SIGTERM):
    #     loop.add_signal_handler(sig, handle_shutdown)

    try:
        loop.run_until_complete(main(loop))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        handle_shutdown()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

if __name__ == "__main__":
    runner()