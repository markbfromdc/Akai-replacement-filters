"""Generate MockbaMod SD card directory layout for Akai Force.

Creates the expected folder structure for a MockbaMod-compatible SD card
(ExFat filesystem, label "662522").
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def generate_sd_layout(
    output_dir: str | Path,
    addons: list[str] | None = None,
    include_bootstrap: bool = True,
) -> Path:
    """Generate the MockbaMod SD card directory structure.

    Creates:
        output_dir/
        ├── AddOns/
        │   └── (addon folders)
        ├── Scripts/
        │   └── bootstrap.sh
        ├── Logs/
        └── Config/
            └── mockba.conf

    Args:
        output_dir: Root directory to create the SD card layout in.
        addons: List of addon folder names to create placeholders for.
        include_bootstrap: Include the bootstrap startup script.

    Returns:
        Path to the created SD card root directory.

    Note:
        The physical SD card must be formatted as ExFat with volume
        label "662522" for MockbaMod to recognize it.
    """
    root = Path(output_dir) / "MockbaMod_SD"
    (root / "AddOns").mkdir(parents=True, exist_ok=True)
    (root / "Scripts").mkdir(exist_ok=True)
    (root / "Logs").mkdir(exist_ok=True)
    (root / "Config").mkdir(exist_ok=True)

    # Create addon placeholder directories
    if addons:
        for addon_name in addons:
            (root / "AddOns" / addon_name).mkdir(exist_ok=True)

    # Bootstrap script
    if include_bootstrap:
        bootstrap = dedent("""\
            #!/bin/bash
            # MockbaMod Bootstrap Script
            # Runs at Force boot when SD card (label: 662522) is inserted.
            #
            # This script is responsible for:
            # 1. Filesystem integrity check
            # 2. Loading addon startup scripts
            # 3. Setting up LD_PRELOAD environment if needed

            SD_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
            LOG_DIR="$SD_ROOT/Logs"
            ADDONS_DIR="$SD_ROOT/AddOns"
            BOOT_LOG="$LOG_DIR/boot_$(date +%Y%m%d_%H%M%S).log"

            echo "=== MockbaMod Bootstrap ===" > "$BOOT_LOG"
            echo "Date: $(date)" >> "$BOOT_LOG"
            echo "SD Root: $SD_ROOT" >> "$BOOT_LOG"

            # Filesystem check
            echo "Running filesystem check..." >> "$BOOT_LOG"
            fsck.fat -a /dev/mmcblk0p1 >> "$BOOT_LOG" 2>&1 || true

            # Load addons
            if [ -d "$ADDONS_DIR" ]; then
                for addon in "$ADDONS_DIR"/*/; do
                    if [ -f "${addon}startup.sh" ]; then
                        echo "Loading addon: $(basename $addon)" >> "$BOOT_LOG"
                        bash "${addon}startup.sh" >> "$BOOT_LOG" 2>&1 &
                    fi
                done
            fi

            echo "Bootstrap complete." >> "$BOOT_LOG"
        """)
        bootstrap_path = root / "Scripts" / "bootstrap.sh"
        bootstrap_path.write_text(bootstrap)
        bootstrap_path.chmod(0o755)

    # Default config
    config = dedent("""\
        # MockbaMod Configuration
        # SD Card Label: 662522 (ExFat)

        # Enable SSH access
        ssh_enabled=true

        # Enable VNC remote display
        vnc_enabled=false

        # Auto-load addons on boot
        auto_load_addons=true

        # Log verbosity (0=quiet, 1=normal, 2=verbose)
        log_level=1
    """)
    (root / "Config" / "mockba.conf").write_text(config)

    return root
