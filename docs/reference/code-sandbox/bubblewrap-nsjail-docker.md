# Bubblewrap, nsjail, Docker — Self-Host Lightweights

Sources:
- https://github.com/containers/bubblewrap
- https://code.claude.com/docs/en/sandboxing
- https://www.morphllm.com/nsjail-sandbox
- https://github.com/google/nsjail
- https://docs.docker.com/ai/sandboxes/
Retrieved: 2026-05-18

## Bubblewrap (bwrap)
- Unprivileged sandbox via Linux user namespaces; no setuid required.
- Used by Flatpak and Claude Code itself (Linux/WSL2 backend).
- Claude Code recipe: `bwrap --unshare-net` + socat + HTTP(S)_PROXY to host proxy.
- License: LGPL-2.0 (per Arch Wiki / repo COPYING).
- Ubuntu 24.04+: AppArmor blocks unprivileged user namespaces by default — needs custom AppArmor profile.
- Flags worth knowing: `--ro-bind`, `--bind`, `--unshare-pid`, `--unshare-net`, `--unshare-user`, `--new-session`, `--die-with-parent`.
- Caveat: protection level == quality of args; "running untrusted code is never safe; sandboxing cannot change this" (Arch Wiki).

## nsjail
- Google-built process isolator (namespaces + seccomp-bpf + cgroups + rlimits). MIT license, stable since 2015.
- Used by Google for CTF infra, by Windmill for Python/Go workflow sandboxing (incl. AI agents).
- ~sub-20 ms startup, zero-daemon — efficient for agent loops with many short executions.
- More opinionated than bwrap (config file driven).

## Docker / Podman containers
- Shared kernel; not safe for untrusted-code class threats by themselves.
- Docker Sandboxes (Mar 2026): adds a microVM layer per sandbox (own kernel, FS, network). Supports Claude Code, Gemini CLI, Codex, Copilot, Kiro, OpenCode, Docker Agent.
- Podman rootless + libkrun: similar microVM-on-Podman path.
- For our threat model (a coding agent we wrote, run on a shared machine, operating on `demo_repo/`): hardened rootless Docker or bwrap is reasonable; for an open public demo, would want microVM/gVisor.

## Local-fit summary (lambdavector2, single user, demo_repo isolation)
- Cheapest: bubblewrap with read-only host bind, RW bind only `demo_repo/`, `--unshare-net`.
- Slightly more featured: nsjail with config file checked into repo.
- "Future-proofing" tier: Docker container with `--read-only`, `--cap-drop=ALL`, `--network=none`, `--pids-limit`, tmpfs for /tmp, mount `demo_repo/` only.
