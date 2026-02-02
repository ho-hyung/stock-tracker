#!/bin/bash

echo "=== Stock Tracker 업데이트 ==="

# 1. 기존 스케줄러 중지
echo "[1/5] 스케줄러 중지..."
pkill -f 'python.*main.py.*scheduler' 2>/dev/null || true

# 2. 코드 업데이트
echo "[2/5] 코드 업데이트..."
git pull origin main

# 3. 가상환경 활성화 및 의존성 확인
echo "[3/5] 의존성 확인..."
source venv/bin/activate
pip install -r requirements.txt -q

# 4. 스케줄러 재시작
echo "[4/5] 스케줄러 재시작..."
nohup python -u src/main.py --mode scheduler > scheduler.log 2>&1 &

# 5. 가격 모니터 서비스 재시작
echo "[5/5] 가격 모니터 재시작..."
sudo systemctl restart stock-tracker-monitor

sleep 2

# 확인
echo ""
echo "=== 상태 확인 ==="

if pgrep -f 'python.*main.py.*scheduler' > /dev/null; then
    echo "✅ 스케줄러: 실행 중"
else
    echo "❌ 스케줄러: 시작 실패"
fi

if systemctl is-active --quiet stock-tracker-monitor; then
    echo "✅ 가격 모니터: 실행 중"
else
    echo "❌ 가격 모니터: 시작 실패"
fi

echo ""
echo "로그 확인:"
echo "  스케줄러: tail -f scheduler.log"
echo "  모니터:   sudo journalctl -u stock-tracker-monitor -f"
