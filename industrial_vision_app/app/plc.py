from __future__ import annotations


class PlcClient:
    def __init__(self, enabled: bool, host: str, port: int, ok_coil: int, ng_coil: int):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.ok_coil = ok_coil
        self.ng_coil = ng_coil
        self.client = None

    def connect(self) -> None:
        if not self.enabled:
            return
        from pymodbus.client import ModbusTcpClient

        self.client = ModbusTcpClient(self.host, port=self.port)
        if not self.client.connect():
            raise RuntimeError(f"Cannot connect PLC {self.host}:{self.port}")

    def publish_result(self, is_ok: bool) -> None:
        if not self.enabled or self.client is None:
            return
        self.client.write_coil(self.ok_coil, bool(is_ok))
        self.client.write_coil(self.ng_coil, not bool(is_ok))

    def close(self) -> None:
        if self.client:
            self.client.close()
