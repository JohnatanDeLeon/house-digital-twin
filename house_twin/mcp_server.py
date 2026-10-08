"""House MCP: expone la casa a Claude como operaciones semánticas de solo lectura.

Uso (stdio): python -m house_twin.mcp_server [ruta/a/existing.facts.json]
"""
import functools
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from house_twin.model import HouseModel, RoomNotFound

DEFAULT_FACTS = Path(__file__).resolve().parent.parent / 'data' / 'facts' / 'existing.facts.json'

INSTRUCTIONS = """Gemelo digital de una casa habitación. Las medidas están en metros y salen del plano
(levantamiento). Los datos que el plano no contiene se reportan como null y están en list_unknowns():
nunca los supongas. Las propuestas de remodelación no sustituyen la validación estructural ni normativa
de un arquitecto o ingeniero."""


def _explain_lookup_errors(tool):
    """Un espacio o muro inexistente es un error del pedido, no un fallo: el mensaje debe llegar a Claude."""
    @functools.wraps(tool)
    def wrapper(*args, **kwargs):
        try:
            return tool(*args, **kwargs)
        except RoomNotFound as exc:
            raise ToolError(str(exc)) from exc
        except KeyError as exc:
            raise ToolError(f'No existe {exc}') from exc
    return wrapper


def create_server(facts_path: Path = DEFAULT_FACTS) -> MCPServer:
    house = HouseModel.from_file(facts_path)
    server = MCPServer(name='house', instructions=INSTRUCTIONS)
    tool = lambda fn: server.tool()(_explain_lookup_errors(fn))

    @tool
    def house_summary() -> dict:
        """Resumen de la casa: terreno, área interior libre, conteos y procedencia de los datos."""
        return house.summary()

    @tool
    def list_rooms() -> list[dict]:
        """Lista todos los espacios (interiores y exterior) con id, nombre y área."""
        return house.list_rooms()

    @tool
    def get_room(room: str) -> dict:
        """Detalle de un espacio: polígono, área, nivel, puertas/ventanas y vecinos. `room` es id (S02) o nombre."""
        return house.get_room(room)

    @tool
    def get_adjacent_rooms(room: str) -> list[dict]:
        """Espacios vecinos de `room`: conectados por puerta, abiertos entre sí (exteriores), por ventana o solo por muro."""
        return house.adjacent_rooms(room)

    @tool
    def calculate_area(room: str) -> dict:
        """Área libre y perímetro de un espacio, en m² y m."""
        return house.area(room)

    @tool
    def get_wall(wall_id: str) -> dict:
        """Detalle de un muro (W01…): eje, largo, espesor, si es colindante, qué separa y qué vanos tiene."""
        return house.get_wall(wall_id)

    @tool
    def walk_path(start: str, end: str) -> dict:
        """Recorrido entre dos espacios por puertas y límites abiertos (cuántas puertas se cruzan y por dónde)."""
        return house.walk_path(start, end)

    @tool
    def list_unknowns() -> list[dict]:
        """Datos que el plano no contiene y que bloquean ciertos análisis (alturas, estructura, losa…)."""
        return house.unknowns()

    return server


if __name__ == '__main__':
    create_server(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FACTS).run()
