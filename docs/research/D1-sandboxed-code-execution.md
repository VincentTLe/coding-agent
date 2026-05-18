# D1 — Sandboxed Code Execution for AI Agents (2026)

## TL;DR

For our coding agent's `run_bash` tool on shared host lambdavector2 operating on `demo_repo/`, use **bubblewrap (bwrap)** — unprivileged, zero-overhead, on every modern Linux, and what Claude Code itself uses on Linux/WSL2. Keep hardened **Docker** as a fallback for guest/demo use. Skip hosted clouds (E2B, Daytona, Modal) until we need untrusted-third-party-code scale; then **E2B** is the pick.

## Why this matters

The agent shells out commands an LLM emits. Accidents are easy: `rm -rf ~`, dependency installs polluting the host, `curl | sh`, fork bombs, outbound exfiltration. On a multi-user GPU box we explicitly cannot risk other users' jobs. We need (a) writes scoped to `demo_repo/`, (b) CPU/mem/PID caps, (c) network off by default, (d) zero cost, (e) trivial enough that we keep it on.

## SOTA 2026

Three isolation tiers are recognized [Northflank, Docker, Augment]:

1. **MicroVMs (Firecracker, Cloud Hypervisor, Kata)** — own kernel per sandbox; ~125-150 ms cold start via snapshots. Powers E2B, Vercel Sandbox (GA Jan 30 2026), Docker Sandboxes (GA Mar 2026), AWS Lambda, Replit.
2. **gVisor (runsc, user-space kernel)** — syscall interception; powers GKE Agent Sandbox (300/sec, Next '26) and Modal. CUDA-only GPU via `nvproxy`. 20-50% I/O overhead.
3. **Hardened containers + namespace tools (Docker, Podman rootless, nsjail, bubblewrap)** — share host kernel; fine for semi-trusted "your-own-agent on your-own-server".

The 2026 shift: microVMs are now table stakes for *productized* sandboxes; plain Docker is widely called insufficient for untrusted AI-generated code [SoftwareSeni, Arcade.dev, Docker's own blog].

## Most-used in production

E2B (Manus, Perplexity [UNVERIFIED per-customer]), Modal sandboxes (ML-heavy agents needing in-sandbox GPU), Daytona (high-RPS code interpreters, sub-90 ms), bubblewrap (Claude Code, Flatpak), nsjail (Google CTF, Windmill), Firecracker (Lambda; reused inside E2B/Vercel/Docker Sandboxes), gVisor (Google/Gemini-claimed; Modal; GKE).

## Comparison table

| Option | Isolation | Cold start | Network policy | FS isolation | GPU | Self-host | Pricing | License |
|---|---|---|---|---|---|---|---|---|
| **E2B** | Firecracker microVM | 78 ms p50 | CIDR/IP/domain allow + CIDR/IP deny, hot-update | Per-VM rootfs; FUSE S3/GCS/R2 | No (Firecracker has no PCIe passthrough) | Yes (Terraform+Packer+Nomad, GCP/AWS) | Per-second; $100 free | Apache-2.0 |
| **Daytona** | Docker container default [UNVERIFIED claim of "dedicated kernel"] | 27-90 ms | Per-sandbox | Container FS | Limited | Yes (AGPL, single-server Caddy) | $0.0504/vCPU-hr + $0.0162/GiB-hr; $200 free | AGPL-3.0 |
| **Modal** | gVisor | <1s; scales 50k+ | Block-all or CIDR allow; tunnels | Per-sandbox rootfs | **Yes A100/H100 in-sandbox** (unique in 2026) | No | ~$0.142/physical-core-hr + $0.024/GiB-hr (3x premium); $30/mo free | Closed |
| **Firecracker DIY** | microVM | ~125 ms boot, ~150 ms snapshot | BYO | Own | No PCIe (paused 2025) | Yes; you build orchestrator | Free | Apache-2.0 |
| **Cloud Hypervisor** | microVM | ~150 ms | BYO | Own | **Yes (VFIO)** | Yes | Free | Apache-2.0 |
| **gVisor DIY** | user-space kernel | container-class | container netns | container | CUDA only (`nvproxy`) | Yes (Docker/containerd plugin) | Free | Apache-2.0 |
| **Docker hardened** | shared kernel | hundreds ms | netns / `--network=none` | bind mounts | Native (NVIDIA toolkit) | Yes | Free | Apache-2.0 |
| **Podman rootless** | shared kernel (rootless) | hundreds ms | netns | bind mounts | Native | Yes | Free | Apache-2.0 |
| **nsjail** | namespaces+seccomp+cgroups | sub-20 ms | netns | bind mounts | If exposed | Yes (single binary) | Free | Apache-2.0 |
| **bubblewrap** | namespaces, unprivileged | ~10 ms | `--unshare-net` | `--ro-bind`/`--bind` | If bound | Yes (single binary) | Free | LGPL-2.1 |

Latency numbers vendor- or third-party-reported; treat as best-case [UNVERIFIED in our environment].

## Recommendation

**bubblewrap.** Right-sized for "single-user from-scratch agent on a Linux host". Same tool Claude Code uses on Linux. No daemon, no root, no money. Promote to Docker fallback for guest demos. Skip E2B/Daytona/Modal until threat model changes (untrusted third-party code, public endpoint, in-sandbox GPU). When that day comes, E2B wins for combining Firecracker isolation, OSS self-host, and per-second pricing.

## Next steps (concrete setup)

1. Add `bubblewrap` and `socat` to dev-setup notes. Ubuntu 24.04 caveat: default AppArmor blocks unprivileged user namespaces; need an AppArmor profile for `bwrap`.
2. Wrap `run_bash` to actually exec:
   ```
   bwrap --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib \
     --ro-bind /lib64 /lib64 --ro-bind /etc /etc \
     --bind <project>/demo_repo /workspace --chdir /workspace \
     --tmpfs /tmp --proc /proc --dev /dev \
     --unshare-pid --unshare-net --unshare-uts --unshare-ipc --unshare-user \
     --new-session --die-with-parent \
     --setenv HOME /workspace --setenv PATH /usr/bin:/bin \
     -- bash -lc "$cmd"
   ```
3. Wrap that in `systemd-run --user --scope -p MemoryMax=2G -p CPUQuota=200% -p TasksMax=256` for cgroup-v2 caps.
4. Optional "network on" mode: drop `--unshare-net`, set `HTTP(S)_PROXY` to a per-session whitelisting proxy (tinyproxy/mitmproxy). Off by default.
5. Add `timeout 30` + bash `ulimit -t 60` so no command hangs forever.
6. Three smoke tests per PR: `rm -rf /` does not touch host; `curl 1.1.1.1` fails offline and passes via proxy; `dd if=/dev/zero of=/tmp/x bs=1M count=10000` is killed by caps.
7. Ship `--unsafe-host-exec` escape hatch with loud logging for the rare deliberate cases.

## Open questions

- Does lambdavector2's AppArmor profile already allow `bwrap`? If admin permission is required, switch to rootless Docker.
- For sandboxing GPU-using code later: likely `runsc` + `nvproxy`, since Firecracker still has no PCIe passthrough.
- Where does the agent's persistent state (history, scratchpads) live — second `--bind`, or inside the workspace?

## Sources

- [E2B pricing](https://e2b.dev/pricing), [E2B GitHub](https://github.com/e2b-dev/E2B), [E2B infra/self-host](https://github.com/e2b-dev/infra), [E2B sandbox-network API](https://e2b.dev/docs/api-reference/sandboxes/put-sandboxes-network)
- [Daytona pricing](https://www.daytona.io/pricing), [Daytona OSS deployment](https://www.daytona.io/docs/en/oss-deployment/), [Daytona GitHub](https://github.com/daytonaio/daytona)
- [Modal sandboxes](https://modal.com/products/sandboxes), [Modal pricing](https://modal.com/pricing)
- [Superagent — Modal vs E2B vs Daytona benchmark 2026](https://www.superagent.sh/blog/ai-code-sandbox-benchmark-2026)
- [Northflank — Sandboxing AI agents 2026](https://northflank.com/blog/how-to-sandbox-ai-agents), [Northflank — AI Sandbox pricing comparison](https://northflank.com/blog/ai-sandbox-pricing), [Northflank — Best sandbox 2026](https://northflank.com/blog/best-code-execution-sandbox-for-ai-agents)
- [Firecracker GitHub](https://github.com/firecracker-microvm/firecracker), [Firecracker GPU/PCIe discussion #4845](https://github.com/firecracker-microvm/firecracker/discussions/4845)
- [gVisor GPU docs](https://gvisor.dev/docs/user_guide/gpu/), [gVisor performance guide](https://gvisor.dev/docs/architecture_guide/performance/)
- [GKE Agent Sandbox @ Next '26 — InfoQ](https://www.infoq.com/news/2026/05/gke-agent-sandbox-hypercluster/)
- [Bubblewrap GitHub](https://github.com/containers/bubblewrap), [ArchWiki Bubblewrap](https://wiki.archlinux.org/title/Bubblewrap), [Claude Code Sandboxing](https://code.claude.com/docs/en/sandboxing)
- [nsjail — Morph guide](https://www.morphllm.com/nsjail-sandbox), [awesome-sandbox](https://github.com/restyler/awesome-sandbox)
- [Docker — Comparing sandboxing approaches](https://www.docker.com/blog/comparing-sandboxing-approaches-ai-agents/), [Docker Sandboxes docs](https://docs.docker.com/ai/sandboxes/), [Arcade.dev — Docker sandboxes aren't enough](https://www.arcade.dev/blog/docker-sandboxes-arent-enough-for-agent-safety/)
- [Augment Code — What is an agent execution sandbox?](https://www.augmentcode.com/guides/agent-execution-sandbox)
- [Vercel Sandbox / Firecracker explainer](https://www.marketingscoop.com/ai/vercel-sandbox-explained-how-firecracker-microvms-run-untrusted-ai-generated-code/)
