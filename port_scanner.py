
import argparse
import csv
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

results = []
results_lock = threading.Lock()

def grab_banner(sock: socket.socket) -> str:
    try:
        data = sock.recv(1024)
        if data:
            return data.decode(errors="ignore").strip()
    except:
        pass
    try:
        sock.sendall(b"\r\n")
        data = sock.recv(1024)
        if data:
            return data.decode(errors="ignore").strip()
    except:
        pass
    return "No banner"
def scan_port(host: str, port: int, timeout: float = 1.0, show_closed: bool = False):
    status = "CLOSED"
    banner = ""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        status = "OPEN"
        banner = grab_banner(s)
    except:
        pass
    finally:
        s.close()

    if status == "OPEN" or show_closed:
        with results_lock:
            results.append({"port": port, "status": status, "banner": banner})
        if status == "OPEN":
            print(f"[+] Port {port:<5} OPEN   --> {banner}")
        else:
            print(f"[-] Port {port:<5} CLOSED")

def run_scanner(host: str, start_port: int, end_port: int, threads: int, timeout: float, show_closed: bool):
    total = end_port - start_port + 1
    print(f"Target     : {host}")
    print(f"Port range : {start_port}-{end_port} ({total} ports)")
    print(f"Threads    : {threads}")
    print(f"Timeout    : {timeout}s\n")

    t0 = time.time()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(scan_port, host, p, timeout, show_closed) for p in range(start_port, end_port + 1)]
        for _ in as_completed(futures):
            pass

    elapsed = time.time() - t0
    open_count = sum(1 for r in results if r["status"] == "OPEN")
    print(f"\n✅ Done in {elapsed:.2f}s. Open ports: {open_count}/{total}.")

def save_results(fmt: str, output_prefix: str):
    if fmt in ("csv", "both"):
        csv_path = f"{output_prefix}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["port", "status", "banner"])
            writer.writeheader()
            for row in sorted(results, key=lambda r: r["port"]):
                writer.writerow(row)
        print(f"📂 Saved CSV : {csv_path}")

    if fmt in ("json", "both"):
        json_path = f"{output_prefix}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sorted(results, key=lambda r: r["port"]), f, indent=2)
        print(f"📂 Saved JSON: {json_path}")

def parse_args():
    p = argparse.ArgumentParser(description="Fast multithreaded TCP port scanner with banner grabbing.")
    p.add_argument("host", help="Target IP or hostname (must have permission to scan)")
    p.add_argument("--start", type=int, default=1, help="Start port (default: 1)")
    p.add_argument("--end", type=int, default=1024, help="End port (default: 1024)")
    p.add_argument("-t", "--threads", type=int, default=200, help="Number of threads (default: 200)")
    p.add_argument("--timeout", type=float, default=1.0, help="Timeout per port in seconds (default: 1.0)")
    p.add_argument("-f", "--format", choices=["csv", "json", "both"], default="csv", help="Output format (default: csv)")
    p.add_argument("-o", "--output", default="scan_results", help="Output filename prefix (default: scan_results)")
    p.add_argument("--show-closed", action="store_true", help="Include closed ports in results")
    return p.parse_args()

def main():
    args = parse_args()

    if args.start < 1 or args.end > 65535 or args.start > args.end:
        raise SystemExit("❌ Invalid port range. Must be between 1–65535.")

    run_scanner(args.host, args.start, args.end, args.threads, args.timeout, args.show_closed)
    save_results(args.format, args.output)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Scan interrupted by user.")
