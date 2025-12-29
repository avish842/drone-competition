# Distributed System with Node.js Supervisor and Python Workers

A distributed system architecture using Node.js for supervision, Python for workers, PM2 for process management, and Redis for inter-process communication.

## Architecture

```
┌─────────────────────────────────────────────┐
│          PM2 Process Manager                │
└─────────────────────────────────────────────┘
          │           │           │
          ▼           ▼           ▼
┌──────────────┐  ┌────────┐  ┌────────┐
│  Supervisor  │  │Worker A│  │Worker B│
│   (Node.js)  │  │(Python)│  │(Python)│
└──────┬───────┘  └───┬────┘  └───┬────┘
       │              │            │
       └──────────────┴────────────┘
                  │
            ┌─────▼─────┐
            │   Redis   │
            │    IPC    │
            └───────────┘
```

## Components

### Supervisor (Node.js)

-   Dispatches tasks to worker queues
-   Monitors worker responses and heartbeats
-   Manages task distribution and system status
-   Located in `supervisor/supervisor.js`

### Workers (Python)

-   **Worker A**: Processes computational tasks
-   **Worker B**: Performs analysis operations
-   Both workers:
    -   Poll Redis queues for tasks
    -   Send heartbeats to supervisor
    -   Return results via Redis pub/sub

### Redis Communication

-   **Task Queues**: `queue:worker_a`, `queue:worker_b`
-   **Response Channel**: `worker:responses`
-   **Heartbeat Channel**: `worker:heartbeat`

### PM2 Configuration

-   Manages all processes (1 supervisor + 4 workers)
-   Auto-restart on failure
-   Memory limits and monitoring
-   Configured in `ecosystem.config.js`

## Prerequisites

### Required Software

-   **Node.js** (v14 or higher)
-   **Python** (v3.7 or higher)
-   **Redis Server** (v5 or higher)
-   **PM2** (global installation)

### Installation

1. **Install Redis**

    ```bash
    # Windows (using Chocolatey)
    choco install redis-64

    # Or download from: https://github.com/microsoftarchive/redis/releases
    ```

2. **Install PM2**

    ```bash
    npm install -g pm2
    ```

3. **Install Node.js Dependencies**

    ```bash
    npm init -y
    npm install ioredis
    ```

4. **Install Python Dependencies**
    ```bash
    pip install redis
    ```

## Usage

### Starting Redis

```bash
# Windows
redis-server

# Or as a service
redis-server --service-start
```

### Starting the System

```bash
# Start all processes with PM2
pm2 start ecosystem.config.js

# View status
pm2 status

# View logs
pm2 logs

# View specific process logs
pm2 logs supervisor
pm2 logs worker_a
pm2 logs worker_b
```

### Monitoring

```bash
# Real-time monitoring dashboard
pm2 monit

# View detailed process info
pm2 show supervisor

# Check system status
pm2 list
```

### Stopping the System

```bash
# Stop all processes
pm2 stop all

# Stop specific process
pm2 stop supervisor

# Delete all processes from PM2
pm2 delete all
```

### Restarting Processes

```bash
# Restart all
pm2 restart all

# Restart specific process
pm2 restart worker_a

# Reload without downtime
pm2 reload all
```

## Configuration

### Environment Variables

Edit `ecosystem.config.js` to configure:

-   `REDIS_HOST`: Redis server hostname (default: localhost)
-   `REDIS_PORT`: Redis server port (default: 6379)
-   `WORKER_ID`: Worker identifier
-   `NODE_ENV`: Node environment (production/development)

### Scaling Workers

```bash
# Scale worker_a to 4 instances
pm2 scale worker_a 4

# Scale worker_b to 3 instances
pm2 scale worker_b 3
```

## Task Flow

1. **Supervisor** creates a task and pushes it to a Redis queue:

    ```javascript
    queue:worker_a → [task_1, task_2, ...]
    ```

2. **Worker** polls the queue and retrieves a task:

    ```python
    task = redis.brpop('queue:worker_a', timeout=2)
    ```

3. **Worker** processes the task and publishes the result:

    ```python
    redis.publish('worker:responses', json.dumps(result))
    ```

4. **Supervisor** receives the result via subscription:
    ```javascript
    subscriber.on("message", handleWorkerResponse);
    ```

## Heartbeat System

Workers send periodic heartbeats every 10 seconds:

```json
{
	"worker_id": "worker_a_12345",
	"pid": 12345,
	"tasks_processed": 42,
	"timestamp": 1735468800.0
}
```

## Troubleshooting

### Redis Connection Issues

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Check Redis logs
redis-cli monitor
```

### Worker Not Processing Tasks

1. Check PM2 logs: `pm2 logs worker_a`
2. Verify Redis connection
3. Check queue length: `redis-cli LLEN queue:worker_a`

### PM2 Process Crashes

```bash
# View error logs
pm2 logs --err

# Restart with fresh state
pm2 delete all
pm2 start ecosystem.config.js
```

### Performance Tuning

-   Adjust `instances` in `ecosystem.config.js` for scaling
-   Modify `max_memory_restart` for memory limits
-   Tune Redis persistence settings for throughput
-   Adjust task timeout values in workers

## Development

### Running Manually (without PM2)

**Supervisor:**

```bash
node supervisor/supervisor.js
```

**Workers:**

```bash
python workers/worker_a.py
python workers/worker_b.py
```

### Testing Components

**Test Redis connection:**

```bash
redis-cli
> SET test "hello"
> GET test
> DEL test
```

**Monitor Redis pub/sub:**

```bash
redis-cli
> SUBSCRIBE worker:responses
> SUBSCRIBE worker:heartbeat
```

**Check queues:**

```bash
redis-cli
> LLEN queue:worker_a
> LRANGE queue:worker_a 0 -1
```

## Production Considerations

1. **Redis Persistence**: Configure RDB/AOF for data durability
2. **PM2 Startup**: Configure PM2 to start on system boot
    ```bash
    pm2 startup
    pm2 save
    ```
3. **Monitoring**: Integrate with PM2 Plus or other monitoring tools
4. **Load Balancing**: Scale workers based on queue depth
5. **Error Handling**: Implement dead letter queues for failed tasks
6. **Security**: Use Redis AUTH and configure firewall rules

## License

MIT
