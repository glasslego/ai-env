---
name: k8s-ops
description: Kubernetes context / pod / metrics 조회 + 안전한 cp (read-mostly). 사용자가 "/k8s", "kubernetes", "쿠버네티스", "pod 상태", "k8s context", "노드 상태", "logs 가져와" 를 말하면 트리거. 실제 호출은 cde-skills `platform/kubernetes` 서브스킬에 위임. delete 명령은 본 wrapper 가 차단 (cde-skills 직접 호출 + --confirm 사용).
---

# K8s Ops

> Origin: cde-skills/platform/kubernetes. **재구현 금지** — read-mostly wrapper.

## When to invoke

- "pod 상태", "이 pod 왜 CrashLoop", "node disk pressure?"
- `/k8s pods`, `/k8s logs <pod>`, `/k8s context`

## 자주 쓰는 명령

```bash
~/.claude/skills/k8s-ops/scripts/k8s.sh contexts                     # context 목록
~/.claude/skills/k8s-ops/scripts/k8s.sh pods -n my-ns                 # 네임스페이스의 pod
~/.claude/skills/k8s-ops/scripts/k8s.sh logs -n my-ns my-pod          # 로그 (마지막 1000줄)
~/.claude/skills/k8s-ops/scripts/k8s.sh observe -n my-ns my-pod       # describe + events
~/.claude/skills/k8s-ops/scripts/k8s.sh metrics -n my-ns              # CPU/MEM
~/.claude/skills/k8s-ops/scripts/k8s.sh cp -n my-ns my-pod /a/b ./c   # 파일 복사 (read 측)
```

## 위임 경로

cde-skills 의 `k8s_{context,pod,observe,metrics,copy}.py` 모듈로 라우팅.

## 안전

- 본 wrapper 는 `delete` / `apply` / `exec` 명령을 차단.
- `cp` 는 read 방향만 허용 (pod→로컬). 로컬→pod 복사는 차단.
- 파괴적 정리 스크립트 (`k8s_disk_pressure_force_cleanup.sh`) 는 wrapper 통과 안 됨.
