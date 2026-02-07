"""
Dedicated module for HTTP API calls to the Kospel heater.

This module contains only HTTP logic. Register backend abstraction (HTTP vs YAML)
lives in kospel/backend.py; the controller uses a RegisterBackend, not this API directly.
"""

import logging
import aiohttp
from typing import Optional, Dict

from ..registers.utils import reg_to_int

logger = logging.getLogger(__name__)


async def read_register(
    session: aiohttp.ClientSession,
    api_base_url: str,
    register: str,
) -> Optional[str]:
    """
    Read a single register from the heater.

    Args:
        session: aiohttp ClientSession
        api_base_url: Base URL for the heater API (e.g., "http://192.168.1.1/api/dev/65")
        register: Register address (e.g., "0b55")

    Returns:
        Hex string value of the register, or None if read failed
    """
    url = f"{api_base_url}/{register}/1"
    logger.debug(f"Reading register {register} from {url}")
    try:
        async with session.get(url, timeout=5) as response:
            response.raise_for_status()
            data = await response.json()
            regs = data.get("regs", {})
            value = regs.get(register)
            if value:
                int_val = reg_to_int(value)
                logger.debug(f"Register {register}: {value} ({int_val})")
            else:
                logger.warning(f"Register {register} not found in response")
            return value
    except (aiohttp.ClientError, aiohttp.ClientResponseError) as e:
        logger.error(f"Error reading register {register}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error reading register {register}: {e}", exc_info=True
        )
        return None


async def read_registers(
    session: aiohttp.ClientSession,
    api_base_url: str,
    start_register: str,
    count: int,
) -> Dict[str, str]:
    """
    Read multiple registers from the heater in a single batch call.

    Args:
        session: aiohttp ClientSession
        api_base_url: Base URL for the heater API
        start_register: Starting register address (e.g., "0b00")
        count: Number of registers to read

    Returns:
        Dictionary mapping register addresses to hex values
    """
    url = f"{api_base_url}/{start_register}/{count}"
    logger.debug(f"Reading {count} registers starting from {start_register} from {url}")
    try:
        async with session.get(url, timeout=5) as response:
            response.raise_for_status()
            data = await response.json()
            regs = data.get("regs", {})
            logger.debug(f"Read {len(regs)} registers from {start_register}")
            return regs
    except (aiohttp.ClientError, aiohttp.ClientResponseError) as e:
        logger.error(f"Error reading registers from {start_register}: {e}")
        return {}
    except Exception as e:
        logger.error(
            f"Unexpected error reading registers from {start_register}: {e}",
            exc_info=True,
        )
        return {}


async def write_register(
    session: aiohttp.ClientSession,
    api_base_url: str,
    register: str,
    hex_value: str,
) -> bool:
    """
    Write a value to a single register.

    Args:
        session: aiohttp ClientSession
        api_base_url: Base URL for the heater API
        register: Register address (e.g., "0b55")
        hex_value: Hex string value to write (e.g., "d700")

    Returns:
        True if write succeeded, False otherwise
    """
    url = f"{api_base_url}/{register}"
    int_val = reg_to_int(hex_value)
    logger.debug(f"Writing register {register}: {hex_value} ({int_val}) to {url}")
    try:
        async with session.post(url, json=hex_value, timeout=5) as response:
            response.raise_for_status()
            data = await response.json()
            success = data.get("status") == "0"
            if success:
                logger.debug(f"Successfully wrote register {register}")
            else:
                logger.warning(
                    f"Register {register} write returned non-zero status: {data.get('status')}"
                )
            return success
    except (aiohttp.ClientError, aiohttp.ClientResponseError) as e:
        logger.error(f"Error writing register {register}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error writing register {register}: {e}", exc_info=True
        )
        return False
