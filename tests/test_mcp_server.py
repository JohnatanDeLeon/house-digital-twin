import asyncio
import json

from house_twin.mcp_server import create_server

EXPECTED_TOOLS = {'house_summary', 'list_rooms', 'get_room', 'get_adjacent_rooms', 'calculate_area',
                  'get_wall', 'walk_path', 'list_unknowns'}


def test_server_exposes_semantic_tools():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    assert {t.name for t in tools} == EXPECTED_TOOLS
