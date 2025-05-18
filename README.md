# WireGuard Configuration Generator

A command-line tool for managing WireGuard VPN interfaces and clients. This project helps you set up and maintain
a WireGuard VPN server, generate client configurations, and render system configuration files for both systemd-networkd
and wg-quick.

## Features

- Create and manage WireGuard interfaces
- Add and remove VPN clients
- Generate configuration files for WireGuard clients
- Export client configuration as QR codes
- Generate systemd-networkd configuration
- Generate wg-quick configuration
- Manage client IP addressing automatically
- Support for both IPv4 and IPv6
- SQLite-based persistent storage

## Installation

### Prerequisites

The tool requires Python 3.10+.

### Install from source

```bash
pip install git+https://github.com/mosquito/wg-gen.git
```

## Usage

### Basic Commands

```bash
# List available commands
wg-gen --help

# Create a new WireGuard interface
wg-gen interface add wg0 --ipv4 10.0.0.1/24 --ipv6 fd00::1/64 --endpoint vpn.example.com:51820 --listen-port 51820

# List all interfaces
wg-gen interface list

# Add a new client to an interface
wg-gen client add wg0 laptop

# Generate client configuration with QR code
wg-gen client add wg0 phone --qr

# List all clients
wg-gen client list

# Remove a client
wg-gen client remove wg0 phone

# Generate systemd-networkd configuration by default to /etc/systemd/network
wg-gen render systemd

# If you want specific output directory
wg-gen render systemd --output ~/test/networkd

# Generate wg-quick configuration by default to /etc/wireguard
wg-gen render wgquick

# If you want specific output directory
wg-gen render wgquick --output ~/wg-quick
```

### Configuration Options

#### Interface Configuration

When adding a new interface, the following options are available:

```bash
wg-gen interface add <interface_name> [OPTIONS]
```

| Option                   | Description                                                | Default                           |
|--------------------------|------------------------------------------------------------|-----------------------------------|
| `--ipv4`                 | IPv4 interface for server with subnet (e.g., 10.0.0.1/24)  | None                              |
| `--ipv6`                 | IPv6 interface for server with subnet (e.g., fd00::1/64)   | None                              |
| `--mtu`                  | MTU to use for the interface                               | 1420                              |
| `--listen-port`          | Server listen port                                         | 51820                             |
| `--endpoint`             | Server endpoint host:port for clients                      | Required                          |
| `--dns`                  | DNS servers for clients                                    | 1.1.1.1, 8.8.8.8                  |
| `--allowed-ips`          | Allowed IPs for peers                                      | 0.0.0.0/0, 2000::/3, 64:ff9b::/96 |
| `--persistent-keepalive` | Persistent keepalive seconds                               | 15                                |

#### Client Configuration

When adding a new client, the following options are available:

```bash
wg-gen client add <interface_name> <client_alias> [OPTIONS]
```

| Option            | Description                                                     | Default |
|-------------------|-----------------------------------------------------------------|--------|
| `--preshared-key` | Use a preshared key for additional security                     | False  |
| `--force`         | Overwrite existing client with the same alias on same interface | False  |
| `--qr`            | Display client configuration as a QR code                       | False  |

## How It Works

1. The tool maintains a SQLite database of interfaces and clients
2. When adding an interface, it generates WireGuard keys and stores the configuration
3. When adding a client, it assigns the next available IP addresses from the interface's subnet
4. Client configurations include private keys, server endpoint, and allowed IPs
5. The render commands output configuration files for various init systems

## Example Setup

### Create a WireGuard Server

```bash
# Create interface with IPv4 and IPv6 subnets
wg-gen interface add wg0 \
  --ipv4 10.7.0.1/24 \
  --ipv6 fd00:7::1/64 \
  --endpoint vpn.example.com:51820 \
  --dns 1.1.1.1 9.9.9.9

# Generate systemd-networkd configuration
wg-gen render systemd

# Activate the interface
systemctl restart systemd-networkd
```

### Add Clients

```bash
# Add a client named 'laptop'
wg-gen client add wg0 laptop

# Add a client 'phone' with QR code for mobile app
wg-gen client add wg0 phone --qr
```

## Directory Structure

- `wg_gen/`: Main package
  - `cli/`: Command-line interface modules
  - `db.py`: Database interface
  - `keygen.py`: Key generation utilities
  - `table.py`: Table formatting for output
  - `__main__.py`: Entry point

## Database Location

By default, the SQLite database is stored at `~/.local/share/wg-gen/database.sqlite3`. 
You can specify a different location with the `--db-path` option.

## Configuration Files

Utility support read configuration files from `~/.config/wg-gen/config.yaml` by default or from path located in 
`WG_GEN_CONFIG` environment variable.

### Example

```ini
[DEFAULT]
# Default configuration for wg-gen will be written to ~/.config/wg-gen/config.yaml 
# when database is created
db_path = ~/.local/share/wg-gen/database.sqlite3

log_level = info
```
