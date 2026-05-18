# Firecracker / gVisor / Cloud Hypervisor — Cached Reference

Sources:
- https://github.com/firecracker-microvm/firecracker
- https://gvisor.dev/docs/user_guide/gpu/
- https://github.com/firecracker-microvm/firecracker/discussions/4845
Retrieved: 2026-05-18

## Firecracker
- AWS-built microVM (Rust). Powers Lambda, Fargate, E2B, Vercel Sandbox, Replit.
- Boot ~125 ms; <5 MiB overhead/VM; ~150 VMs/sec/host.
- Snapshot restore typical for prod (~150 ms cold start).
- Each VM has its own Linux kernel — strongest isolation in this class.
- No PCIe / GPU passthrough; work paused 2025. Use Cloud Hypervisor if you need GPU VFIO.
- Open source, Apache-2.0.

## gVisor (runsc)
- Google user-space kernel intercepting syscalls. Open source.
- GKE Agent Sandbox uses gVisor at 300 sandboxes/sec; Google says "same tech that secures Gemini".
- Modal Sandboxes built on gVisor.
- GPU: `nvproxy` supports CUDA paths (PyTorch, TF inference). Non-CUDA GPU workloads (video transcode, etc.) not supported.
- Overhead: negligible for GPU/CPU-bound; 20–50% for I/O-heavy syscall paths.

## Cloud Hypervisor
- rust-vmm sibling of Firecracker; adds VFIO passthrough for GPUs and broader device support.
- Heavier surface than Firecracker. Backed by Intel/IBM/MS.

## Takeaway
- For an internal coding agent on a shared lab box: Firecracker direct setup is non-trivial (kernel images, snapshots, networking, orchestration). gVisor runsc plugs into Docker/containerd more easily.
- For GPU-passthrough sandboxing: Cloud Hypervisor or Kata Containers (Cloud Hypervisor backend).
