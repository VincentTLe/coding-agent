# E2B (e2b.dev) — Cached Reference

Source: https://e2b.dev/pricing, https://github.com/e2b-dev/E2B, https://github.com/e2b-dev/infra
Retrieved: 2026-05-18

## Model
- Open-source runtime for AI-generated code, built on Firecracker microVMs.
- Hosted product (e2b.dev) + self-hostable infra (`e2b-dev/infra`).

## Isolation
- Firecracker microVM per sandbox: dedicated Linux kernel, no shared kernel paths between sandboxes.
- Median sandbox creation p50 ~78 ms (Jan 2026).
- Egress rules: allowlist (CIDR/IP/domain incl. wildcard) and denylist (CIDR/IP only). Updatable on a running sandbox via API.

## Filesystem
- Persistent volumes; FUSE-mount S3, GCS, R2 buckets directly into sandbox.

## GPU
- Firecracker itself does not support PCIe/GPU passthrough as of 2026.
- E2B OSS on bare metal recommended path if GPU is needed; cloud GPU access flagged as a constraint.

## Pricing (cloud)
- Per-second billing while sandbox is running; billing stops on pause/kill/timeout.
- $100 free credits for new users.
- "VP eng / CTO" enterprise tier with annual contracts.

## Self-host
- Terraform v1.5.x + Packer + Nomad. GCP primary target, AWS in beta. Cloudflare for DNS.

## Notes
- Production users cited: Manus, Perplexity, others.
