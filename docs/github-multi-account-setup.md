# GitHub 멀티 계정 설정 가이드

> GitHub CLI(`gh`)를 활용하여 **개인 계정**(Git 작업용)과 **조직 계정**(Copilot용)을 동시에 사용하는 설정 방법.

---

## 개요

| 용도 | 계정 | 활성 상태 |
|------|------|-----------|
| Git push/pull, GitHub CLI | `junwoojeong100` | Active |
| GitHub Copilot | `junwoojeong_microsoft` | Inactive |

두 계정 모두 `gh auth login`으로 등록하되, **active 계정**만 Git 작업에 사용되고 Copilot은 별도의 inactive 계정 토큰을 사용한다.

---

## 1단계: GitHub CLI에 두 계정 등록

```bash
# 첫 번째 계정 (개인 — Git 작업용)
gh auth login --hostname github.com

# 두 번째 계정 (조직 — Copilot용)
gh auth login --hostname github.com
```

로그인 후 확인:

```bash
gh auth status
```

출력 예시:

```
github.com
  ✓ Logged in to github.com account junwoojeong100 (keyring)
  - Active account: true

  ✓ Logged in to github.com account junwoojeong_microsoft (keyring)
  - Active account: false
```

---

## 2단계: 활성 계정 설정

Git 작업에 사용할 계정을 active로 설정한다:

```bash
gh auth switch --user junwoojeong100
```

결과로 `~/.config/gh/hosts.yml`이 다음과 같이 설정된다:

```yaml
github.com:
    git_protocol: https
    users:
        junwoojeong100:
        junwoojeong_microsoft:
    user: junwoojeong100    # ← active 계정
```

---

## 3단계: Git Credential Helper 설정

Git이 push/pull 시 `gh`의 토큰을 자동으로 사용하도록 credential helper를 설정한다.

### 3-1. Helper 스크립트 생성

```bash
mkdir -p ~/.config/git
cat > ~/.config/git/credential-helper-junwoojeong100.sh << 'EOF'
#!/bin/bash
TOKEN=$(gh auth token --user junwoojeong100 2>/dev/null)
if [ -n "$TOKEN" ]; then
    echo "protocol=https"
    echo "host=github.com"
    echo "username=junwoojeong100"
    echo "password=$TOKEN"
fi
EOF
chmod +x ~/.config/git/credential-helper-junwoojeong100.sh
```

### 3-2. 글로벌 Git 설정에 등록

```bash
# 기존 credential helper 초기화 후 커스텀 helper 등록
git config --global credential.helper ""
git config --global --add credential.helper '!~/.config/git/credential-helper-junwoojeong100.sh'
```

결과로 `~/.gitconfig`에 다음이 추가된다:

```ini
[credential]
    helper = ""
    helper = !~/.config/git/credential-helper-junwoojeong100.sh
```

> **참고:** `helper = ""`를 먼저 설정하여 macOS Keychain 등 기본 credential helper를 비활성화한다.

---

## 4단계: Git 사용자 정보 설정

```bash
git config --global user.name "junwoojeong100"
git config --global user.email "junwoojeong100@gmail.com"
```

---

## 설정 파일 요약

| 파일 | 역할 |
|------|------|
| `~/.config/gh/hosts.yml` | gh CLI 멀티 계정 관리 (active/inactive) |
| `~/.config/gh/config.yml` | gh CLI 전역 설정 (protocol, editor 등) |
| `~/.config/git/credential-helper-junwoojeong100.sh` | Git에 junwoojeong100 토큰 제공 |
| `~/.gitconfig` | 글로벌 Git 설정 (user, credential helper) |

---

## 자주 쓰는 명령어

```bash
# 현재 인증 상태 확인
gh auth status

# 활성 계정 전환
gh auth switch --user junwoojeong_microsoft

# 특정 계정의 토큰 확인
gh auth token --user junwoojeong100

# credential helper 동작 테스트
echo "protocol=https\nhost=github.com" | git credential fill
```

---

## 주의 사항

1. **Copilot 인증은 자동**: `junwoojeong_microsoft`가 inactive여도 Copilot은 해당 계정의 토큰을 독립적으로 사용한다.
2. **토큰 갱신**: `gh auth refresh --user <account>`로 만료된 토큰을 갱신할 수 있다.
3. **리포별 계정 분리가 필요한 경우**: 특정 리포에서 다른 계정을 쓰려면 로컬 `.git/config`에 별도 credential helper를 설정한다.
4. **SSH를 사용하는 경우**: 이 가이드는 HTTPS 기반이다. SSH를 쓸 때는 `~/.ssh/config`에 Host alias를 설정하는 방식을 사용한다.
