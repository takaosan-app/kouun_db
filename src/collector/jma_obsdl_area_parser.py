from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from collector.models import (
    ObsdlAreaRecord,
    ParsedObsdlAreaPage,
)

AREA_CODE_PATTERN = re.compile(r"\d{2}")


class ObsdlAreaParseError(ValueError):
    pass


def parse_obsdl_area_page(
    content: bytes,
) -> ParsedObsdlAreaPage:
    if not content:
        raise ObsdlAreaParseError(
            "Area page content is empty."
        )

    soup = BeautifulSoup(
        content,
        "html.parser",
        from_encoding="utf-8",
    )
    areas_by_code: dict[str, ObsdlAreaRecord] = {}

    for node in soup.select(
        "#prefectureTable div.prefecture"
    ):
        if not isinstance(node, Tag):
            continue

        area = _parse_area_node(node)
        existing = areas_by_code.get(area.area_code)

        if existing is not None and existing != area:
            raise ObsdlAreaParseError(
                "Conflicting entries for area "
                f"{area.area_code}."
            )

        areas_by_code[area.area_code] = area

    if not areas_by_code:
        raise ObsdlAreaParseError(
            "No observation areas were found."
        )

    names = {
        area.area_name
        for area in areas_by_code.values()
    }

    if len(names) != len(areas_by_code):
        raise ObsdlAreaParseError(
            "Observation area names are not unique."
        )

    return ParsedObsdlAreaPage(
        areas=tuple(
            sorted(
                areas_by_code.values(),
                key=lambda area: area.area_code,
            )
        )
    )


def _parse_area_node(
    node: Tag,
) -> ObsdlAreaRecord:
    input_node = node.find(
        "input",
        attrs={"name": "prid"},
        recursive=False,
    )

    if not isinstance(input_node, Tag):
        raise ObsdlAreaParseError(
            "Area code input was not found."
        )

    area_code = input_node.get("value")

    if (
        not isinstance(area_code, str)
        or not AREA_CODE_PATTERN.fullmatch(area_code)
    ):
        raise ObsdlAreaParseError(
            f"Invalid area code: {area_code!r}"
        )

    area_name = node.get_text(
        strip=True,
    )

    if not area_name:
        raise ObsdlAreaParseError(
            f"Area name is empty: {area_code}"
        )

    return ObsdlAreaRecord(
        area_code=area_code,
        area_name=area_name,
    )
