#!/bin/bash

echo "=== Stock Tracker 업데이트 ==="

# 1. 기존 스케줄러 중지
echo "[1/4] 스케줄러 중지..."
pkill -f 'python.*main.py.*scheduler' 2>/dev/null || true

# 2. 코드 업데이트
echo "[2/4] 코드 업데이트..."
git pull origin main

# 3. 가상환경 활성화 및 의존성 확인
echo "[3/4] 의존성 확인..."
source venv/bin/activate
pip install -r requirements.txt -q

# 4. 스케줄러 재시작
echo "[4/4] 스케줄러 재시작..."
nohup python -u src/main.py --mode scheduler > scheduler.log 2>&1 &

sleep 2

# 확인
if pgrep -f 'python.*main.py.*scheduler' > /dev/null; then
    echo ""
    echo "✅ 업데이트 완료! 스케줄러 실행 중"
    echo "   로그 확인: tail -f scheduler.log"
else
    echo ""
    echo "❌ 스케줄러 시작 실패. 로그를 확인하세요."
fi
