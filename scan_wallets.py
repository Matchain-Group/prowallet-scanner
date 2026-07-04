#!/usr/bin/env python3
"""
scan_wallets.py

Scan a folder of Bitcoin `wallet.dat` files, extract every address from
each one, and check REAL on-chain balances - so you can tell which of
your old wallets are empty and which still hold funds.

    python scan_wallets.py /path/to/wallets_folder --out report.csv

One command. No manual steps. See README.md for setup + security notes.

Requirements:
    - Bitcoin Core (bitcoind + bitcoin-cli) installed and on your PATH.
      Version 22.x-25.x recommended for best legacy wallet.dat support -
      some newer Core builds drop old Berkeley DB wallet support.
    - pip install -r requirements.txt   (just needs `requests`)
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

try:
    import requests
except ImportError:
    print("Missing dependency. Run:  pip install -r requirements.txt")
    sys.exit(1)

LINE_ADDR_RE = re.compile(r"addr=([a-km-zA-HJ-NP-Z1-9]{25,90})")
API_BASE = "https://blockstream.info/api"
RPC_PORT = 18754


def check_binaries():
    for b in ("bitcoind", "bitcoin-cli"):
        if shutil.which(b) is None:
            print(f"ERROR: '{b}' not found on your PATH.")
            print("Install Bitcoin Core first: https://bitcoincore.org/en/download/")
            sys.exit(1)


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
        print("ERROR: bitcoind did not start in time.")
        sys.exit(1)

    def stop(self):
        self.cli("stop")
        time.sleep(3)

    def cleanup(self):
        shutil.rmtree(self.datadir, ignore_errors=True)


def dump_wallet(node, wallet_path, dump_dir):
    name = os.path.splitext(os.path.basename(wallet_path))[0]
    wdir = os.path.join(node.datadir, "wallets", name)
    os.makedirs(wdir, exist_ok=True)
    shutil.copy(wallet_path, os.path.join(wdir, "wallet.dat"))

    r = node.cli("loadwallet", name)
    if r.returncode != 0:
        print(f"  FAILED to load ({r.stderr.strip()[:200]})")
        return None

    dump_file = os.path.join(dump_dir, f"{name}_dump.txt")
    r = node.cli(f"-rpcwallet={name}", "dumpwallet", dump_file)
    if r.returncode != 0:
        print("  appears encrypted.")
        passphrase = getpass.getpass(f"  Enter passphrase for '{name}' (blank to skip): ")
        if passphrase:
            node.cli(f"-rpcwallet={name}", "walletpassphrase", passphrase, "120")
            r = node.cli(f"-rpcwallet={name}", "dumpwallet", dump_file)
        if r.returncode != 0:
            print("  could not dump, skipping.")
            node.cli("unloadwallet", name)
            return None

    node.cli("unloadwallet", name)
    print("  OK")
    return dump_file


def extract_addresses(dump_path):
    addrs = set()
    with open(dump_path, "r", errors="ignore") as f:
        for line in f:
            m = LINE_ADDR_RE.search(line)
            if m:
                addrs.add(m.group(1))
    return addrs


def get_balance_btc(address, retries=3):
    url = f"{API_BASE}/address/{address}"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            d = r.json()
            funded = d["chain_stats"]["funded_txo_sum"] + d["mempool_stats"]["funded_txo_sum"]
            spent = d["chain_stats"]["spent_txo_sum"] + d["mempool_stats"]["spent_txo_sum"]
            return (funded - spent) / 1e8
        elif r.status_code == 429:
            time.sleep(2 * (attempt + 1))
        else:
            return None
    return None


def main():
    ap = argparse.ArgumentParser(description="Scan a folder of wallet.dat files for real balances.")
    ap.add_argument("wallets_dir", help="Folder containing your .dat files")
    ap.add_argument("--out", default="report.csv", help="CSV report output path (default: report.csv)")
    ap.add_argument("--keep-dumps", action="store_true",
                     help="Keep extracted key/address dump files (contain PRIVATE KEYS - off by default)")
    ap.add_argument("--delay", type=float, default=0.3, help="Seconds between balance API calls (default 0.3)")
    args = ap.parse_args()

    check_binaries()

    wallet_files = sorted(glob.glob(os.path.join(args.wallets_dir, "*.dat")))
    if not wallet_files:
        print(f"No .dat files found in {args.wallets_dir}")
        sys.exit(1)

    print(f"Found {len(wallet_files)} wallet.dat file(s).")
    dump_dir = tempfile.mkdtemp(prefix="wallet_dumps_")
    node = Node()
    print("Starting local, throwaway Bitcoin Core instance (no blockchain sync)...")
    node.start()

    rows = []
    try:
        for wf in wallet_files:
            name = os.path.splitext(os.path.basename(wf))[0]
            print(f"\n== {name} ==")
            dump_file = dump_wallet(node, wf, dump_dir)
            if not dump_file:
                rows.append({"wallet": name, "addresses_found": 0, "addresses_checked": 0,
                             "funded_addresses": 0, "total_btc": 0.0, "status": "COULD NOT LOAD"})
                continue

            addrs = extract_addresses(dump_file)
            total_btc, funded, checked = 0.0, 0, 0
            for a in addrs:
                bal = get_balance_btc(a)
                time.sleep(args.delay)
                if bal is None:
                    continue
                checked += 1
                if bal > 0:
                    funded += 1
                    total_btc += bal

            status = "HAS BALANCE" if total_btc > 0 else "EMPTY"
            rows.append({"wallet": name, "addresses_found": len(addrs), "addresses_checked": checked,
                         "funded_addresses": funded, "total_btc": round(total_btc, 8), "status": status})
            print(f"  -> {total_btc:.8f} BTC across {funded} funded address(es): {status}")
    finally:
        node.stop()
        node.cleanup()
        if not args.keep_dumps:
            shutil.rmtree(dump_dir, ignore_errors=True)
        else:
            print(f"\nDump files (contain PRIVATE KEYS) kept at: {dump_dir}")

    if not rows:
        print("No results.")
        sys.exit(1)

    rows.sort(key=lambda r: r["total_btc"], reverse=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nReport written to: {args.out}")
    print("\n=== Wallets WITH balance ===")
    found = False
    for r in rows:
        if r["status"] == "HAS BALANCE":
            found = True
            print(f"  {r['wallet']}: {r['total_btc']} BTC")
    if not found:
        print("  (none found)")


if __name__ == "__main__":
    main()
