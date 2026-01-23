#!/bin/bash
# Stock Tracker systemd 서비스 설치 스크립트

echo "Stock Tracker 서비스 설치"
echo "=========================="

# 경로 설정 (필요시 수정)
PROJECT_DIR="/home/ubuntu/stock-tracker"
USER="ubuntu"

# 서비스 파일 복사
sudo cp stock-tracker-scheduler.service /etc/systemd/system/
sudo cp stock-tracker-monitor.service /etc/systemd/system/

# 경로/사용자 업데이트 (현재 환경에 맞게)
sudo sed -i "s|/home/ubuntu/stock-tracker|$PROJECT_DIR|g" /etc/systemd/system/stock-tracker-*.service
sudo sed -i "s|User=ubuntu|User=$USER|g" /etc/systemd/system/stock-tracker-*.service

# systemd 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable stock-tracker-scheduler
sudo systemctl enable stock-tracker-monitor

# 서비스 시작
sudo systemctl start stock-tracker-scheduler
sudo systemctl start stock-tracker-monitor

echo ""
echo "설치 완료!"
echo ""
echo "서비스 상태 확인:"
echo "  sudo systemctl status stock-tracker-scheduler"
echo "  sudo systemctl status stock-tracker-monitor"
echo ""
echo "로그 확인:"
echo "  sudo journalctl -u stock-tracker-scheduler -f"
echo "  sudo journalctl -u stock-tracker-monitor -f"
