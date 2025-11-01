import os
import modal

app = modal.App.lookup("A10G-vscode-tunnel", create_if_missing=True)

image = (
    modal.Image
        .debian_slim(python_version="3.12")
        .apt_install(
            # base + git + ssh client + tools
            "wget", "ca-certificates", "tar", "git", "openssh-client",
            "ffmpeg", "libsm6", "libxext6", "unzip", "zip", "htop", "curl", "nano"
        )
        # Install VS Code CLI (linux build) and put on PATH
        .run_commands(
            "wget -O /tmp/vscode_cli.tar.gz 'https://code.visualstudio.com/sha/download?build=stable&os=cli-linux-x64' && "
            "mkdir -p /opt/vscode && tar -xzf /tmp/vscode_cli.tar.gz -C /opt/vscode && "
            "ln -sf /opt/vscode/code /usr/local/bin/code && "
            "code --version"
        )
        # SSH + Git setup
        .run_commands(
            # Prepare ~/.ssh and known_hosts
            "mkdir -p /root/.ssh && chmod 700 /root/.ssh && "
            "ssh-keyscan -H github.com >> /root/.ssh/known_hosts && "
            # If keys exist in /volume/ssh, set strict perms (done again at runtime is OK)
            "mkdir -p /volume/ssh && "
            "if [ -f /volume/ssh/id_ed25519 ]; then chmod 700 /volume/ssh && chmod 600 /volume/ssh/id_ed25519; fi && "
            "if [ -f /volume/ssh/id_ed25519.pub ]; then chmod 644 /volume/ssh/id_ed25519.pub; fi && "
            # Point SSH to use the volume key for GitHub
            "printf 'Host github.com\\n  HostName github.com\\n  User git\\n  IdentityFile /volume/ssh/id_ed25519\\n  IdentitiesOnly yes\\n' > /root/.ssh/config && "
            "chmod 600 /root/.ssh/config && "
            # Global Git identity
            "git config --global user.email 'husain.a.althagafi@okaz.com' && "
            "git config --global user.name 'Husain-Althagafi' && "
            "git clone git@github.com:Husain-Althagafi/Kaust_project.git /root/mjo/Kaust_project || echo 'Repo already cloned.'"
            "git clone git@github.com:Husain-Althagafi/Generation.git /root/mjo/Generation || echo 'Repo already cloned.'"
            "uv venv generationVenv"
            "source generationVenv/bin/activate"
            "uv pip install datasets --upgrade && uv pip install pycocotools scikit-learn mne polars[gpu] open_clip_torch einops wandb braindecode reformer_pytorch && uv pip install numpy==2.1.2 && uv pip install cudf-cu12 && uv pip install scipy==1.11.2 && uv pip install diffusers==0.24.0 && uv pip install numpy==2.1.2 && uv pip install cudf-cu12 && uv pip install scipy==1.11.2 && uv pip install huggingface-hub==0.25.0 && uv pip install transformers==4.34.0 pip install git+https://github.com/openai/CLIP.gitpip install git+https://github.com/openai/CLIP.git"
            "python3 /root/mjo/Generation/download_datasets.py"
            "deactivate"
            )
        # Your dirs & dataset
        .run_commands(
            "mkdir -p /root/mjo/upb && "
            "mkdir -p /root/mjo/datasets/things-eeg/image_set/training_images && "
            "mkdir -p /root/mjo/datasets/things-eeg/image_set/test_images"
        )
        .run_commands(
            "wget -O training.zip https://osf.io/download/3v527/ && "
            "wget -O test.zip https://osf.io/download/znu7b/ && "
            "unzip training.zip -d /root/mjo/datasets/things-eeg/image_set/training_images && "
            "unzip test.zip -d /root/mjo/datasets/things-eeg/image_set/test_images && "
            "rm training.zip test.zip"
        )
)

TUNNEL_NAME = os.environ.get("VSCODE_TUNNEL_NAME", "modaling")

print("🏖️  Creating sandbox (VS Code Tunnel)")
with modal.enable_output():
    sandbox = modal.Sandbox.create(
        "code", "tunnel",
        "--accept-server-license-terms",
        f"--name={TUNNEL_NAME}",
        "--telemetry-level=off",
        "--cli-data-dir=/volume/vscode-cli",
        timeout=60 * 60 * 24 * 1,  # 24h
        image=image,
        app=app,
        gpu="A10G",
        volumes={"/volume": modal.Volume.from_name("vscode-volume", create_if_missing=True)},
    )

print(f"🏖️  Sandbox ID: {sandbox.object_id}")
print(f"🏖️  VS Code Tunnel name: {TUNNEL_NAME}")
print("🏖️  In VS Code, open Remote Explorer → Tunnels and connect to the tunnel by name.")
