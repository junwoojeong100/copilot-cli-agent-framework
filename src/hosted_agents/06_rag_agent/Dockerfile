# Foundry Hosted Agent 컨테이너 이미지
# 주의: 호스팅 플랫폼은 x86_64(linux/amd64) 이미지를 요구합니다.
# Apple Silicon 등 ARM 머신에서 빌드하면 다음처럼 플랫폼을 지정하세요:
#   docker build --platform linux/amd64 .
FROM python:3.13-slim

WORKDIR /app

COPY . user_agent/
WORKDIR /app/user_agent

RUN if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        echo "No requirements.txt found"; \
    fi

# Responses 프로토콜 서버 포트
EXPOSE 8088

CMD ["python", "main.py"]
