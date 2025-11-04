#!/usr/bin/env bash
set -euo pipefail

# =========================== CONFIG ===========================
APP_NAME="support-bot"
BIN_NAME="s-b"
DEFAULT_INSTALL_DIR="/opt/${APP_NAME}"
INSTALL_DIR="${INSTALL_DIR:-${DEFAULT_INSTALL_DIR}}"
REPO_URL="https://github.com/mrtesla07/support-bot.git"
ENV_FILE=""
EXAMPLE_FILE=""
COMPOSE_DIR=""

# Укажите URL «сырой» версии ЭТОГО скрипта для самообновления (например, GitHub Raw/Gist Raw).
# Пример: UPDATE_URL="https://raw.githubusercontent.com/you/yourrepo/main/s-b"
UPDATE_URL="https://raw.githubusercontent.com/mrtesla07/support-bot/main/scripts/s-b.sh"

SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"

update_paths() {
  INSTALL_DIR="${INSTALL_DIR%/}"
  [[ -z "${INSTALL_DIR}" ]] && INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
  ENV_FILE="${INSTALL_DIR}/.env"
  EXAMPLE_FILE="${INSTALL_DIR}/.env.example"
  COMPOSE_DIR="${INSTALL_DIR}"
}

normalize_install_dir() {
  # Expand ~ if present
  if [[ "${INSTALL_DIR}" == ~* ]]; then
    INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"
  fi
  update_paths
}

prompt_install_dir() {
  normalize_install_dir
  echo
  read -r -p "Каталог установки [${INSTALL_DIR}]: " in_dir || true
  if [[ -n "${in_dir:-}" ]]; then
    INSTALL_DIR="${in_dir%/}"
    normalize_install_dir
  fi
  if [[ ! -d "${INSTALL_DIR}" ]]; then
    warn "Каталог ${INSTALL_DIR} пока не существует — будет создан при установке."
  fi
}

update_paths

require_compose_dir() {
  if [[ ! -d "${COMPOSE_DIR}" ]]; then
    warn "Каталог ${COMPOSE_DIR} не найден. Сначала выполните установку (пункты 1 или 3)."
    return 1
  fi
  return 0
}
# =============================================================

# ---------- helpers ----------
log()  { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[DONE]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[ERR ]\033[0m %s\n" "$*" >&2; }
run()  { log "$*"; eval "$*"; }

need_sudo() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    command -v sudo >/dev/null 2>&1 && echo sudo || { err "Нужен root или sudo."; exit 1; }
  fi
}
SUDO="$(need_sudo || true)"

sha256() { command -v sha256sum >/dev/null 2>&1 && sha256sum "$1" | awk '{print $1}' || shasum -a 256 "$1" | awk '{print $1}'; }

generate_password() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  elif command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
  else
    LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32
  fi
}

# ---------- self install to PATH ----------
self_install() {
  local target="/usr/local/bin/${BIN_NAME}"
  local source_path=""

  if [[ -n "${SCRIPT_SOURCE}" && "${SCRIPT_SOURCE}" != "bash" && -e "${SCRIPT_SOURCE}" ]]; then
    if [[ "${SCRIPT_SOURCE}" = /* ]]; then
      source_path="${SCRIPT_SOURCE}"
    else
      source_path="$(pwd)/${SCRIPT_SOURCE}"
    fi
  fi

  if [[ "${target}" == "${source_path}" ]]; then
    return 0
  fi

  log "Устанавливаю ${BIN_NAME} в ${target}"

  if [[ -n "${source_path}" && -r "${source_path}" ]]; then
    $SUDO install -m 0755 -D "${source_path}" "${target}"
  elif [[ -n "${UPDATE_URL}" ]]; then
    local tmp; tmp="$(mktemp)"
    if curl -fsSL "${UPDATE_URL}" -o "${tmp}"; then
      $SUDO install -m 0755 -D "${tmp}" "${target}"
    else
      rm -f "${tmp}"
      err "Не удалось скачать скрипт по UPDATE_URL для установки."
      exit 1
    fi
    rm -f "${tmp}"
  else
    err "Нет локального файла и UPDATE_URL — не могу установить ${BIN_NAME}."
    exit 1
  fi

  ok "Установлено. Теперь можно вызывать: ${BIN_NAME}"
}

# ---------- Ubuntu-only detection ----------
detect_ubuntu_like() {
  [[ -r /etc/os-release ]] || { err "Нет /etc/os-release"; exit 1; }
  . /etc/os-release
  local like="${ID_LIKE:-}"; local id_lc="${ID,,}"
  if [[ "$id_lc" == "ubuntu" || "$like" == *"ubuntu"* || "$id_lc" == "linuxmint" || "$id_lc" == "pop" ]]; then
    REPO_OS="ubuntu"
    CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
    ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
    [[ -n "${CODENAME}" ]] || warn "Не удалось определить кодовое имя Ubuntu — попробую fallback."
    return 0
  else
    REPO_OS="non-ubuntu"
    return 1
  fi
}

# ---------- Docker install ----------
docker_is_installed() { command -v docker >/dev/null 2>&1; }

prep_apt() {
  run "$SUDO apt-get update"
  run "$SUDO apt-get install -y ca-certificates curl gnupg lsb-release"
  run "$SUDO install -m 0755 -d /etc/apt/keyrings"
  run "$SUDO rm -f /etc/apt/sources.list.d/docker.list"
  run "$SUDO rm -f /etc/apt/keyrings/docker.gpg"
  local GPG_URL="https://download.docker.com/linux/ubuntu/gpg"
  run "curl -fsSL ${GPG_URL} | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
  run "$SUDO chmod a+r /etc/apt/keyrings/docker.gpg"
}

add_repo() {
  local repo_line
  repo_line="deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${CODENAME} stable"
  echo "${repo_line}" | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
  run "$SUDO apt-get update"
}

install_pkgs() {
  run "$SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
}

fallback_get_docker() {
  warn "Система не Ubuntu-семейства или не удалось определить релиз — использую официальный скрипт get.docker.com"
  run "curl -fsSL https://get.docker.com | $SUDO sh"
}

post_install_docker() {
  if command -v systemctl >/dev/null 2>&1; then
    run "$SUDO systemctl enable --now docker"
  fi
  if ! getent group docker >/dev/null 2>&1; then
    run "$SUDO groupadd docker"
  fi
  if id -nG "$USER" 2>/dev/null | tr ' ' '\n' | grep -qx docker; then
    log "Пользователь $USER уже в группе docker."
  else
    run "$SUDO usermod -aG docker $USER"
    warn "Добавлен $USER в группу docker. Выполните 'newgrp docker' или перелогиньтесь, чтобы использовать docker без sudo."
  fi
}

install_docker_if_needed() {
  if docker_is_installed; then
    ok "Docker уже установлен — шаг установки пропущен."
    return 0
  fi
  if detect_ubuntu_like; then
    if [[ -n "${CODENAME:-}" ]]; then
      set +e
      prep_apt && add_repo && install_pkgs
      local STATUS=$?
      set -e
      if [[ $STATUS -ne 0 ]]; then
        warn "Не удалось установить из репозитория Ubuntu. Пробую fallback."
        fallback_get_docker
      fi
    else
      fallback_get_docker
    fi
  else
    fallback_get_docker
  fi
  post_install_docker
  ok "Docker установлен."
}

# ---------- Docker helpers ----------
decide_docker_prefix() {
  if id -nG "$USER" 2>/dev/null | tr ' ' '\n' | grep -qx docker; then
    DOCKER_PREFIX=""
  else
    DOCKER_PREFIX="$SUDO"
  fi
}

# ---------- Bot steps ----------
ensure_install_dir() {
  if [[ ! -d "${INSTALL_DIR}" ]]; then
    run "$SUDO mkdir -p '${INSTALL_DIR}'"
    run "$SUDO chown -R ${USER}:${USER} '${INSTALL_DIR}'"
  fi
}

clone_or_update_repo() {
  ensure_install_dir
  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    log "Обновляю репозиторий (${INSTALL_DIR})…"
    (cd "${INSTALL_DIR}" && git pull --ff-only) || warn "Не удалось обновить (оставляю как есть)."
  else
    run "git clone '${REPO_URL}' '${INSTALL_DIR}'"
  fi
}

prompt_overrides() {
  echo
  echo "— Укажите ТОЛЬКО те параметры, которые хотите изменить."
  echo "— Пустой ввод = оставить значение из .env.example без изменений."
  read -r -p "BOT_TOKEN (оставьте пустым, чтобы не менять): " in_token || true
  read -r -p "BOT_DEV_ID (оставьте пустым, чтобы не менять): " in_dev   || true
  read -r -p "BOT_GROUP_ID (оставьте пустым, чтобы не менять): " in_group || true
  read -r -p "BOT_EMOJI_ID (оставьте пустым, чтобы не менять): " in_emoji || true
  read -r -p "BOT_ACTIVE_EMOJI_ID (оставьте пустым, чтобы не менять): " in_emoji_active || true
  read -r -p "BOT_RESOLVED_EMOJI_ID (оставьте пустым, чтобы не менять): " in_emoji_resolved || true
  read -r -p "BOT_DEFAULT_LANGUAGE (например en, ru; пусто = оставить): " in_lang || true
  read -r -p "BOT_LANGUAGE_PROMPT_ENABLED (true/false/yes/no; пусто = оставить): " in_prompt || true
  read -r -p "BOT_REMINDERS_ENABLED (true/false/yes/no; пусто = оставить): " in_reminders || true
  read -r -p "REDIS_PASSWORD (Enter — сгенерировать автоматически): " in_redis_password || true
  OV_BOT_TOKEN="${in_token:-}"
  OV_DEV_ID="${in_dev:-}"
  OV_GROUP_ID="${in_group:-}"
  OV_BOT_EMOJI_ID="${in_emoji:-}"
  OV_BOT_ACTIVE_EMOJI_ID="${in_emoji_active:-}"
  OV_BOT_RESOLVED_EMOJI_ID="${in_emoji_resolved:-}"
  OV_DEFAULT_LANGUAGE="${in_lang:-}"
  OV_LANGUAGE_PROMPT=""
  OV_REMINDERS_ENABLED=""
  OV_REDIS_PASSWORD=""
  if [[ -z "${in_redis_password:-}" ]]; then
    in_redis_password="$(generate_password)"
    log "REDIS_PASSWORD сгенерирован автоматически и будет записан в .env."
  fi
  OV_REDIS_PASSWORD="${in_redis_password}"
  if [[ -n "${in_prompt:-}" ]]; then
    case "${in_prompt,,}" in
      y|yes|1)    OV_LANGUAGE_PROMPT="true" ;;
      n|no|0)     OV_LANGUAGE_PROMPT="false" ;;
      true|false) OV_LANGUAGE_PROMPT="${in_prompt,,}" ;;
      *)
        warn "Не удалось распознать значение BOT_LANGUAGE_PROMPT_ENABLED, сохраню как введено."
        OV_LANGUAGE_PROMPT="${in_prompt}"
        ;;
    esac
  fi
  if [[ -n "${in_reminders:-}" ]]; then
    case "${in_reminders,,}" in
      y|yes|1)    OV_REMINDERS_ENABLED="true" ;;
      n|no|0)     OV_REMINDERS_ENABLED="false" ;;
      true|false) OV_REMINDERS_ENABLED="${in_reminders,,}" ;;
      *)
        warn "Не удалось распознать значение BOT_REMINDERS_ENABLED, сохраню как введено."
        OV_REMINDERS_ENABLED="${in_reminders}"
        ;;
    esac
  fi
}

# KEY=VALUE точечная замена
safe_replace() {
  local key="$1"; shift
  local val="$1"; shift
  local file="$1"
  local esc_val
  esc_val="$(printf '%s' "$val" | sed -e 's/[&/\]/\\&/g')"
  if grep -qE "^${key}=" "$file"; then
    sed -i -E "s|^${key}=.*$|${key}=${esc_val}|" "$file"
  else
    printf "\n%s=%s\n" "$key" "$val" >> "$file"
  fi
}

write_env_from_example() {
  [[ -f "${EXAMPLE_FILE}" ]] || { err "Не найден ${EXAMPLE_FILE}"; exit 1; }
  if [[ -f "${ENV_FILE}" ]]; then
    local ts; ts="$(date +%Y%m%d_%H%M%S)"
    run "cp '${ENV_FILE}' '${ENV_FILE}.bak_${ts}'"
  fi
  run "cp '${EXAMPLE_FILE}' '${ENV_FILE}'"
  [[ -n "${OV_BOT_TOKEN}" ]] && safe_replace "BOT_TOKEN"    "${OV_BOT_TOKEN}" "${ENV_FILE}"
  [[ -n "${OV_DEV_ID}"    ]] && safe_replace "BOT_DEV_ID"   "${OV_DEV_ID}"    "${ENV_FILE}"
  [[ -n "${OV_GROUP_ID}"  ]] && safe_replace "BOT_GROUP_ID" "${OV_GROUP_ID}"  "${ENV_FILE}"
  [[ -n "${OV_BOT_EMOJI_ID}" ]] && safe_replace "BOT_EMOJI_ID" "${OV_BOT_EMOJI_ID}" "${ENV_FILE}"
  [[ -n "${OV_BOT_ACTIVE_EMOJI_ID}" ]] && safe_replace "BOT_ACTIVE_EMOJI_ID" "${OV_BOT_ACTIVE_EMOJI_ID}" "${ENV_FILE}"
  [[ -n "${OV_BOT_RESOLVED_EMOJI_ID}" ]] && safe_replace "BOT_RESOLVED_EMOJI_ID" "${OV_BOT_RESOLVED_EMOJI_ID}" "${ENV_FILE}"
  [[ -n "${OV_DEFAULT_LANGUAGE}" ]] && safe_replace "BOT_DEFAULT_LANGUAGE" "${OV_DEFAULT_LANGUAGE}" "${ENV_FILE}"
  [[ -n "${OV_LANGUAGE_PROMPT}"  ]] && safe_replace "BOT_LANGUAGE_PROMPT_ENABLED" "${OV_LANGUAGE_PROMPT}" "${ENV_FILE}"
  [[ -n "${OV_REMINDERS_ENABLED}" ]] && safe_replace "BOT_REMINDERS_ENABLED" "${OV_REMINDERS_ENABLED}" "${ENV_FILE}"
  [[ -n "${OV_REDIS_PASSWORD}" ]] && safe_replace "REDIS_PASSWORD" "${OV_REDIS_PASSWORD}" "${ENV_FILE}"
  ok ".env создан из .env.example и обновлён выбранными параметрами."
}

compose_up() {
  require_compose_dir || return 1
  decide_docker_prefix
  (cd "${COMPOSE_DIR}" && ${DOCKER_PREFIX} docker compose up -d --build)
  ok "Контейнеры запущены (detached)."
}

compose_down() {
  require_compose_dir || return 1
  decide_docker_prefix
  (cd "${COMPOSE_DIR}" && ${DOCKER_PREFIX} docker compose down)
  ok "Контейнеры остановлены и удалены."
}

compose_restart() {
  require_compose_dir || return 1
  decide_docker_prefix
  (cd "${COMPOSE_DIR}" && ${DOCKER_PREFIX} docker compose restart)
  ok "Контейнеры перезапущены."
}

compose_logs() {
  require_compose_dir || return 1
  decide_docker_prefix
  (cd "${COMPOSE_DIR}" && ${DOCKER_PREFIX} docker compose logs -f)
}

compose_ps() {
  require_compose_dir || return 1
  decide_docker_prefix
  (cd "${COMPOSE_DIR}" && ${DOCKER_PREFIX} docker compose ps)
}

status_summary() {
  echo "==== STATUS ===="
  if docker_is_installed; then docker --version || true; else echo "docker: not installed"; fi
  if [[ -d "${INSTALL_DIR}" ]]; then
    echo "Repo dir : ${INSTALL_DIR}"
    (cd "${INSTALL_DIR}" && git rev-parse --short HEAD 2>/dev/null || echo "no git") || true
  else
    echo "Repo dir : not present"
  fi
  if [[ -f "${ENV_FILE}" ]]; then
    echo ".env     : present ($(wc -l < "${ENV_FILE}") lines)"
  else
    echo ".env     : not present"
  fi
  compose_ps || true
  echo "==============="
}

update_bot() {
  clone_or_update_repo
  compose_up
}

uninstall_bot() {
  compose_down || true
  warn "Удалить каталог ${INSTALL_DIR}? Это сотрёт .env и локальные изменения!"
  read -r -p "Введите 'yes' для удаления: " ans
  if [[ "${ans}" == "yes" ]]; then
    run "$SUDO rm -rf '${INSTALL_DIR}'"
    ok "Каталог удалён."
  else
    warn "Удаление каталога отменено."
  fi
}

# ---------- Self-update ----------
self_update_check() {
  if [[ -z "${UPDATE_URL}" ]]; then
    warn "UPDATE_URL не задан. Укажите ссылку на raw-скрипт внутри файла, чтобы включить проверку обновлений."
    return 1
  fi
  local tmp; tmp="$(mktemp)"
  if ! curl -fsSL "${UPDATE_URL}" -o "${tmp}"; then
    err "Не удалось скачать обновление по UPDATE_URL."
    rm -f "${tmp}"; return 2
  fi
  local current="/usr/local/bin/${BIN_NAME}"
  if [[ ! -f "${current}" ]]; then
    warn "Текущая установленная копия не найдена (${current})."
    rm -f "${tmp}"; return 3
  fi
  local h_cur h_new
  h_cur="$(sha256 "${current}")"
  h_new="$(sha256 "${tmp}")"
  if [[ "${h_cur}" == "${h_new}" ]]; then
    ok "Обновлений нет — установлена актуальная версия."
    rm -f "${tmp}"; return 0
  else
    warn "Доступна новая версия. Текущий: ${h_cur:0:7}, новый: ${h_new:0:7}"
    echo "Обновить сейчас? (yes/NO)"
    read -r ans
    if [[ "${ans}" == "yes" ]]; then
      $SUDO install -m 0755 -D "${tmp}" "${current}"
      ok "s-b обновлён."
    else
      warn "Обновление отменено."
    fi
    rm -f "${tmp}"
  fi
}

self_update_now() {
  if [[ -z "${UPDATE_URL}" ]]; then
    warn "UPDATE_URL не задан — не могу обновиться."
    return 1
  fi
  local tmp; tmp="$(mktemp)"
  curl -fsSL "${UPDATE_URL}" -o "${tmp}"
  $SUDO install -m 0755 -D "${tmp}" "/usr/local/bin/${BIN_NAME}"
  rm -f "${tmp}"
  ok "s-b обновлён до последней версии."
}

# ---------- Menu ----------
print_menu() {
  cat <<MENU
================= Меню установки/управления =================
Текущий каталог установки: ${INSTALL_DIR}
1) Быстрая установка (Docker + бот)
2) Установить Docker (Ubuntu) / fallback (get.docker.com)
3) Установить/обновить бота (клонировать/обновить репозиторий)
4) Создать .env из .env.example и изменить выбранные параметры
5) Запустить (docker compose up -d --build)
6) Перезапустить контейнеры
7) Остановить и удалить контейнеры (compose down)
8) Показать логи
9) Обновить бота (git pull + up -d)
10) Статус
11) Проверить обновления s-b (без установки)
12) Самообновление s-b (скачать и установить новую версию)
13) Удалить бота (compose down, опционально удалить каталог)
0) Выход
==============================================================
MENU
}

quick_install() {
  install_docker_if_needed
  clone_or_update_repo
  prompt_overrides
  write_env_from_example
  compose_up
}

install_bot_only() {
  clone_or_update_repo
  prompt_overrides
  write_env_from_example
}

menu_loop() {
  while true; do
    print_menu
    read -r -p "Выберите пункт: " choice
    case "$choice" in
      1) quick_install ;;
      2) install_docker_if_needed ;;
      3) install_bot_only ;;
      4) [[ -d "${INSTALL_DIR}" ]] || { warn "Сначала пункт 3 (установка/обновление бота)."; continue; }
         prompt_overrides; write_env_from_example ;;
      5) install_docker_if_needed; [[ -d "${INSTALL_DIR}" ]] || { warn "Сначала пункт 3."; continue; }; compose_up ;;
      6) compose_restart ;;
      7) compose_down ;;
      8) compose_logs ;;
      9) update_bot ;;
      10) status_summary ;;
      11) self_update_check ;;
      12) self_update_now ;;
      13) uninstall_bot ;;
      0) exit 0 ;;
      *) warn "Неизвестный пункт." ;;
    esac
  done
}

# ---------- Entry ----------
main() {
  prompt_install_dir
  self_install
  menu_loop
}
main "$@"
