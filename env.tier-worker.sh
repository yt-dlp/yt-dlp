# PMOVES.AI Tier Environment: Worker
# For background worker services (extract, langextract, media analyzers, etc.)
# Source after env.shared: source env.shared && source env.tier-worker.sh

# ============================================================================
# Worker Tier Configuration
# ============================================================================

export TIER=worker

# Worker limits
export MAX_CONCURRENT_JOBS=${MAX_CONCURRENT_JOBS:-10}
export JOB_TIMEOUT_MS=${JOB_TIMEOUT_MS:-600000}  # 10 minutes
export JOB_QUEUE_SIZE=${JOB_QUEUE_SIZE:-100}

# Job retry configuration
export JOB_RETRY_MAX=${JOB_RETRY_MAX:-3}
export JOB_RETRY_DELAY_MS=${JOB_RETRY_DELAY_MS:-5000}
export JOB_BACKOFF_MULTIPLIER=${JOB_BACKOFF_MULTIPLIER:-2}

# Worker pool configuration
export WORKER_POOL_SIZE=${WORKER_POOL_SIZE:-4}
export WORKER_PREFETCH_MULTIPLIER=${WORKER_PREFETCH_MULTIPLIER:-2}
export WORKER_ACK_DEADLINE_MS=${WORKER_ACK_DEADLINE_MS:-300000}  # 5 minutes

# NATS JetStream for job queue
export WORKER_JETSTREAM_ENABLED=${WORKER_JETSTREAM_ENABLED:-true}
export WORKER_CONSUMER_GROUP=${WORKER_CONSUMER_GROUP:-workers}
export WORKER_DURABLE_NAME=${WORKER_DURABLE_NAME:-worker-durable}

# Job result storage
export JOB_RESULT_BACKEND=${JOB_RESULT_BACKEND:-supabase}  # supabase | minio | memory
export JOB_RESULT_TTL=${JOB_RESULT_TTL:-86400}  # 24 hours

# Progress reporting
export PROGRESS_REPORTING_ENABLED=${PROGRESS_REPORTING_ENABLED:-true}
export PROGRESS_REPORT_INTERVAL_MS=${PROGRESS_REPORT_INTERVAL_MS:-5000}

# Media processing (for media workers)
export MEDIA_MAX_FILE_SIZE_MB=${MEDIA_MAX_FILE_SIZE_MB:-500}
export MEDIA_TIMEOUT_MS=${MEDIA_TIMEOUT_MS:-1800000}  # 30 minutes
export MEDIA_QUALITY=${MEDIA_QUALITY:-high}

# Embedding configuration (for extract/ indexing workers)
export EMBEDDING_MODEL=${EMBEDDING_MODEL:-all-MiniLM-L6-v2}
export EMBEDDING_DIMENSION=${EMBEDDING_DIMENSION:-384}
export EMBEDDING_BATCH_SIZE=${EMBEDDING_BATCH_SIZE:-32}

# Text processing (for language workers)
export TEXT_MAX_LENGTH=${TEXT_MAX_LENGTH:-1000000}
export TEXT_CHUNK_SIZE=${TEXT_CHUNK_SIZE:-1000}
export TEXT_CHUNK_OVERLAP=${TEXT_CHUNK_OVERLAP:-200}
