#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/gotchi}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"
REMOVE_GLOBAL_CONFIG="0"
REMOVE_LOGIN_SNIPPET="0"
LOGIN_SNIPPET_USER=""
REMOVE_APP_DIR="1"

usage() {
  cat <<'EOF'
uninstall-system.sh

Remove a instalação nativa do gotchi sem apagar pets dos usuários por padrão.

Uso:
  sudo ./scripts/uninstall-system.sh [opcoes]

Opções:
  --install-dir PATH         Diretório da aplicação. Default: /opt/gotchi
  --bin-dir PATH             Diretório dos launchers. Default: /usr/local/bin
  --keep-app-dir             Mantém /opt/gotchi no disco
  --remove-global-config     Remove /etc/xdg/gotchi/gotchi.json e diretório relacionado
  --remove-login-snippet     Remove o snippet opcional do ~/.bashrc do usuário informado
  --login-user USER          Usuário alvo para remover o snippet de login
  -h, --help                 Mostra esta ajuda
EOF
}

remove_launchers() {
  rm -f "${BIN_DIR}/gotchi"
  rm -f "${BIN_DIR}/flash"
}

remove_app_dir() {
  if [[ "${REMOVE_APP_DIR}" != "1" ]]; then
    return
  fi
  rm -rf "${INSTALL_DIR}"
}

remove_global_config() {
  if [[ "${REMOVE_GLOBAL_CONFIG}" != "1" ]]; then
    return
  fi

  rm -f /etc/xdg/gotchi/gotchi.json
  rmdir /etc/xdg/gotchi 2>/dev/null || true
}

remove_login_snippet() {
  if [[ "${REMOVE_LOGIN_SNIPPET}" != "1" ]]; then
    return
  fi

  if [[ -z "${LOGIN_SNIPPET_USER}" ]]; then
    echo "Erro: use --login-user USER junto com --remove-login-snippet" >&2
    exit 1
  fi

  local user_home
  user_home="$(getent passwd "${LOGIN_SNIPPET_USER}" | cut -d: -f6)"
  if [[ -z "${user_home}" ]]; then
    echo "Erro: usuário não encontrado: ${LOGIN_SNIPPET_USER}" >&2
    exit 1
  fi

  local bashrc="${user_home}/.bashrc"
  if [[ ! -f "${bashrc}" ]]; then
    return
  fi

  python3 - <<PY
from pathlib import Path
path = Path(${bashrc@Q})
text = path.read_text(encoding="utf-8")
begin = "# >>> gotchi line >>>"
end = "# <<< gotchi line <<<"
start = text.find(begin)
finish = text.find(end)
if start != -1 and finish != -1 and finish > start:
    finish = text.find("\n", finish)
    if finish == -1:
        finish = len(text)
    else:
        finish += 1
    text = text[:start].rstrip() + "\n" + text[finish:].lstrip("\n")
    path.write_text(text, encoding="utf-8")
PY
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-dir)
        INSTALL_DIR="$2"
        shift 2
        ;;
      --bin-dir)
        BIN_DIR="$2"
        shift 2
        ;;
      --keep-app-dir)
        REMOVE_APP_DIR="0"
        shift
        ;;
      --remove-global-config)
        REMOVE_GLOBAL_CONFIG="1"
        shift
        ;;
      --remove-login-snippet)
        REMOVE_LOGIN_SNIPPET="1"
        shift
        ;;
      --login-user)
        LOGIN_SNIPPET_USER="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Opção desconhecida: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
}

main() {
  parse_args "$@"
  remove_launchers
  remove_app_dir
  remove_global_config
  remove_login_snippet

  cat <<EOF
Desinstalação concluída.

Removido:
  launcher: ${BIN_DIR}/gotchi
  flash: ${BIN_DIR}/flash
  app dir: ${INSTALL_DIR} $( [[ "${REMOVE_APP_DIR}" == "1" ]] && echo '(removido)' || echo '(mantido)' )

Observação:
  Os diretórios privados e bancos dos usuários não foram removidos automaticamente.
EOF
}

main "$@"
