"""
Register range scanner for reverse-engineering heater registers.

Scans a range of registers from the device, applies multiple interpretation
parsers to each value, and outputs results in human-readable or YAML format.
"""

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp
import yaml

from ..kospel.backend import (
    HttpRegisterBackend,
    RegisterBackend,
    YamlRegisterBackend,
)
from ..registers.decoders import decode_scaled_pressure, decode_scaled_temp
from ..registers.utils import get_bit, int_to_reg_address, reg_address_to_int, reg_to_int

logger = logging.getLogger(__name__)

FORMAT_VERSION = "1"


@dataclass
class RegisterInterpretation:
    """Parsed interpretation of a single register value."""

    register: str
    hex: str
    raw_int: int
    scaled_temp: Optional[float]
    scaled_pressure: Optional[float]
    bits: dict[int, bool]


@dataclass
class RegisterScanResult:
    """Result of scanning a register range."""

    start_register: str
    count: int
    registers: list[RegisterInterpretation] = field(default_factory=list)


def _interpret_register(register: str, hex_val: str) -> RegisterInterpretation:
    """Apply parsers to a single register value."""
    raw_int = reg_to_int(hex_val)
    scaled_temp = decode_scaled_temp(hex_val)
    scaled_pressure = decode_scaled_pressure(hex_val)
    bits = {i: get_bit(raw_int, i) for i in range(16)}
    return RegisterInterpretation(
        register=register,
        hex=hex_val,
        raw_int=raw_int,
        scaled_temp=scaled_temp,
        scaled_pressure=scaled_pressure,
        bits=bits,
    )


async def scan_register_range(
    backend: RegisterBackend,
    start_register: str,
    count: int,
) -> RegisterScanResult:
    """
    Scan a range of registers and apply interpretation parsers.

    Args:
        backend: RegisterBackend (HttpRegisterBackend or YamlRegisterBackend).
        start_register: Starting register address (e.g. "0b00").
        count: Number of registers to read.

    Returns:
        RegisterScanResult with raw values and parsed interpretations.
    """
    raw_registers = await backend.read_registers(start_register, count)
    interpretations: list[RegisterInterpretation] = []
    start_int = reg_address_to_int(start_register)
    prefix = start_register[:2]

    for i in range(count):
        reg_int = start_int + i
        reg_str = int_to_reg_address(prefix, reg_int)
        hex_val = raw_registers.get(reg_str, "0000")
        interpretations.append(_interpret_register(reg_str, hex_val))

    return RegisterScanResult(
        start_register=start_register,
        count=count,
        registers=interpretations,
    )


def _is_empty_register(reg: RegisterInterpretation) -> bool:
    """Register is empty when hex is 0000."""
    return reg.hex == "0000"


def format_scan_result(
    result: RegisterScanResult,
    *,
    include_empty: bool = False,
) -> str:
    """
    Format scan result as human-readable table.

    Args:
        result: Scan result from scan_register_range.
        include_empty: If False (default), omit registers with hex 0000.

    Returns:
        Formatted string for console output.
    """
    lines: list[str] = []
    end_int = reg_address_to_int(result.start_register) + result.count - 1
    prefix = result.start_register[:2]
    end_register = int_to_reg_address(prefix, end_int)

    if include_empty:
        displayed = result.registers
    else:
        displayed = [r for r in result.registers if not _is_empty_register(r)]

    if len(displayed) < result.count and not include_empty:
        lines.append(
            f"Register Scan: {result.start_register} - {end_register} "
            f"({len(displayed)} of {result.count} registers, empty hidden)"
        )
    else:
        lines.append(
            f"Register Scan: {result.start_register} - {end_register} "
            f"({len(displayed)} registers)"
        )
    lines.append("")

    if not displayed:
        lines.append("(no registers)")
        return "\n".join(lines)

    header = f"{'Register':<8} {'Hex':<6} {'Int':>7} {'°C':>6} {'bar':>6}  Bits"
    separator = "-" * 8 + " " + "-" * 6 + " " + "-" * 7 + " " + "-" * 6 + " " + "-" * 6 + "  " + "-" * 19
    lines.append(header)
    lines.append(separator)

    for reg in displayed:
        temp_str = f"{reg.scaled_temp:.1f}" if reg.scaled_temp is not None else "—"
        press_str = (
            f"{reg.scaled_pressure:.2f}" if reg.scaled_pressure is not None else "—"
        )
        # ● = set, · = clear (visually scannable in large tables)
        bits_chars = "".join(
            "\u25CF" if reg.bits[i] else "\u00B7" for i in range(15, -1, -1)
        )
        bits_str = " ".join(bits_chars[i : i + 4] for i in range(0, 16, 4))
        row = f"{reg.register:<8} {reg.hex:<6} {reg.raw_int:>7} {temp_str:>6} {press_str:>6}  {bits_str}"
        lines.append(row)

    return "\n".join(lines)


def _result_to_dict(
    result: RegisterScanResult,
    *,
    include_empty: bool = False,
) -> dict:
    """Convert RegisterScanResult to a dict suitable for YAML serialization."""
    if include_empty:
        displayed = result.registers
    else:
        displayed = [r for r in result.registers if not _is_empty_register(r)]

    registers_dict: dict[str, dict] = {}
    for reg in displayed:
        reg_data: dict = {
            "hex": reg.hex,
            "raw_int": reg.raw_int,
            "scaled_temp": reg.scaled_temp,
            "scaled_pressure": reg.scaled_pressure,
            "bits": dict(sorted(reg.bits.items())),
        }
        registers_dict[reg.register] = reg_data

    scan_meta: dict = {
        "start_register": result.start_register,
        "count": result.count,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if not include_empty:
        scan_meta["hide_empty"] = True
        scan_meta["registers_shown"] = len(displayed)

    return {
        "format_version": FORMAT_VERSION,
        "scan": scan_meta,
        "registers": registers_dict,
    }


def serialize_scan_result(
    result: RegisterScanResult,
    *,
    include_empty: bool = False,
) -> str:
    """
    Serialize scan result to YAML string.

    Output is human-readable and machine-parseable for future diff tools.

    Args:
        result: Scan result from scan_register_range.
        include_empty: If False (default), omit registers with hex 0000.

    Returns:
        YAML string.
    """
    data = _result_to_dict(result, include_empty=include_empty)
    return yaml.safe_dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def write_scan_result(
    path: Path,
    result: RegisterScanResult,
    *,
    include_empty: bool = False,
) -> None:
    """
    Write scan result to a YAML file.

    Args:
        path: Output file path.
        result: Scan result from scan_register_range.
        include_empty: If False (default), omit registers with hex 0000.
    """
    content = serialize_scan_result(result, include_empty=include_empty)
    path.write_text(content, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Scan a range of heater registers for reverse-engineering."
    )
    parser.add_argument(
        "--url",
        type=str,
        help="HTTP mode: base URL (e.g. http://192.168.1.1/api/dev/65)",
    )
    parser.add_argument(
        "--yaml",
        dest="yaml_path",
        type=str,
        metavar="PATH",
        help="YAML mode: path to state file (for offline/dev)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        metavar="FILE",
        help="Write results to file (YAML format)",
    )
    parser.add_argument(
        "--show-empty",
        action="store_true",
        help="Include registers with hex 0000 (default: hide them)",
    )
    parser.add_argument(
        "start_register",
        nargs="?",
        default="0b00",
        help="Starting register address (default: 0b00)",
    )
    parser.add_argument(
        "count",
        nargs="?",
        type=int,
        default=256,
        help="Number of registers to read (default: 256)",
    )
    return parser.parse_args()


async def _main_async() -> int:
    """Async main logic. Returns exit code."""
    args = _parse_args()

    if args.url and args.yaml_path:
        print("Error: Use either --url or --yaml, not both.", file=sys.stderr)
        return 1
    if not args.url and not args.yaml_path:
        print(
            "Error: Specify --url for HTTP mode or --yaml for YAML (offline) mode.",
            file=sys.stderr,
        )
        return 1

    if args.yaml_path:
        backend: RegisterBackend = YamlRegisterBackend(args.yaml_path)
        should_close = False
    else:
        session = aiohttp.ClientSession()
        backend = HttpRegisterBackend(session, args.url)
        should_close = True

    try:
        result = await scan_register_range(
            backend, args.start_register, args.count
        )

        include_empty = args.show_empty
        if args.output:
            out_path = Path(args.output)
            write_scan_result(out_path, result, include_empty=include_empty)
            print(f"Wrote scan to {out_path}")
        else:
            print(format_scan_result(result, include_empty=include_empty))
    finally:
        if should_close and hasattr(backend, "aclose"):
            await backend.aclose()

    return 0


def main() -> None:
    """CLI entry point."""
    exit_code = asyncio.run(_main_async())
    raise SystemExit(exit_code)
