# Foundry Hosted Agent 컨테이너 이미지
# 주의: 호스팅 플랫폼은 x86_64(linux/amd64) 이미지를 요구합니다.
# Apple Silicon 등 ARM 머신에서 빌드하면 다음처럼 플랫폼을 지정하세요:
#   docker build --platform linux/amd64 .
FROM python:3.14.5-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY . user_agent/
WORKDIR /app/user_agent

RUN python -m pip install --no-cache-dir -r requirements.txt

# Responses 프로토콜 서버 포트
EXPOSE 8088

CMD ["python", "main.py"]
