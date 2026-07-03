# Installing OpenOSINT Systemd Services

Two unit files are provided. Install with:

```bash
sudo cp openosint-mcp.service /etc/systemd/system/
sudo cp openosint-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openosint-mcp.service   # MCP server
sudo systemctl enable --now openosint-web.service    # Web UI (optional, ports 8080)
```

Check status:
```bash
sudo systemctl status openosint-mcp.service
sudo journalctl -u openosint-mcp -f
```
