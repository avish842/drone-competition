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

WORKER_ID = "path_planning_worker"

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

shutdown_event = asyncio.Event()
redis = RedisClient(loop=loop, worker_id=WORKER_ID)

occupancy_grid = [[0]*100 for _ in range(100)]  # placeholder grid

@redis.listen("event:planning_request")
async def handle_planning_request(data):
    """
    Triggered when Mission Manager requests a new waypoint.
    Payload may include:
    - drone_id
    - target_type (scout / sprayer)
    - target_position (optional)
    """
    logger.info(f"[{WORKER_ID}] Planning request received: {data}")
    # TODO: enqueue planning job or update internal state

@redis.listen("event:occupancy_grid_updated")
async def handle_occupancy_grid_update(data):
    """
    Triggered when LiDAR worker updates the occupancy grid.
    """
    logger.debug(f"[{WORKER_ID}] Occupancy grid update event")
    # TODO: refresh local grid cache

@redis.listen("event:drone_pose_update")
async def handle_drone_pose_update(data):
    """
    Triggered when Mission Manager updates drone pose.
    Payload may include:
    - drone_id
    - position (x, y, z)
    - yaw
    """
    logger.debug(f"[{WORKER_ID}] Drone pose update: {data}")
    # TODO: update internal pose state

@redis.listen("event:crop_detected")
async def handle_crop_detected(data):
    """
    Triggered when Camera Worker detects a diseased crop.
    Payload may include:
    - crop_id
    - gps_position
    - confidence
    """
    logger.info(f"[{WORKER_ID}] Crop detected event: {data}")
    # TODO: register crop and plan path for sprayer drone

async def heartbeat_loop():
    """Send heartbeat periodically to Supervisor"""
    while not shutdown_event.is_set():
        try:
            await redis.heartbeat()
        except Exception as e:
            logger.error(f"[{WORKER_ID}] Heartbeat error: {e}")
        await asyncio.sleep(1)


async def planning_loop():
    """
    Main planning loop.
    This loop should:
    - check internal planning state
    - compute next waypoint (later)
    - publish result to Mission Manager
    """
    while not shutdown_event.is_set():
        # TODO: implement planning decision logic
        await asyncio.sleep(0.1)


async def publish_waypoint(drone_id, waypoint):
    """
    Publish a planned waypoint to Mission Manager.
    """
    message = {
        "drone_id": drone_id,
        "waypoint": waypoint,
        "timestamp": time.time()
    }

    try:
        await redis.publish("event:planned_waypoint", message)
        logger.info(f"[{WORKER_ID}] Waypoint published: {message}")
    except Exception as e:
        logger.error(f"[{WORKER_ID}] Failed to publish waypoint: {e}")


async def publish_no_safe_path(drone_id):
    """
    Notify Mission Manager that no safe path exists.
    """
    message = {
        "drone_id": drone_id,
        "reason": "NO_SAFE_PATH",
        "timestamp": time.time()
    }

    try:
        await redis.publish("event:no_safe_path", message)
        logger.warning(f"[{WORKER_ID}] No safe path for {drone_id}")
    except Exception as e:
        logger.error(f"[{WORKER_ID}] Failed to publish no-path event: {e}")

async def main(loop):
    global occupancy_grid

    await redis.connect()

    # Load initial occupancy grid from Redis
    occupancy_grid = await redis.client.get("occupancy_grid") or occupancy_grid

    startup_mode = await redis.get_startup_mode()
    logger.info(f"[{WORKER_ID}] Starting in {startup_mode} mode")

    tasks = [
        loop.create_task(heartbeat_loop()),
        loop.create_task(planning_loop()),
    ]

    await shutdown_event.wait()

    logger.info(f"[{WORKER_ID}] Shutting down...")
    for task in tasks:
        task.cancel()

    await redis.close()

def handle_shutdown():
    logger.info(f"[{WORKER_ID}] Shutdown signal received")
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
        logger.error(f"[{WORKER_ID}] Fatal error: {e}")
    finally:
        handle_shutdown()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

if __name__ == "__main__":
    runner()
