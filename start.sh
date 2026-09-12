#!/usr/bin/env bash
# 本机开发一键启动 / 停止：Postgres+Qdrant（Docker）、本机 Redis、Ollama、后端、前端。
# tunnel：把前端 :5173 转到临时 HTTPS 公网地址（仅转发本机端口，不暴露数据库 / Ollama）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${ROOT}/.run"
JWT_SECRET_DEFAULT="change-me-to-a-long-random-string"
CLOUDFLARED_RELEASE="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

mkdir -p "${RUN_DIR}"

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn | grep -qE ":${port}[[:space:]]"
  else
    return 1
  fi
}

wait_http() {
  local url="$1" name="$2" tries="${3:-40}" maxt="${4:-2}"
  local i
  for i in $(seq 1 "${tries}"); do
    if curl -fsS -o /dev/null --max-time "${maxt}" "${url}" 2>/dev/null; then
      log "  ${name} ready"
      return 0
    fi
    sleep 0.5
  done
  die "${name} did not become ready: ${url}"
}

ensure_env() {
  if [[ ! -f "${ROOT}/.env" ]]; then
    cp "${ROOT}/.env.example" "${ROOT}/.env"
  fi
  if [[ ! -f "${ROOT}/backend/.env" ]]; then
    cp "${ROOT}/backend/.env.example" "${ROOT}/backend/.env"
  fi
  if [[ ! -f "${ROOT}/frontend/.env" && -f "${ROOT}/frontend/.env.example" ]]; then
    cp "${ROOT}/frontend/.env.example" "${ROOT}/frontend/.env"
  fi
}

export_jwt_from_backend_env() {
  if [[ -n "${JWT_SECRET:-}" ]]; then
    export JWT_SECRET
    return 0
  fi
  local envf="${ROOT}/backend/.env"
  [[ -f "${envf}" ]] || return 0
  local line
  line="$(grep -E '^[[:space:]]*JWT_SECRET=' "${envf}" | tail -n 1 || true)"
  [[ -n "${line}" ]] || return 0
  JWT_SECRET="${line#*=}"
  JWT_SECRET="${JWT_SECRET%\"}"
  JWT_SECRET="${JWT_SECRET#\"}"
  JWT_SECRET="${JWT_SECRET%\'}"
  JWT_SECRET="${JWT_SECRET#\'}"
  export JWT_SECRET
}

start_infra() {
  command -v docker >/dev/null 2>&1 || die "docker not found"
  docker compose -f "${ROOT}/docker-compose.yml" up -d postgres qdrant
  if command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1; then
    log "  redis: host service on :6379"
  else
    docker compose -f "${ROOT}/docker-compose.yml" up -d redis
    log "  redis: docker :6379"
  fi
  command -v ollama >/dev/null 2>&1 || die "ollama not found; install from https://ollama.com"
  if ! curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:11434/api/tags; then
    die "Ollama is not answering on 127.0.0.1:11434"
  fi
  ollama list | grep -q 'qwen3-embedding:0.6b' || ollama pull qwen3-embedding:0.6b
  ollama list | grep -q 'qwen2.5:1.5b' || ollama pull qwen2.5:1.5b
}

kill_port() {
  local port="$1"
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  fi
}

spawn_session() {
  local name="$1" dir="$2"
  shift 2
  if command -v setsid >/dev/null 2>&1; then
    (
      cd "${dir}" || exit 1
      exec setsid "$@"
    ) >"${RUN_DIR}/${name}.log" 2>&1 &
  else
    (
      cd "${dir}" || exit 1
      exec "$@"
    ) >"${RUN_DIR}/${name}.log" 2>&1 &
  fi
  echo $! >"${RUN_DIR}/${name}.pid"
}

start_backend() {
  if port_in_use 8000; then
    local pid=""
    [[ -f "${RUN_DIR}/backend.pid" ]] && pid="$(cat "${RUN_DIR}/backend.pid" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      log "  backend already on :8000"
      return 0
    fi
    log "  freeing leftover :8000"
    kill_port 8000
    sleep 0.3
  fi
  if [[ ! -d "${ROOT}/backend/.venv" ]]; then
    (cd "${ROOT}/backend" && uv sync --python 3.12 --extra dev)
  fi
  spawn_session backend "${ROOT}/backend" uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
}

start_frontend() {
  if port_in_use 5173; then
    local pid=""
    [[ -f "${RUN_DIR}/frontend.pid" ]] && pid="$(cat "${RUN_DIR}/frontend.pid" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      log "  frontend already on :5173"
      return 0
    fi
    log "  freeing leftover :5173"
    kill_port 5173
    sleep 0.3
  fi
  if [[ ! -d "${ROOT}/frontend/node_modules" ]]; then
    (cd "${ROOT}/frontend" && npm install)
  fi
  spawn_session frontend "${ROOT}/frontend" npm run dev -- --host 127.0.0.1 --port 5173
}

stop_pidfile() {
  local pidfile="$1"
  [[ -f "${pidfile}" ]] || return 0
  local pid
  pid="$(cat "${pidfile}" || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    kill -- "-${pid}" 2>/dev/null || kill "${pid}" 2>/dev/null || true
    sleep 0.4
    kill -9 -- "-${pid}" 2>/dev/null || kill -9 "${pid}" 2>/dev/null || true
  fi
  rm -f "${pidfile}"
}

cloudflared_bin() {
  if command -v cloudflared >/dev/null 2>&1; then
    command -v cloudflared
    return 0
  fi
  if [[ -x "${RUN_DIR}/cloudflared" ]]; then
    printf '%s\n' "${RUN_DIR}/cloudflared"
    return 0
  fi
  return 1
}

ensure_cloudflared() {
  if cloudflared_bin >/dev/null; then
    return 0
  fi
  command -v curl >/dev/null 2>&1 || die "curl not found (needed to download cloudflared)"
  log "  downloading cloudflared..."
  curl -fsSL -o "${RUN_DIR}/cloudflared" "${CLOUDFLARED_RELEASE}"
  chmod +x "${RUN_DIR}/cloudflared"
  "${RUN_DIR}/cloudflared" --version >/dev/null || die "cloudflared download failed"
}

read_tunnel_url() {
  [[ -f "${RUN_DIR}/tunnel.log" ]] || return 1
  grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "${RUN_DIR}/tunnel.log" | tail -n 1
}

wait_tunnel_url() {
  local tries="${1:-60}" i url pid
  for i in $(seq 1 "${tries}"); do
    url="$(read_tunnel_url || true)"
    if [[ -n "${url}" ]]; then
      printf '%s\n' "${url}"
      return 0
    fi
    if [[ -f "${RUN_DIR}/tunnel.pid" ]]; then
      pid="$(cat "${RUN_DIR}/tunnel.pid" || true)"
      if [[ -n "${pid}" ]] && ! kill -0 "${pid}" 2>/dev/null; then
        die "cloudflared exited; see ${RUN_DIR}/tunnel.log"
      fi
    fi
    sleep 0.5
  done
  die "tunnel URL not found; see ${RUN_DIR}/tunnel.log"
}

cmd_stop() {
  stop_pidfile "${RUN_DIR}/tunnel.pid"
  rm -f "${RUN_DIR}/tunnel.url"
  stop_pidfile "${RUN_DIR}/frontend.pid"
  stop_pidfile "${RUN_DIR}/backend.pid"
  stop_pidfile "${RUN_DIR}/backend2.pid"
  stop_pidfile "${RUN_DIR}/backend1.pid"
  if port_in_use 8000; then
    kill_port 8000
  fi
  if port_in_use 5173; then
    kill_port 5173
  fi
  log "stopped app processes and tunnel (Postgres/Qdrant/Redis/Ollama left running)"
}

cmd_start() {
  ensure_env
  log "starting infra..."
  start_infra
  log "starting apps..."
  start_backend
  start_frontend
  wait_http "http://127.0.0.1:8000/api/v1/health" "backend" 50
  wait_http "http://127.0.0.1:5173/" "frontend" 50
  log "seeding knowledge/sdnu..."
  export_jwt_from_backend_env
  (cd "${ROOT}/backend" && uv run python "${ROOT}/scripts/seed_sdnu_kb.py")
  log ""
  log "ready"
  log "  frontend   http://127.0.0.1:5173"
  log "  backend    http://127.0.0.1:8000/docs"
  log "  tenant     sdnu-demo"
  log "  logs       ${RUN_DIR}/"
  log "  stop       ${ROOT}/start.sh stop"
  log "  public     ${ROOT}/start.sh tunnel"
  log "JWT_SECRET default ${JWT_SECRET_DEFAULT} (set in backend/.env)"
}

cmd_tunnel() {
  export_jwt_from_backend_env
  if [[ "${JWT_SECRET:-${JWT_SECRET_DEFAULT}}" == "${JWT_SECRET_DEFAULT}" ]]; then
    log "WARNING: JWT_SECRET is the demo placeholder; the public URL shares that secret."
  fi
  cmd_start
  ensure_cloudflared
  local bin url pid
  bin="$(cloudflared_bin)" || die "cloudflared not found"
  if [[ -f "${RUN_DIR}/tunnel.pid" ]]; then
    pid="$(cat "${RUN_DIR}/tunnel.pid" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      url="$(read_tunnel_url || true)"
      if [[ -n "${url}" ]]; then
        printf '%s\n' "${url}" >"${RUN_DIR}/tunnel.url"
        log "tunnel already running"
        log "  public     ${url}"
        log "  local      http://127.0.0.1:5173"
        log "  stop       ${ROOT}/start.sh stop"
        return 0
      fi
    fi
  fi
  : >"${RUN_DIR}/tunnel.log"
  nohup "${bin}" tunnel --url http://127.0.0.1:5173 --no-autoupdate \
    >"${RUN_DIR}/tunnel.log" 2>&1 &
  echo $! >"${RUN_DIR}/tunnel.pid"
  log "waiting for public URL..."
  url="$(wait_tunnel_url 80)"
  printf '%s\n' "${url}" >"${RUN_DIR}/tunnel.url"
  wait_http "${url}" "public tunnel" 40 10
  log ""
  log "ready (temporary public HTTPS; URL changes each start)"
  log "  public     ${url}"
  log "  local      http://127.0.0.1:5173"
  log "  stop       ${ROOT}/start.sh stop"
}

case "${1:-start}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_stop; cmd_start ;;
  tunnel) cmd_tunnel ;;
  *) die "usage: $0 [start|stop|restart|tunnel]" ;;
esac
