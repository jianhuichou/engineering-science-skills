---
name: embedded-systems
description: >
  Embedded systems workflows: firmware analysis, register map parsing,
  timing and latency analysis, communication protocol decoding (UART, SPI,
  I2C, CAN), interrupt latency budgeting, and code-size profiling. Load
  this skill for microcontroller firmware review, hardware bring-up, RTOS
  task analysis, or embedded communication protocol debugging tasks.
license: Apache-2.0
category: electrical-engineering
---

# Embedded Systems

## Register map parsing

When a datasheet-derived register map is provided (as CSV, JSON, or SVD file),
parse it to generate header files or access helpers.

```python
import json, pandas as pd

def parse_register_map_csv(csv_path):
    """
    Parse a register map CSV with columns:
    offset_hex, name, width_bits, access, reset_hex, description
    Returns a DataFrame.
    """
    df = pd.read_csv(csv_path)
    df["offset"] = df["offset_hex"].apply(lambda x: int(x, 16))
    df["reset"]  = df["reset_hex"].apply(lambda x: int(x, 16) if pd.notna(x) else None)
    return df.sort_values("offset")

def generate_c_header(reg_df, peripheral="PERIPH", base_addr=0x40000000):
    """Generate a C register map header from parsed DataFrame."""
    lines = [f"/* Auto-generated register map for {peripheral} */",
             f"#define {peripheral}_BASE  0x{base_addr:08X}UL\n"]
    for _, row in reg_df.iterrows():
        name = row["name"].upper()
        offset = row["offset"]
        lines.append(f"#define {peripheral}_{name}_OFFSET  0x{offset:04X}UL")
        lines.append(f"#define {peripheral}_{name}  (*(volatile uint32_t*)({peripheral}_BASE + {peripheral}_{name}_OFFSET))")
        if pd.notna(row.get("description")):
            lines.append(f"/* {row['description']} */")
        lines.append("")
    return "\n".join(lines)
```

## Bit-field manipulation

```python
def extract_field(reg_val, bit_high, bit_low):
    """Extract a bit field from a register value."""
    mask = (1 << (bit_high - bit_low + 1)) - 1
    return (reg_val >> bit_low) & mask

def set_field(reg_val, bit_high, bit_low, value):
    """Set a bit field in a register value, preserving other bits."""
    mask = ((1 << (bit_high - bit_low + 1)) - 1) << bit_low
    return (reg_val & ~mask) | ((value << bit_low) & mask)

# Example: set bits [5:3] to 0b101 in a 32-bit register
reg = 0xA5A5A5A5
new_reg = set_field(reg, bit_high=5, bit_low=3, value=0b101)
print(f"0x{new_reg:08X}")
```

## UART frame decoding

```python
def decode_uart_bytes(raw_bytes, baud=115200, data_bits=8,
                       parity="none", stop_bits=1, encoding="utf-8"):
    """
    Validate and decode a UART byte stream.
    raw_bytes : bytes object
    Returns (decoded_string, error_info).
    """
    errors = []
    if parity != "none":
        # Check parity bit (illustrative — real analysis needs bit-level data)
        for i, b in enumerate(raw_bytes):
            bit_count = bin(b & 0xFF).count("1")
            expected = 0 if parity == "even" else 1
            if bit_count % 2 != expected:
                errors.append(f"Parity error at byte {i}: 0x{b:02X}")
    try:
        decoded = raw_bytes.decode(encoding, errors="replace")
    except Exception as e:
        decoded = ""
        errors.append(str(e))
    return decoded, errors
```

## SPI / I2C transaction analysis

```python
def parse_spi_transaction(cs_active_low, clk, mosi, miso, cpol=0, cpha=0):
    """
    Parse a SPI transaction from logic-level arrays.
    All arrays are 1-D numpy arrays of 0/1 sampled at the same rate.
    Returns (mosi_bytes, miso_bytes).
    """
    import numpy as np
    # Sample on rising/falling edge based on CPOL/CPHA
    sample_edge = "rising" if cpha == 0 else "falling"
    if cpol == 1:
        sample_edge = "falling" if cpha == 0 else "rising"

    if sample_edge == "rising":
        edges = np.where(np.diff(clk) == 1)[0] + 1
    else:
        edges = np.where(np.diff(clk) == -1)[0] + 1

    # Only sample when CS is asserted
    active = np.where(cs_active_low == 0)[0]
    edges = edges[np.isin(edges, active)]

    mosi_bits = mosi[edges]
    miso_bits = miso[edges]

    def bits_to_bytes(bits):
        out = []
        for i in range(0, len(bits) - 7, 8):
            byte_val = 0
            for j in range(8):
                byte_val = (byte_val << 1) | int(bits[i + j])
            out.append(byte_val)
        return bytes(out)

    return bits_to_bytes(mosi_bits), bits_to_bytes(miso_bits)
```

## Interrupt latency and timing budget

```python
def interrupt_latency_budget(f_cpu_hz, pipeline_stages, irq_entry_cycles,
                              context_save_cycles, isr_body_cycles,
                              context_restore_cycles):
    """
    Estimate total ISR latency from interrupt assertion to first ISR instruction
    and full return.
    Returns (latency_assertion_to_first_instruction_us,
             total_isr_duration_us).
    """
    cycle_time_ns = 1e9 / f_cpu_hz
    entry_cycles = pipeline_stages + irq_entry_cycles + context_save_cycles
    total_cycles = entry_cycles + isr_body_cycles + context_restore_cycles
    return (entry_cycles * cycle_time_ns / 1e3,   # us
            total_cycles * cycle_time_ns / 1e3)

# Example: ARM Cortex-M4, 168 MHz
lat, total = interrupt_latency_budget(
    f_cpu_hz=168e6, pipeline_stages=3, irq_entry_cycles=12,
    context_save_cycles=12, isr_body_cycles=50, context_restore_cycles=10
)
print(f"Latency to ISR entry: {lat:.3f} us,  Total ISR: {total:.3f} us")
```

## RTOS task analysis

```python
def rtos_schedulability_rm(tasks):
    """
    Rate-Monotonic schedulability test (Liu & Layland bound).
    tasks : list of (period_ms, wcet_ms) tuples
    Returns (utilization, schedulable).
    """
    import numpy as np
    n = len(tasks)
    U = sum(C/T for T, C in tasks)
    U_bound = n * (2**(1/n) - 1)   # Liu-Layland bound
    return U, U <= U_bound

tasks = [(10, 2), (20, 4), (50, 8)]   # (period, WCET) in ms
U, ok = rtos_schedulability_rm(tasks)
print(f"CPU utilization: {U*100:.1f}%  ({'schedulable' if ok else 'may NOT be schedulable'} by RM)")
```

## Code size and memory footprint analysis

```python
import subprocess, re

def parse_map_file(map_path):
    """
    Parse a GCC linker .map file to extract section sizes.
    Returns dict {section_name: size_bytes}.
    """
    text = open(map_path).read()
    pattern = re.compile(r"^\.(text|data|bss|rodata)\s+0x[0-9a-f]+\s+(0x[0-9a-f]+)", re.M)
    sections = {}
    for m in pattern.finditer(text):
        sections[m.group(1)] = int(m.group(2), 16)
    return sections

def arm_size(elf_path):
    """Run arm-none-eabi-size and return Flash/RAM usage."""
    result = subprocess.run(["arm-none-eabi-size", elf_path],
                             capture_output=True, text=True)
    # Parse output: text + data = Flash; data + bss = RAM
    lines = result.stdout.strip().split("\n")
    if len(lines) >= 2:
        parts = lines[1].split()
        text, data, bss = int(parts[0]), int(parts[1]), int(parts[2])
        return {"flash_bytes": text + data, "ram_bytes": data + bss}
    return {}
```

## Reporting

For every embedded systems analysis, report:
1. Target MCU/SoC: architecture, clock frequency, flash/RAM sizes.
2. Register map: peripheral name, base address, relevant register offsets.
3. Communication: protocol, baud rate / clock frequency, transaction count, error rate.
4. Interrupt: latency breakdown (pipeline + entry + context save + ISR body), deadline.
5. RTOS: task list with periods, WCET, utilization, schedulability result.
6. Memory footprint: flash used, RAM used, headroom.
7. Toolchain version (compiler, linker, SDK) for reproducibility.
