# Kospel HTTP API

This module implements HTTP communication with the Kospel C.MI heater device.

## API Endpoints

**Base URL**: `http://<HEATER_IP>/api/dev/<DEVICE_ID>`

### Read Register

Read a single register from the heater.

- **Endpoint**: `GET /api/dev/<DEVICE_ID>/<register>/<count>`
- **Example**: `GET /api/dev/65/0b55/1`
- **Response**: `{"regs": {"0b55": "d700"}, "sn": "...", "time": "..."}`

### Write Register

Write a register value to the heater.

- **Endpoint**: `POST /api/dev/<DEVICE_ID>/<register>`
- **Body**: Hex string (e.g., `"d700"`)
- **Content-Type**: `application/json`
- **Response**: `{"status": "0"}` on success (0 = success)

### Read Multiple Registers

Read multiple registers in a single request.

- **Endpoint**: `GET /api/dev/<DEVICE_ID>/<start_register>/<count>`
- **Example**: `GET /api/dev/65/0b00/256` (reads 256 registers starting from 0b00)
- **Response**: `{"regs": {"0b00": "...", "0b01": "...", ...}}`

## Request/Response Format

- All register values are hex strings (4 characters)
- Values use little-endian byte order
- JSON encoding for requests and responses

## Error Handling

**Network Errors**:
- Timeout: 5 seconds (configurable)
- Connection errors: Returns `None` or empty dict
- HTTP errors: Logged and returns `None`/`False`

## Implementation

The HTTP API is implemented in:
- `api.py` - Low-level HTTP functions (`read_register`, `read_registers`, `write_register`)
- `backend.py` - `HttpRegisterBackend` class that implements the `RegisterBackend` protocol

## References

This library was reverse-engineered from JavaScript code used in the heater's web interface. Key findings:

- Register encoding uses little-endian byte order
- Flag bits are used for boolean settings within registers
- Temperature and pressure values are scaled for precision
- Read-Modify-Write pattern is required for setting flag bits

For details on register encoding and decoding, see [`../registers/README.md`](../registers/README.md).
