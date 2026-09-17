#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path
import random
from datetime import date

# ============================================================
# ŚCIEŻKI
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

DATA_DIR = PROJECT_DIR / "data"
LINES_FILE = DATA_DIR / "lines.json"

STOPS_DIR = DATA_DIR / "stops"
STOPS_INDEX_FILE = STOPS_DIR / "index.json"

STOPS_SOURCE_FILE = SCRIPT_DIR / "stops.txt"
STOPS_JSON_FILE = DATA_DIR / "stops.json"

INPUT_FILES = sorted(
    path
    for path in SCRIPT_DIR.glob("*.txt")
    if path.name.lower() != "stops.txt"
)


# ============================================================
# POMOCNICZE
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return value.strip()


def split_tsv(line):

    return [
        clean_text(cell)
        for cell in line.rstrip("\r\n").split("\t")
    ]

def is_empty_row(row):

    return not any(cell.strip() for cell in row)


def ensure_columns(row, count):

    while len(row) < count:
        row.append("")

    return row


# ============================================================
# OZNACZENIA
# ============================================================

def parse_flags(value):

    value = value.upper().strip()

    flags = {
        "request": False,
        "terminus": False,
        "alightingOnly": False
    }

    if not value:
        return flags

    parts = re.split(
        r"[\s,;/]+",
        value
    )

    for part in parts:

        if part in ("NŻ", "NZ"):
            flags["request"] = True

        elif part == "K":
            flags["terminus"] = True

        elif part in ("WYS", "WYS."):
            flags["alightingOnly"] = True

    return flags


# ============================================================
# KIERUNEK
# ============================================================

def parse_direction(cell):

    if not cell:
        return None

    match = re.search(
        r"Kierunek:\s*(.*?)\s*$",
        cell,
        re.IGNORECASE
    )

    if not match:
        return None

    return {
        "name": match.group(1).strip()
    }

# ============================================================
# NORMALIZACJA NAZW
# ============================================================

def normalize_name(value):

    value = value.upper().strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value

def load_stops_file():

    if not STOPS_SOURCE_FILE.exists():
        print(
            f"UWAGA: nie znaleziono pliku {STOPS_SOURCE_FILE}"
        )
        return {}

    stops = {}

    try:

        text = STOPS_SOURCE_FILE.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        print(
            "BŁĄD: stops.txt musi być zapisany jako UTF-8."
        )

        return {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split("\t", 1)

        if len(parts) != 2:
            continue

        name = normalize_name(parts[0])
        district = clean_text(parts[1])

        if not name:
            continue

        stops[name] = district

    return stops

# ============================================================
# ZESPOŁY PRZYSTANKOWE
# ============================================================

def load_stop_index():

    STOPS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not STOPS_INDEX_FILE.exists():

        return {
            "nextId": 1,
            "groups": []
        }

    try:

        data = json.loads(
            STOPS_INDEX_FILE.read_text(
                encoding="utf-8"
            )
        )

        if "groups" not in data:
            data["groups"] = []

        if "nextId" not in data:
            data["nextId"] = 1

        return data

    except Exception:

        print(
            "UWAGA: stops/index.json jest nieprawidłowy."
        )

        return {
            "nextId": 1,
            "groups": []
        }


def save_stop_index(index):

    STOPS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    STOPS_INDEX_FILE.write_text(
        json.dumps(
            index,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )


def make_unique_group_id(index):

    used = {
        str(group.get("id", ""))
        for group in index["groups"]
    }

    next_id = int(
        index.get(
            "nextId",
            1
        )
    )

    while True:

        group_id = f"{next_id:04d}"

        next_id += 1

        if group_id not in used:
            index["nextId"] = next_id
            return group_id

def find_group(
    index,
    name=None,
    street=None,
    number=None
):

    normalized_name = (
        normalize_name(name)
        if name
        else ""
    )

    normalized_street = (
        normalize_name(street)
        if street
        else ""
    )

    # --------------------------------------------------------
    # ZESPÓŁ NAZWANY
    #
    # ID zespołu zależy WYŁĄCZNIE od nazwy.
    #
    # DW.CENTRALNY 01
    # DW.CENTRALNY 02
    # DW.CENTRALNY 07
    #
    # -> jeden wspólny groupId
    # --------------------------------------------------------

    if normalized_name:

        for group in index["groups"]:

            if (
                normalize_name(
                    group.get("name", "")
                ) == normalized_name
            ):
                return group

        return None

    # --------------------------------------------------------
    # ZESPÓŁ BEZ NAZWY
    #
    # Dla nienazwanych zespołów nie mamy nazwy,
    # więc identyfikujemy je po ulicy.
    #
    # Numer przystanku NIE jest częścią identyfikatora
    # zespołu.
    # --------------------------------------------------------

    for group in index["groups"]:

        if (
            not group.get("name")
            and normalize_name(
                group.get("streetKey", "")
            ) == normalized_street
        ):
            return group

    return None


def create_group(
    index,
    name=None,
    street=None,
    number=None
):

    group_id = make_unique_group_id(
        index
    )

    group = {
        "id": group_id,
        "name": name or "",
        "stops": {}
    }

    # --------------------------------------------------------
    # Dla nienazwanego zespołu zapamiętujemy ulicę.
    #
    # Numer NIE jest zapisywany jako numberKey,
    # ponieważ numer należy do konkretnego przystanku
    # wewnątrz zespołu.
    # --------------------------------------------------------

    if not name:

        group["streetKey"] = (
            street or ""
        )

    index["groups"].append(
        group
    )

    return group

def ensure_stop_in_group(
    group,
    number,
    street,
    line_number,
    flags
):

    number = str(number or "")

    if not number:
        return

    if "stops" not in group:
        group["stops"] = {}

    if number not in group["stops"]:

        group["stops"][number] = {
            "streets": [],
            "regular": [],
            "request": [],
            "terminus": [],
            "alightingOnly": []
        }

    stop = group["stops"][number]

    # --------------------------------------------------------
    # ULICA
    # --------------------------------------------------------

    if street:

        if street not in stop["streets"]:

            stop["streets"].append(
                street
            )

    # --------------------------------------------------------
    # LINIA
    #
    # Linie z "E" na początku są zawsze umieszczane pierwsze.
    # --------------------------------------------------------

    line_number = str(line_number)

    if flags["request"]:

        if line_number not in stop["request"]:
            stop["request"].append(line_number)

        stop["request"].sort(
            key=lambda x: (not x.upper().startswith("E"), x)
        )

    elif flags["terminus"]:

        if line_number not in stop["terminus"]:
            stop["terminus"].append(line_number)

        stop["terminus"].sort(
            key=lambda x: (not x.upper().startswith("E"), x)
        )

    elif flags["alightingOnly"]:

        if line_number not in stop["alightingOnly"]:
            stop["alightingOnly"].append(line_number)

        stop["alightingOnly"].sort(
            key=lambda x: (not x.upper().startswith("E"), x)
        )

    else:

        if line_number not in stop["regular"]:
            stop["regular"].append(line_number)

        stop["regular"].sort(
            key=lambda x: (not x.upper().startswith("E"), x)
        )


def get_or_create_group(
    index,
    name,
    street,
    number
):

    group = find_group(
        index,
        name=name,
        street=street,
        number=number
    )

    if group:
        return group

    return create_group(
        index,
        name=name,
        street=street,
        number=number
    )

def generate_travel_time():
    return random.choices(
        [1, 2],
        weights=[80, 20],
        k=1
    )[0]

# ============================================================
# PARSOWANIE JEDNEJ STRONY
# ============================================================

def parse_side(
    rows,
    line_number,
    stop_index
):

    stops = []

    previous_street = ""
    elapsed_time = 0

    for row in rows:

        ensure_columns(
            row,
            4
        )

        street = row[0]
        name = row[1]
        number = row[2]
        flag = row[3]

        # ----------------------------------------------------
        # Nagłówki
        # ----------------------------------------------------

        if (
            street.lower() == "ulica"
            or name.lower() == "przystanek"
            or number.lower() == "nr"
        ):
            continue

        # ----------------------------------------------------
        # Pusty wiersz
        # ----------------------------------------------------

        if not any(row):
            continue

        # ----------------------------------------------------
        # ULICA
        # ----------------------------------------------------

        if street:
            previous_street = street

        else:
            street = previous_street

        flags = parse_flags(flag)

        # ----------------------------------------------------
        # WIERSZ BEZ PRZYSTANKU
        #
        # Ulica zostaje zapisana w JSON-ie.
        # ----------------------------------------------------

        if not name:

            stops.append({
                "street": street
            })

            continue

        # ----------------------------------------------------
        # PRZYSTANEK
        # ----------------------------------------------------

        item = {
            "street": street,
            "name": name
        }

        item["travelTime"] = elapsed_time

        elapsed_time += generate_travel_time()

        if number:
            item["number"] = number

        if flags["request"]:
            item["request"] = True

        if flags["terminus"]:
            item["terminus"] = True

        if flags["alightingOnly"]:
            item["alightingOnly"] = True

        # ----------------------------------------------------
        # ZESPÓŁ PRZYSTANKOWY
        # ----------------------------------------------------

        group = get_or_create_group(
            stop_index,
            name=name,
            street=street,
            number=number
        )

        item["groupId"] = group["id"]

        ensure_stop_in_group(
            group,
            number,
            street,
            line_number,
            flags
        )

        stops.append(
            item
        )

    return stops

def detect_line_info(first_row):

    line_number = ""

    if first_row:
        # Zachowujemy pełne oznaczenie linii, np.:
        # N63 -> N63
        # E8  -> E8
        # 63  -> 63
        # Nie wycinamy samej części numerycznej.
        value = clean_text(first_row[0])

        match = re.search(
            r"(?i)\\b[A-ZĄĆĘŁŃÓŚŹŻ]*\\d+[A-ZĄĆĘŁŃÓŚŹŻ]*\\b",
            value
        )

        if match:
            line_number = match.group(0)
        elif value:
            # Awaryjnie zachowujemy cały pierwszy nagłówek,
            # zamiast usuwać litery.
            line_number = value

    description = ""

    if len(first_row) >= 2:
        description = first_row[1]

    description_lower = description.lower()

    if "linia metra" in description_lower:
        line_type = "metro"

    elif "linia tramwajowa" in description_lower:
        line_type = "tram"

    elif "linia kolejowa" in description_lower:
        line_type = "train"

    else:
        line_type = "bus"

    return (
        line_number,
        line_type,
        description
    )

# ============================================================
# PARSOWANIE CAŁEGO PLIKU
# ============================================================

def generate_timetable(frequency):
    """
    Generuje fikcyjny rozkład jazdy zachowujący zadaną częstotliwość.

    frequency:
        x/y/z
        x = szczyt DP
        y = pozostałe DP
        z = DŚ
    """

    peak, weekday, holiday = map(
        int,
        frequency.split("/")
    )

    def generate_day(intervals):
        result = {}

        for start_hour, end_hour, interval in intervals:

            minute = random.randint(0, interval - 1)

            total = start_hour * 60 + minute
            end = end_hour * 60

            while total < end:

                hour = total // 60
                minute_of_hour = total % 60

                result.setdefault(
                    str(hour),
                    []
                ).append(
                    minute_of_hour
                )

                # lekkie losowe odchylenie,
                # ale średnia pozostaje blisko częstotliwości
                variation = random.choice([-1, 0, 0, 0, 1])

                total += max(
                    1,
                    interval + variation
                )

        return result

    weekday_data = generate_day([
        (5, 9, peak),
        (9, 15, weekday),
        (15, 19, peak),
        (19, 24, weekday)
    ])

    saturday_data = generate_day([
        (5, 24, holiday)
    ])

    return {
        "weekday": weekday_data,
        "saturday": saturday_data
    }

def generate_travel_times(stops):
    """
    Generuje skumulowany czas przejazdu od pierwszego
    rzeczywistego przystanku wariantu.

    Między kolejnymi przystankami:
    - najczęściej 1 minuta,
    - czasami 2 minuty.

    Przykład:
        0
        1
        2
        4
        5
        6
        8
    """

    elapsed_time = 0
    first_stop = True

    for stop in stops:

        # Wiersz zawierający tylko ulicę
        if not stop.get("name"):
            continue

        # Pierwszy przystanek zawsze = 0
        if first_stop:

            stop["travelTime"] = 0
            first_stop = False

            continue

        # Zwykle 1 minuta, czasem 2
        travel = random.choices(
            [1, 2],
            weights=[85, 15],
            k=1
        )[0]

        elapsed_time += travel

        stop["travelTime"] = elapsed_time


def parse_input(
    text,
    frequency,
    stop_index
):

    lines = text.splitlines()

    rows = [
        split_tsv(line)
        for line in lines
    ]

    while rows and is_empty_row(rows[0]):
        rows.pop(0)

    while rows and is_empty_row(rows[-1]):
        rows.pop()

    if not rows:

        raise ValueError(
            "input.txt jest pusty."
        )

    # --------------------------------------------------------
    # OPIS LINII
    # --------------------------------------------------------

    first_row = rows[0]

    line_number, line_type, line_description = \
        detect_line_info(first_row)

    # --------------------------------------------------------
    # KIERUNKI
    #
    # Szukamy wszystkich nagłówków w całej tabeli.
    # --------------------------------------------------------

    directions = []

    for row_index, row in enumerate(rows):

        for column, cell in enumerate(row):

            direction = parse_direction(
                cell
            )

            if direction:

                directions.append({
                    "row": row_index,
                    "column": column,
                    "name": direction["name"]
                })

    if not directions:

        raise ValueError(
            "Nie znaleziono żadnego kierunku."
        )

    # --------------------------------------------------------
    # PARSOWANIE KIERUNKÓW
    # --------------------------------------------------------

    routes = []
    used_route_names = set()

    for direction_index, direction in enumerate(
        directions
    ):

        start_row = direction["row"]
        start_column = direction["column"]

        # ----------------------------------------------------
        # LEWA / PRAWA POŁOWA TABELI
        # ----------------------------------------------------

        if start_column < 5:

            columns = (
                0,
                1,
                2,
                3
            )

        else:

            columns = (
                5,
                6,
                7,
                8
            )

        # ----------------------------------------------------
        # SZUKAMY NASTĘPNEGO KIERUNKU
        # ----------------------------------------------------

        end_row = len(rows)

        for next_direction in directions[
            direction_index + 1:
        ]:

            if next_direction["row"] > start_row:

                end_row = next_direction["row"]

                break

        # ----------------------------------------------------
        # WYCIĄGNIĘCIE ODPOWIEDNICH KOLUMN
        # ----------------------------------------------------

        side_rows = []

        for row in rows[
            start_row + 1:end_row
        ]:

            ensure_columns(
                row,
                9
            )

            side_rows.append([
                row[columns[0]],
                row[columns[1]],
                row[columns[2]],
                row[columns[3]]
            ])

        # ----------------------------------------------------
        # PRZYSTANKI
        # ----------------------------------------------------

        stops = parse_side(
            side_rows,
            line_number,
            stop_index
        )

        # ----------------------------------------------------
        # CZASY PRZEJAZDU
        #
        # travelTime oznacza czas OD POCZĄTKU WARIANTU,
        # a nie czas od poprzedniego przystanku.
        # ----------------------------------------------------

        generate_travel_times(
            stops
        )

        # ----------------------------------------------------
        # PRAWDZIWE PRZYSTANKI
        # ----------------------------------------------------

        real_stops = [
            stop
            for stop in stops
            if stop.get("name")
        ]

        if real_stops:

            route_from = real_stops[0]["name"]
            route_to = real_stops[-1]["name"]

        else:

            route_from = ""
            route_to = ""

        # ----------------------------------------------------
        # NAZWA TRASY
        # ----------------------------------------------------

        letters = "".join(
            char
            for char in route_to
            if char.isalpha()
        ).upper()

        base_name = "TP-" + letters[:3]

        route_name = base_name

        if route_name in used_route_names:

            for char in letters[3:]:

                candidate = (
                    base_name[:-1] + char
                )

                if candidate not in used_route_names:

                    route_name = candidate

                    break

            else:

                number = 2

                while (
                    base_name + str(number)
                    in used_route_names
                ):
                    number += 1

                route_name = (
                    base_name + str(number)
                )

        used_route_names.add(
            route_name
        )

        # ----------------------------------------------------
        # TRASA
        # ----------------------------------------------------

        routes.append({
            "id": route_name,
            "name": route_name,
            "from": route_from,
            "to": route_to,
            "stops": stops,
            "timetable": generate_timetable(frequency)
        })

    # --------------------------------------------------------
    # WYNIK
    # --------------------------------------------------------

    return {
        "line": line_number,
        "type": line_type,
        "description": line_description,
        "validFrom": date.today().isoformat(),
        "routes": routes
    }

# ============================================================
# ZAPIS PLIKÓW ZESPOŁÓW
# ============================================================

def save_stop_groups(stop_index):

    STOPS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    stops_data = load_stops_file()

    # --------------------------------------------------------
    # KAŻDY ZESPÓŁ
    # --------------------------------------------------------

    for group in stop_index["groups"]:

        output_file = (
            STOPS_DIR /
            f"{group['id']}.json"
        )

        districts = []

        for stop_data in group.get("stops", {}).values():

            for street in stop_data.get("streets", []):

                district = stops_data.get(
                    normalize_name(street),
                    ""
                )

                if district and district not in districts:
                    districts.append(district)

        data = {
            "id": group["id"],
            "name": group.get("name", ""),
            "streetKey": group.get("streetKey", ""),
            "district": districts[0] if districts else "",
            "stops": group.get("stops", {})
        }

        output_file.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )

    # --------------------------------------------------------
    # INDEX GLOBALNY
    #
    # WAŻNE:
    # Nie zapisujemy już tylko id + name.
    # Całe dane zespołów są dostępne od razu w index.json.
    # --------------------------------------------------------

    index_output = {
        "groups": []
    }

    for group in stop_index["groups"]:

        districts = []

        for stop_data in group.get("stops", {}).values():

            for street in stop_data.get("streets", []):

                district = stops_data.get(
                    normalize_name(street),
                    ""
                )

                if district and district not in districts:
                    districts.append(district)

        index_output["groups"].append({
            "id": group["id"],
            "name": group.get("name", ""),
            "streetKey": group.get("streetKey", ""),
            "district": districts[0] if districts else "",
            "stops": group.get("stops", {})
        })

    STOPS_INDEX_FILE.write_text(
        json.dumps(
            index_output,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

    print(
        f"stop groups: zapisano {len(index_output['groups'])} zespołów"
    )

def save_stops_json(stops):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    STOPS_JSON_FILE.write_text(
        json.dumps(
            stops,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

    print(
        f"stops.json: zapisano {len(stops)} przystanków"
    )

# ============================================================
# LINES.JSON
# ============================================================

def update_lines(
    line_number,
    line_type,
    description
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if LINES_FILE.exists():

        try:

            lines = json.loads(
                LINES_FILE.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(lines, list):
                raise ValueError

        except Exception:

            print(
                "UWAGA: lines.json jest nieprawidłowy."
            )

            lines = []

    else:

        lines = []

    existing = None

    for line in lines:

        if str(
            line.get("id")
        ) == str(line_number):

            existing = line
            break

    if existing:

        existing["name"] = line_number
        existing["type"] = line_type
        existing["description"] = description

        action = "zaktualizowano"

    else:

        lines.append({
            "id": line_number,
            "name": line_number,
            "type": line_type,
            "description": description
        })

        action = "dodano"

    # --------------------------------------------------------
    # SORTOWANIE
    # --------------------------------------------------------

    def sort_key(item):

        value = str(
            item.get(
                "id",
                ""
            )
        )

        if value.isdigit():

            return (
                0,
                int(value)
            )

        return (
            1,
            value
        )

    lines.sort(
        key=sort_key
    )

    LINES_FILE.write_text(
        json.dumps(
            lines,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

    print(
        f"lines.json: {action} linię {line_number}"
    )


# ============================================================
# PODSUMOWANIE
# ============================================================

def print_summary(data):

    print()
    print(
        "========================================"
    )
    print(
        "             KONWERSJA OK"
    )
    print(
        "========================================"
    )
    print()

    print(
        f"Linia: {data['line']}"
    )

    print(
        f"Opis:  {data['description']}"
    )

    print()

    for route in data["routes"]:

        real_stops = [
            stop
            for stop in route["stops"]
            if stop.get("name")
        ]

        print(
            f"Kierunek {route['id']}: "
            f"{route['from']} -> {route['to']}"
        )

        print(
            f"  przystanków: {len(real_stops)}"
        )

        print()

    print(
        "========================================"
    )
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    
    # --------------------------------------------------------
    # LISTA PRZYSTANKÓW / DZIELNIC
    # --------------------------------------------------------

    stops_data = load_stops_file()

    save_stops_json(
        stops_data
    )

    # --------------------------------------------------------
    # SZUKANIE PLIKÓW TXT
    # --------------------------------------------------------

    input_files = sorted(
        path
        for path in SCRIPT_DIR.glob("*.txt")
        if path.name.lower() != "stops.txt"
    )

    if not input_files:

        print(
            f"BŁĄD: nie znaleziono żadnych plików .txt w {SCRIPT_DIR}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # ZESPOŁY
    #
    # Jeden wspólny index dla wszystkich plików.
    # Dzięki temu ten sam zespół przystankowy będzie
    # rozpoznawany również pomiędzy różnymi liniami.
    # --------------------------------------------------------

    stop_index = load_stop_index()

    processed = 0

    # --------------------------------------------------------
    # PRZETWARZANIE KAŻDEGO PLIKU
    # --------------------------------------------------------

    for input_file in input_files:

        print()
        print(
            "========================================"
        )
        print(
            f"PLIK: {input_file.name}"
        )
        print(
            "========================================"
        )

        # ----------------------------------------------------
        # ODCZYT
        # ----------------------------------------------------

        try:

            text = input_file.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            print(
                "BŁĄD: plik musi być zapisany jako UTF-8."
            )

            continue

        lines = text.splitlines()

        if not lines:

            print(
                "BŁĄD: plik jest pusty."
            )

            continue

        # ----------------------------------------------------
        # CZĘSTOTLIWOŚĆ
        #
        # Ostatnia linia pliku:
        #
        # 10/20/30
        # ----------------------------------------------------

        frequency = lines[-1].strip()

        if not re.fullmatch(
            r"\d+/\d+/\d+",
            frequency
        ):

            print(
                f"BŁĄD: ostatnia linia pliku "
                f"nie jest częstotliwością X/Y/Z: "
                f"{frequency}"
            )

            continue
            
        table_text = "\n".join(lines[:-1])

        # ----------------------------------------------------
        # PARSOWANIE
        # ----------------------------------------------------

        try:

            data = parse_input(
                table_text,
                frequency,
                stop_index
            )

        except Exception as error:

            print(
                f"BŁĄD podczas parsowania: {error}"
            )

            continue

        line_number = data["line"]
        line_type = data["type"]

        # ----------------------------------------------------
        # ZAPIS LINII
        # ----------------------------------------------------

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file = (
            DATA_DIR /
            f"{line_number}.json"
        )

        output_file.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )

        print(
            f"Zapisano: {output_file}"
        )

        # ----------------------------------------------------
        # LINES.JSON
        # ----------------------------------------------------

        update_lines(
            line_number,
            line_type,
            data["description"]
        )

        print_summary(
            data
        )

        processed += 1

    # --------------------------------------------------------
    # ZAPIS WSZYSTKICH ZESPOŁÓW
    #
    # Dopiero po przetworzeniu wszystkich plików.
    # --------------------------------------------------------

    save_stop_groups(
        stop_index
    )

    print()
    print(
        "========================================"
    )
    print(
        f"PRZETWORZONO PLIKÓW: {processed}/{len(input_files)}"
    )
    print(
        "========================================"
    )
    print()

if __name__ == "__main__":
    main()