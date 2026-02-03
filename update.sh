#!/bin/bash

echo "=== Stock Tracker 업데이트 ==="

# 1. 기존 스케줄러 중지 (중복 방지)
echo "[1/5] 스케줄러 중지..."
pkill -f 'python.*main.py.*scheduler' 2>/dev/null || true
sleep 1
# 완전히 종료될 때까지 대기
while pgrep -f 'python.*main.py.*scheduler' > /dev/null; do
    echo "  스케줄러 종료 대기 중..."
    sleep 1
done
echo "  스케줄러 종료 완료"

# 2. 코드 업데이트
echo "[2/5] 코드 업데이트..."
git pull origin main

# 3. 가상환경 활성화 및 의존성 확인
echo "[3/5] 의존성 확인..."
source venv/bin/activate
pip install -r requirements.txt -q

# 4. 스케줄러 재시작 (중복 확인 후 시작)
echo "[4/5] 스케줄러 재시작..."
if pgrep -f 'python.*main.py.*scheduler' > /dev/null; then
    echo "  ⚠️ 스케줄러가 이미 실행 중입니다. 스킵."
else
    nohup python -u src/main.py --mode scheduler > scheduler.log 2>&1 &
    echo "  스케줄러 시작됨 (PID: $!)"
fi

# 5. 가격 모니터 서비스 재시작
echo "[5/5] 가격 모니터 재시작..."
sudo systemctl restart stock-tracker-monitor

sleep 2

# 확인
echo ""
echo "=== 상태 확인 ==="

SCHEDULER_COUNT=$(pgrep -f 'python.*main.py.*scheduler' | wc -l)
if [ "$SCHEDULER_COUNT" -eq 1 ]; then
    echo "✅ 스케줄러: 실행 중 (1개)"
elif [ "$SCHEDULER_COUNT" -gt 1 ]; then
    echo "⚠️ 스케줄러: ${SCHEDULER_COUNT}개 실행 중 (중복!)"
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
