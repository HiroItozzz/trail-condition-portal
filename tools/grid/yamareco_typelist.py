import json
from pathlib import Path
from pprint import pprint

import httpx


def get_typelist():
    r = httpx.get("https://api.yamareco.com/api/v1/getTypelist")
    return r.json()


if __name__ == "__main__":
    data: dict = get_typelist()

    path = Path.cwd() / "tools/grid/samples/typelist.json"
    data = sorted(data["typelist"], key=lambda x: f"{int(x['type_id']):02d}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    data2 = {}
    for _type in data:
        data2[_type["type_id"]] = _type["name"]

    Path(path.parent / "typelist2.json").write_text(json.dumps(data2, ensure_ascii=False, indent=2))
    pprint(data)
