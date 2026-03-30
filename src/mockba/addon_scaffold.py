"""Generate MockbaMod addon folder structures for Akai Force.

Creates the directory layout, manifest, startup scripts, and optional
Node.js server stubs compatible with the MockbaMod addon manager.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


def scaffold_addon(
    addon_name: str,
    description: str = "",
    version: str = "1.0.0",
    author: str = "",
    include_server: bool = False,
    output_dir: str | Path = ".",
) -> Path:
    """Generate a MockbaMod addon folder structure.

    Creates:
        addon_name/
        ├── manifest.json
        ├── startup.sh
        ├── startup.lua       (optional Lua startup script)
        ├── README.md
        └── server/           (if include_server=True)
            ├── package.json
            └── index.js

    Args:
        addon_name: Name of the addon (used as folder name).
        description: Addon description for the manifest.
        version: Addon version string.
        author: Addon author name.
        include_server: Include a Node.js web server stub.
        output_dir: Parent directory to create the addon in.

    Returns:
        Path to the created addon directory.
    """
    addon_dir = Path(output_dir) / addon_name
    addon_dir.mkdir(parents=True, exist_ok=True)

    # manifest.json
    manifest = {
        "name": addon_name,
        "description": description or f"{addon_name} MockbaMod addon",
        "version": version,
        "author": author,
        "type": "addon",
        "startup": "startup.sh",
        "compatible_firmware": ["4.0.0+"],
    }
    (addon_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # startup.sh
    startup_sh = dedent(f"""\
        #!/bin/bash
        # {addon_name} - MockbaMod Addon Startup Script
        # This script runs when the Force boots with the MockbaMod SD card inserted.

        ADDON_DIR="$(cd "$(dirname "$0")" && pwd)"
        LOG_FILE="/tmp/{addon_name}.log"

        echo "[{addon_name}] Starting addon..." > "$LOG_FILE"
        echo "[{addon_name}] Addon directory: $ADDON_DIR" >> "$LOG_FILE"

        # Add your initialization logic here
        # Example: load custom LD_PRELOAD libraries
        # export LD_PRELOAD="$ADDON_DIR/libs/custom_filter.so:$LD_PRELOAD"

        {"# Start Node.js server" if include_server else "# No server configured"}
        {"cd $ADDON_DIR/server && node index.js >> $LOG_FILE 2>&1 &" if include_server else ""}

        echo "[{addon_name}] Startup complete." >> "$LOG_FILE"
    """)
    startup_path = addon_dir / "startup.sh"
    startup_path.write_text(startup_sh)
    startup_path.chmod(0o755)

    # startup.lua (alternative Lua startup)
    startup_lua = dedent(f"""\
        -- {addon_name} - MockbaMod Addon Startup (Lua)
        -- This script provides an alternative Lua-based startup.

        print("[{addon_name}] Lua startup executing...")

        -- Configuration
        local config = {{
            name = "{addon_name}",
            version = "{version}",
        }}

        -- Add your Lua initialization logic here
        -- MockbaMod provides Lua scripting capabilities for Force automation.

        print("[{addon_name}] Lua startup complete.")
    """)
    (addon_dir / "startup.lua").write_text(startup_lua)

    # README.md
    readme = dedent(f"""\
        # {addon_name}

        {description or "A MockbaMod addon for Akai Force."}

        ## Installation

        1. Copy the `{addon_name}` folder to the `AddOns` directory on your MockbaMod SD card
        2. Restart the Force with the SD card inserted
        3. The addon will start automatically

        ## Version

        {version}
    """)
    (addon_dir / "README.md").write_text(readme)

    # Optional Node.js server
    if include_server:
        server_dir = addon_dir / "server"
        server_dir.mkdir(exist_ok=True)

        package_json = {
            "name": f"{addon_name}-server",
            "version": version,
            "main": "index.js",
            "scripts": {"start": "node index.js"},
        }
        (server_dir / "package.json").write_text(json.dumps(package_json, indent=2))

        index_js = dedent(f"""\
            // {addon_name} - MockbaMod Web Server
            // Compatible with FORCE-APPS-SERVER-MOCKBA pattern

            const http = require('http');
            const PORT = 8080;

            const server = http.createServer((req, res) => {{
              if (req.url === '/status') {{
                res.writeHead(200, {{ 'Content-Type': 'application/json' }});
                res.end(JSON.stringify({{
                  addon: '{addon_name}',
                  version: '{version}',
                  status: 'running'
                }}));
              }} else {{
                res.writeHead(200, {{ 'Content-Type': 'text/html' }});
                res.end('<h1>{addon_name}</h1><p>MockbaMod Addon Running</p>');
              }}
            }});

            server.listen(PORT, () => {{
              console.log(`[{addon_name}] Server running on port ${{PORT}}`);
            }});
        """)
        (server_dir / "index.js").write_text(index_js)

    return addon_dir
