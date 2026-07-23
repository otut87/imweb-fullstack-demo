#!/usr/bin/env bash
# Lightsail/EC2 Ubuntu 24.04 최초 1회 실행 스크립트
set -euo pipefail

sudo apt-get update
sudo apt-get install -y ca-certificates curl git

# Docker 공식 설치 (compose 플러그인 포함)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo
echo "완료. 도커 그룹 적용을 위해 SSH 재접속 후:"
echo "  git clone <저장소URL> enchante-erp && cd enchante-erp"
echo "  cp .env.example .env && nano .env   # IMWEB_* 값 + DOMAIN 설정"
echo "  docker compose -f docker-compose.prod.yml up -d --build"
