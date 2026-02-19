import os
import modal

app = modal.App.lookup("vscode-tunnel", create_if_missing=True)

# Persistent volumes:
VSCODE_VOL = modal.Volume.from_name("vscode-volume", create_if_missing=True)
VSCODE_VOL = modal.Volume.from_name("work", create_if_missing=True)


# Optional HF secret (safe)
HF_SECRET_NAME = "hf-token"
HF_SECRET = None
try:
    HF_SECRET = modal.Secret.from_name(HF_SECRET_NAME)
except Exception:
    HF_SECRET = None

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        # base dev tools
        "wget", "ca-certificates", "tar", "git", "openssh-client",
        "curl", "nano", "htop", "unzip", "zip",
        # audio/video (useful for whisper + datasets)
        "ffmpeg",
        # misc
        "procps", "jq",
    )
    # Install uv properly (no guessing)
    .run_commands(
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "ln -sf /root/.local/bin/uv /usr/local/bin/uv",
        "uv --version",
    )
    # Install VS Code CLI (tunnel binary)
    .run_commands(
        "curl -fL -o /tmp/vscode_cli.tar.gz 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64'",       
        "mkdir -p /opt/vscode && tar -xzf /tmp/vscode_cli.tar.gz -C /opt/vscode",
        "ln -sf /opt/vscode/code /usr/local/bin/code",
        "code --version",
    )
    # Minimal Python libs you will want for dataset pushing & ML workflows
    .pip_install(
        "datasets>=2.19.0",
        "pyarrow>=15.0.0",
        "huggingface_hub>=0.22.0",
        "fsspec>=2024.2.0",
        "tqdm",
    )
    # Prepare SSH known_hosts (so git clone doesn’t prompt)
    .run_commands(
        "mkdir -p /root/.ssh && chmod 700 /root/.ssh",
        "ssh-keyscan -H github.com >> /root/.ssh/known_hosts || true",
    )
)

TUNNEL_NAME = os.environ.get("VSCODE_TUNNEL_NAME", "modaling")

with modal.enable_output():
    sandbox = modal.Sandbox.create(
        "code", "tunnel",
        "--accept-server-license-terms",
        f"--name={TUNNEL_NAME}",
        "--telemetry-level=off",
        # Put vscode cli data into persistent volume so reconnects are stable
        "--cli-data-dir=/volume/vscode-cli",
        timeout=60 * 60 * 24,  # 24h
        image=image,
        app=app,
        # GPU optional. Keep it since you want training later.
        # gpu="A10G",
        volumes={
            "/volume": VSCODE_VOL,  # vscode state + ssh key storage
        },
        secrets=([HF_SECRET] if HF_SECRET is not None else None),
    )

print(f"🏖️ Sandbox ID: {sandbox.object_id}")
print(f"🏖️ VS Code Tunnel name: {TUNNEL_NAME}")
print("🏖️ In VS Code: Remote Explorer → Tunnels → connect by name.")
print("")
print("Inside the sandbox, use /work for your projects (persistent).")
print("Put SSH keys in /volume/ssh (persistent) if you want git@github.com cloning.")
