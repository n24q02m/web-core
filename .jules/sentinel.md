## 2026-04-07 - [PID Alive Check]
**Vulnerability:** Zombie processes on Linux can be misidentified as "alive" because `os.kill(pid, 0)` succeeds for them.
**Learning:** Checking `/proc/{pid}/status` for the 'Z' state is necessary to accurately determine if a process is truly functional.
**Prevention:** Always verify the process state on Linux using `/proc` when PID reuse or zombie states could impact system reliability.
