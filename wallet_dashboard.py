#!/usr/bin/env python3
"""
wallet_dashboard.py

Enhanced wallet.dat scanner with an interactive dashboard interface.

Features:
  1. Manual private key input (paste raw keys)
  2. Load wallet.dat files from directory
  3. Load wallet.dat files from ZIP archive
  4. Batch scan with speed optimization
  5. View results in real-time
  6. Export reports in multiple formats
  7. Settings & configuration panel

Usage:
    python wallet_dashboard.py

No arguments needed - the dashboard guides you through all options.
"""

import argparse
import csv
import getpass
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import json
import zipfile
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("Missing dependency. Run:  pip install -r requirements.txt")
    sys.exit(1)

LINE_ADDR_RE = re.compile(r"addr=([a-km-zA-HJ-NP-Z1-9]{25,90})")
PRIVKEY_RE = re.compile(r"[5KL][1-9A-HJ-NP-Za-km-z]{50,51}")
API_BASE = "https://blockstream.info/api"
RPC_PORT = 18754

# ANSI color codes for terminal UI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class WalletDashboard:
    """Main interactive dashboard controller."""
    
    def __init__(self):
        self.config = {
            'api_delay': 0.3,
            'retries': 3,
            'keep_dumps': False,
            'output_dir': './wallet_reports',
            'verbose': True,
        }
        self.results = []
        self.node = None
        self.dump_dir = None
        self.wallet_files = []
        self.setup_output_dir()
        
    def setup_output_dir(self):
        """Create output directory if it doesn't exist."""
        os.makedirs(self.config['output_dir'], exist_ok=True)
    
    def print_header(self):
        """Display main dashboard header."""
        print("\n")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}")
        print(f"{'BITCOIN WALLET SCANNER DASHBOARD':^70}")
        print(f"Secure • Fast • Transparent • Open Source")
        print(f"{'='*70}{Colors.END}\n")
    
    def print_menu(self):
        """Display main menu options."""
        print(f"{Colors.BOLD}What would you like to do?{Colors.END}\n")
        print(f"{Colors.BLUE}[1]{Colors.END} Scan wallet.dat files from directory")
        print(f"{Colors.BLUE}[2]{Colors.END} Extract and scan wallet.dat from ZIP archive")
        print(f"{Colors.BLUE}[3]{Colors.END} Paste private keys directly")
        print(f"{Colors.BLUE}[4]{Colors.END} View previous reports")
        print(f"{Colors.BLUE}[5]{Colors.END} Configure settings")
        print(f"{Colors.BLUE}[0]{Colors.END} Exit\n")
    
    def get_menu_choice(self):
        """Get and validate menu choice."""
        while True:
            choice = input(f"{Colors.YELLOW}Enter your choice (0-5): {Colors.END}").strip()
            if choice in ['0', '1', '2', '3', '4', '5']:
                return choice
            print(f"{Colors.RED}Invalid choice. Please enter 0-5.{Colors.END}\n")
    
    def check_binaries(self):
        """Verify Bitcoin Core binaries are available."""
        for b in ("bitcoind", "bitcoin-cli"):
            if shutil.which(b) is None:
                print(f"{Colors.RED}ERROR: '{b}' not found on your PATH.{Colors.END}")
                print("Install Bitcoin Core: https://bitcoincore.org/en/download/")
                print(f"Recommended version: 22.x - 25.x")
                return False
        return True
    
    def option_1_scan_directory(self):
        """Option 1: Scan wallet.dat files from a directory."""
        print(f"\n{Colors.BOLD}Option 1: Scan Directory{Colors.END}")
        print("-" * 50)
        
        while True:
            wallet_dir = input(f"\nEnter path to wallets directory: {Colors.YELLOW}").strip() + Colors.END
            if os.path.isdir(wallet_dir):
                break
            print(f"{Colors.RED}Directory not found. Please try again.{Colors.END}\n")
        
        wallet_files = sorted(glob.glob(os.path.join(wallet_dir, "*.dat")))
        if not wallet_files:
            print(f"{Colors.RED}No .dat files found in {wallet_dir}{Colors.END}")
            return
        
        print(f"\n{Colors.GREEN}✓ Found {len(wallet_files)} wallet.dat file(s){Colors.END}")
        for wf in wallet_files:
            print(f"  • {os.path.basename(wf)}")
        
        confirm = input(f"\n{Colors.YELLOW}Proceed with scan? (y/n): {Colors.END}").strip().lower()
        if confirm == 'y':
            self.wallet_files = wallet_files
            self.run_scan()
        else:
            print("Scan cancelled.")
    
    def option_2_scan_zip(self):
        """Option 2: Extract and scan wallet.dat files from ZIP."""
        print(f"\n{Colors.BOLD}Option 2: Scan ZIP Archive{Colors.END}")
        print("-" * 50)
        
        while True:
            zip_path = input(f"\nEnter path to ZIP file: {Colors.YELLOW}").strip() + Colors.END
            if os.path.isfile(zip_path) and zip_path.endswith('.zip'):
                break
            print(f"{Colors.RED}ZIP file not found. Please try again.{Colors.END}\n")
        
        # Create temp directory for extraction
        extract_dir = tempfile.mkdtemp(prefix="wallet_zip_")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)
            
            wallet_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.dat'):
                        wallet_files.append(os.path.join(root, file))
            
            wallet_files = sorted(wallet_files)
            
            if not wallet_files:
                print(f"{Colors.RED}No .dat files found in ZIP{Colors.END}")
                return
            
            print(f"\n{Colors.GREEN}✓ Extracted {len(wallet_files)} wallet.dat file(s){Colors.END}")
            for wf in wallet_files:
                print(f"  • {os.path.basename(wf)}")
            
            confirm = input(f"\n{Colors.YELLOW}Proceed with scan? (y/n): {Colors.END}").strip().lower()
            if confirm == 'y':
                self.wallet_files = wallet_files
                self.run_scan()
            else:
                print("Scan cancelled.")
        except zipfile.BadZipFile:
            print(f"{Colors.RED}Invalid ZIP file.{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error: {str(e)}{Colors.END}")
        finally:
            if not self.config['keep_dumps']:
                shutil.rmtree(extract_dir, ignore_errors=True)
    
    def option_3_manual_keys(self):
        """Option 3: Paste private keys directly and check balances."""
        print(f"\n{Colors.BOLD}Option 3: Manual Private Key Input{Colors.END}")
        print("-" * 50)
        print(f"\n{Colors.YELLOW}Paste Bitcoin private keys (WIF format), one per line.")
        print("Press Ctrl+D (Unix/Mac) or Ctrl+Z then Enter (Windows) when done.{Colors.END}\n")
        
        private_keys = []
        try:
            while True:
                line = input().strip()
                if line and PRIVKEY_RE.match(line):
                    private_keys.append(line)
                    print(f"{Colors.GREEN}✓ Key added{Colors.END}")
                elif line:
                    print(f"{Colors.RED}Invalid key format (expected WIF){Colors.END}")
        except EOFError:
            pass
        
        if not private_keys:
            print(f"{Colors.RED}No valid keys entered.{Colors.END}")
            return
        
        print(f"\n{Colors.GREEN}✓ Loaded {len(private_keys)} private key(s){Colors.END}")
        print(f"\n{Colors.YELLOW}WARNING: This requires Bitcoin Core to derive addresses.{Colors.END}")
        print("Proceeding will load keys into a temporary, isolated wallet.\n")
        
        confirm = input(f"{Colors.YELLOW}Continue? (y/n): {Colors.END}").strip().lower()
        if confirm == 'y':
            self.check_private_keys(private_keys)
        else:
            print("Operation cancelled.")
    
    def check_private_keys(self, private_keys):
        """Check balances for manually entered private keys."""
        if not self.check_binaries():
            return
        
        self.node = Node()
        self.dump_dir = tempfile.mkdtemp(prefix="wallet_keys_")
        
        print(f"\n{Colors.BOLD}Starting Bitcoin Core node...{Colors.END}")
        self.node.start()
        
        results = []
        try:
            for i, privkey in enumerate(private_keys, 1):
                print(f"\n{Colors.BLUE}[{i}/{len(private_keys)}]{Colors.END} Checking key...")
                
                # Use bitcoin-cli to get address from private key
                wallet_name = f"manual_key_{i}"
                wdir = os.path.join(self.node.datadir, "wallets", wallet_name)
                os.makedirs(wdir, exist_ok=True)
                
                # Create wallet
                r = self.node.cli("createwallet", wallet_name)
                if r.returncode != 0:
                    print(f"{Colors.RED}✗ Could not create wallet: {r.stderr.strip()[:100]}{Colors.END}")
                    continue
                
                # Import private key
                r = self.node.cli(f"-rpcwallet={wallet_name}", "importprivkey", privkey, f"key_{i}", "false")
                if r.returncode != 0:
                    print(f"{Colors.RED}✗ Could not import key: {r.stderr.strip()[:100]}{Colors.END}")
                    self.node.cli("unloadwallet", wallet_name)
                    continue
                
                # Rescan
                print(f"{Colors.BLUE}Rescanning blockchain...{Colors.END}")
                self.node.cli(f"-rpcwallet={wallet_name}", "rescanblockchain")
                
                # Get address
                r = self.node.cli(f"-rpcwallet={wallet_name}", "getaddressesbylabel", f"key_{i}")
                if r.returncode != 0:
                    print(f"{Colors.RED}✗ Could not get address{Colors.END}")
                    self.node.cli("unloadwallet", wallet_name)
                    continue
                
                try:
                    addresses = list(json.loads(r.stdout).keys())
                    if not addresses:
                        print(f"{Colors.YELLOW}No address found{Colors.END}")
                        self.node.cli("unloadwallet", wallet_name)
                        continue
                    
                    address = addresses[0]
                    print(f"{Colors.CYAN}Address: {address}{Colors.END}")
                    
                    # Check balance
                    balance = get_balance_btc(address, self.config['retries'], self.config['api_delay'])
                    if balance is not None:
                        status = "HAS BALANCE" if balance > 0 else "EMPTY"
                        color = Colors.GREEN if balance > 0 else Colors.YELLOW
                        print(f"{color}Balance: {balance:.8f} BTC [{status}]{Colors.END}")
                        results.append({
                            "key": f"manual_key_{i}",
                            "address": address,
                            "balance_btc": round(balance, 8),
                            "status": status
                        })
                    else:
                        print(f"{Colors.RED}✗ Could not fetch balance (API error){Colors.END}")
                
                except json.JSONDecodeError:
                    print(f"{Colors.RED}✗ Invalid response from Bitcoin Core{Colors.END}")
                finally:
                    self.node.cli("unloadwallet", wallet_name)
                    time.sleep(self.config['api_delay'])
        
        finally:
            self.node.stop()
            self.node.cleanup()
            if not self.config['keep_dumps']:
                shutil.rmtree(self.dump_dir, ignore_errors=True)
        
        self.results = results
        if results:
            self.display_results()
            self.export_results("manual_keys")
    
    def option_4_view_reports(self):
        """Option 4: View previous reports."""
        print(f"\n{Colors.BOLD}Option 4: Previous Reports{Colors.END}")
        print("-" * 50)
        
        reports = sorted(glob.glob(os.path.join(self.config['output_dir'], "*.csv")))
        if not reports:
            print(f"{Colors.RED}No reports found.{Colors.END}")
            return
        
        print(f"\n{Colors.GREEN}Found {len(reports)} report(s):{Colors.END}\n")
        for i, report in enumerate(reports, 1):
            print(f"{Colors.BLUE}[{i}]{Colors.END} {os.path.basename(report)}")
        
        while True:
            choice = input(f"\n{Colors.YELLOW}Select report (1-{len(reports)}) or 0 to cancel: {Colors.END}").strip()
            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(reports):
                    self.display_report(reports[idx])
                    break
            except ValueError:
                pass
            print(f"{Colors.RED}Invalid selection.{Colors.END}")
    
    def option_5_settings(self):
        """Option 5: Configure settings."""
        print(f"\n{Colors.BOLD}Option 5: Settings{Colors.END}")
        print("-" * 50)
        print(f"\n{Colors.BLUE}[1]{Colors.END} API delay (current: {self.config['api_delay']}s)")
        print(f"{Colors.BLUE}[2]{Colors.END} Keep dump files (current: {self.config['keep_dumps']})")
        print(f"{Colors.BLUE}[3]{Colors.END} Output directory (current: {self.config['output_dir']})")
        print(f"{Colors.BLUE}[0]{Colors.END} Back\n")
        
        choice = input(f"{Colors.YELLOW}Choose setting to modify (0-3): {Colors.END}").strip()
        
        if choice == '1':
            try:
                delay = float(input(f"Enter API delay in seconds (default 0.3): {Colors.YELLOW}").strip() or "0.3") + Colors.END
                if delay >= 0:
                    self.config['api_delay'] = delay
                    print(f"{Colors.GREEN}✓ Updated{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Invalid input{Colors.END}")
        
        elif choice == '2':
            self.config['keep_dumps'] = not self.config['keep_dumps']
            print(f"{Colors.GREEN}✓ Updated to {self.config['keep_dumps']}{Colors.END}")
        
        elif choice == '3':
            new_dir = input(f"Enter output directory: {Colors.YELLOW}").strip() + Colors.END
            if new_dir:
                self.config['output_dir'] = new_dir
                self.setup_output_dir()
                print(f"{Colors.GREEN}✓ Updated{Colors.END}")
    
    def run_scan(self):
        """Execute the wallet scan."""
        if not self.check_binaries():
            return
        
        self.node = Node()
        self.dump_dir = tempfile.mkdtemp(prefix="wallet_dumps_")
        
        print(f"\n{Colors.BOLD}Starting Bitcoin Core node...{Colors.END}")
        self.node.start()
        
        rows = []
        try:
            for i, wf in enumerate(self.wallet_files, 1):
                name = os.path.splitext(os.path.basename(wf))[0]
                total = len(self.wallet_files)
                print(f"\n{Colors.BLUE}[{i}/{total}]{Colors.END} {Colors.BOLD}{name}{Colors.END}")
                print("-" * 40)
                
                dump_file = dump_wallet(self.node, wf, self.dump_dir)
                if not dump_file:
                    print(f"{Colors.RED}✗ Could not load wallet{Colors.END}")
                    rows.append({
                        "wallet": name, "addresses_found": 0, "addresses_checked": 0,
                        "funded_addresses": 0, "total_btc": 0.0, "status": "FAILED"
                    })
                    continue
                
                addrs = extract_addresses(dump_file)
                total_btc, funded, checked = 0.0, 0, 0
                
                print(f"{Colors.CYAN}Checking {len(addrs)} address(es)...{Colors.END}")
                
                for j, a in enumerate(addrs, 1):
                    bal = get_balance_btc(a, self.config['retries'], self.config['api_delay'])
                    if (j % 10 == 0):
                        print(f"  [{j}/{len(addrs)}] ", end="", flush=True)
                    
                    if bal is None:
                        continue
                    checked += 1
                    if bal > 0:
                        funded += 1
                        total_btc += bal
                        print(f"\n{Colors.GREEN}  ✓ Found: {a}: {bal:.8f} BTC{Colors.END}")
                
                status = "HAS BALANCE" if total_btc > 0 else "EMPTY"
                color = Colors.GREEN if total_btc > 0 else Colors.YELLOW
                
                print(f"\n{color}Result: {total_btc:.8f} BTC across {funded} address(es) [{status}]{Colors.END}")
                
                rows.append({
                    "wallet": name,
                    "addresses_found": len(addrs),
                    "addresses_checked": checked,
                    "funded_addresses": funded,
                    "total_btc": round(total_btc, 8),
                    "status": status
                })
        
        finally:
            self.node.stop()
            self.node.cleanup()
            if not self.config['keep_dumps']:
                shutil.rmtree(self.dump_dir, ignore_errors=True)
            else:
                print(f"\n{Colors.YELLOW}Dump files kept at: {self.dump_dir}{Colors.END}")
        
        self.results = rows
        if rows:
            self.display_results()
            self.export_results("scan")
    
    def display_results(self):
        """Display results in formatted table."""
        if not self.results:
            print(f"{Colors.RED}No results to display.{Colors.END}")
            return
        
        self.results.sort(key=lambda r: r.get("total_btc", 0) if isinstance(r.get("total_btc"), (int, float)) else 0, reverse=True)
        
        print(f"\n{Colors.BOLD}{'='*70}")
        print(f"RESULTS SUMMARY")
        print(f"{'='*70}{Colors.END}\n")
        
        # Summary stats
        total_btc_all = sum(r.get("total_btc", 0) if isinstance(r.get("total_btc"), (int, float)) else 0 for r in self.results)
        funded_count = sum(1 for r in self.results if r.get("status") == "HAS BALANCE")
        
        print(f"{Colors.GREEN}Total BTC found: {total_btc_all:.8f}{Colors.END}")
        print(f"{Colors.GREEN}Wallets with balance: {funded_count}/{len(self.results)}{Colors.END}\n")
        
        # Detailed table
        print(f"{Colors.BOLD}{'Wallet':<20} {'Addresses':<12} {'Funded':<10} {'Balance (BTC)':<15} {'Status':<15}{Colors.END}")
        print("-" * 72)
        
        for r in self.results:
            wallet = r.get("wallet", "unknown")[:19]
            addr_found = r.get("addresses_found", 0)
            funded = r.get("funded_addresses", 0)
            balance = r.get("total_btc", 0)
            status = r.get("status", "UNKNOWN")
            
            color = Colors.GREEN if status == "HAS BALANCE" else Colors.YELLOW
            
            print(f"{wallet:<20} {addr_found:<12} {funded:<10} {balance:<15.8f} {color}{status:<15}{Colors.END}")
        
        print()
    
    def export_results(self, prefix="scan"):
        """Export results to CSV and JSON."""
        if not self.results:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(self.config['output_dir'], f"{prefix}_{timestamp}.csv")
        json_path = os.path.join(self.config['output_dir'], f"{prefix}_{timestamp}.json")
        
        # CSV export
        try:
            with open(csv_path, 'w', newline='') as f:
                if self.results and 'wallet' in self.results[0]:
                    fieldnames = list(self.results[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.results)
            print(f"{Colors.GREEN}✓ CSV report: {csv_path}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}✗ CSV export failed: {str(e)}{Colors.END}")
        
        # JSON export
        try:
            with open(json_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"{Colors.GREEN}✓ JSON report: {json_path}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}✗ JSON export failed: {str(e)}{Colors.END}")
    
    def display_report(self, report_path):
        """Display a CSV report in formatted table."""
        try:
            with open(report_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            print(f"\n{Colors.BOLD}{'='*70}")
            print(f"REPORT: {os.path.basename(report_path)}")
            print(f"{'='*70}{Colors.END}\n")
            
            # Summary
            total_btc = sum(float(r.get("total_btc", 0)) for r in rows)
            funded = sum(1 for r in rows if r.get("status") == "HAS BALANCE")
            
            print(f"{Colors.GREEN}Total BTC: {total_btc:.8f}{Colors.END}")
            print(f"{Colors.GREEN}Funded wallets: {funded}/{len(rows)}{Colors.END}\n")
            
            # Table
            print(f"{Colors.BOLD}{'Wallet':<20} {'Addresses':<12} {'Balance (BTC)':<15}{Colors.END}")
            print("-" * 47)
            
            for r in rows:
                wallet = r.get("wallet", "unknown")[:19]
                addrs = r.get("addresses_checked", 0)
                balance = float(r.get("total_btc", 0))
                
                color = Colors.GREEN if balance > 0 else Colors.YELLOW
                print(f"{wallet:<20} {addrs:<12} {color}{balance:<15.8f}{Colors.END}")
            
            print()
        except Exception as e:
            print(f"{Colors.RED}Error reading report: {str(e)}{Colors.END}")
    
    def run(self):
        """Main dashboard loop."""
        while True:
            self.print_header()
            self.print_menu()
            choice = self.get_menu_choice()
            
            if choice == '0':
                print(f"\n{Colors.GREEN}Thank you for using Wallet Scanner. Goodbye!{Colors.END}\n")
                break
            elif choice == '1':
                self.option_1_scan_directory()
            elif choice == '2':
                self.option_2_scan_zip()
            elif choice == '3':
                self.option_3_manual_keys()
            elif choice == '4':
                self.option_4_view_reports()
            elif choice == '5':
                self.option_5_settings()
            
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.END}")


class Node:
    """Manages a throwaway local bitcoind instance (no blockchain sync needed)."""

    def __init__(self):
        self.datadir = tempfile.mkdtemp(prefix="wallet_scanner_")
        self.rpcpass = f"scanner_{int(time.time())}_{os.getpid()}"
        conf_path = os.path.join(self.datadir, "bitcoin.conf")
        with open(conf_path, "w") as f:
            f.write(
                "server=1\nlisten=0\nconnect=0\ndnsseed=0\nupnp=0\n"
                f"rpcport={RPC_PORT}\nrpcuser=scanner\nrpcpassword={self.rpcpass}\n"
                "prune=550\n"
            )

    def cli(self, *args, check=True):
        cmd = ["bitcoin-cli", f"-datadir={self.datadir}",
               "-rpcuser=scanner", f"-rpcpassword={self.rpcpass}", *args]
        return subprocess.run(cmd, capture_output=True, text=True)

    def start(self):
        subprocess.run(["bitcoind", f"-datadir={self.datadir}", "-daemon"],
                        capture_output=True, text=True)
        for _ in range(30):
            r = self.cli("getblockchaininfo")
            if r.returncode == 0:
                return
            time.sleep(1)
        print(f"{Colors.RED}ERROR: bitcoind did not start in time.{Colors.END}")
        sys.exit(1)

    def stop(self):
        self.cli("stop")
        time.sleep(2)

    def cleanup(self):
        shutil.rmtree(self.datadir, ignore_errors=True)


def dump_wallet(node, wallet_path, dump_dir):
    """Extract addresses from a wallet.dat file."""
    name = os.path.splitext(os.path.basename(wallet_path))[0]
    wdir = os.path.join(node.datadir, "wallets", name)
    os.makedirs(wdir, exist_ok=True)
    shutil.copy(wallet_path, os.path.join(wdir, "wallet.dat"))

    r = node.cli("loadwallet", name)
    if r.returncode != 0:
        return None

    dump_file = os.path.join(dump_dir, f"{name}_dump.txt")
    r = node.cli(f"-rpcwallet={name}", "dumpwallet", dump_file)
    if r.returncode != 0:
        passphrase = getpass.getpass(f"  Enter passphrase for '{name}' (blank to skip): ")
        if passphrase:
            node.cli(f"-rpcwallet={name}", "walletpassphrase", passphrase, "120")
            r = node.cli(f"-rpcwallet={name}", "dumpwallet", dump_file)
        if r.returncode != 0:
            node.cli("unloadwallet", name)
            return None

    node.cli("unloadwallet", name)
    return dump_file


def extract_addresses(dump_path):
    """Extract Bitcoin addresses from wallet dump file."""
    addrs = set()
    with open(dump_path, "r", errors="ignore") as f:
        for line in f:
            m = LINE_ADDR_RE.search(line)
            if m:
                addrs.add(m.group(1))
    return addrs


def get_balance_btc(address, retries=3, delay=0.3):
    """Fetch real on-chain balance from Blockstream API."""
    url = f"{API_BASE}/address/{address}"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
        except requests.RequestException:
            time.sleep(delay * (attempt + 1))
            continue
        if r.status_code == 200:
            d = r.json()
            funded = d["chain_stats"]["funded_txo_sum"] + d["mempool_stats"]["funded_txo_sum"]
            spent = d["chain_stats"]["spent_txo_sum"] + d["mempool_stats"]["spent_txo_sum"]
            return (funded - spent) / 1e8
        elif r.status_code == 429:
            time.sleep(delay * (attempt + 1))
        else:
            return None
    return None


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Bitcoin wallet.dat scanner with interactive dashboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wallet_dashboard.py              # Launch interactive dashboard
  python wallet_dashboard.py --help       # Show this help message
        """
    )
    parser.add_argument("--legacy", action="store_true",
                       help="Use legacy command-line interface instead of dashboard")
    args = parser.parse_args()
    
    if args.legacy:
        # Fall back to original scan_wallets.py
        print("Legacy mode not implemented yet. Use --help for dashboard mode.")
    else:
        # Launch dashboard
        dashboard = WalletDashboard()
        dashboard.run()


if __name__ == "__main__":
    main()
