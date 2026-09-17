const BASE = "data/";


/* =========================================================
   PARAMETRY URL
   ========================================================= */

function getParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}


/* =========================================================
   WCZYTYWANIE JSON
   ========================================================= */

async function getJSON(path) {

    const response = await fetch(path);

    if (!response.ok) {
        throw new Error("Nie można wczytać: " + path);
    }

    return await response.json();
}


/* =========================================================
   WCZYTYWANIE JEDNEJ LINII
   ========================================================= */

async function getLine(lineId) {

    return await getJSON(
        BASE + encodeURIComponent(lineId) + ".json"
    );
}


/* =========================================================
   NORMALIZACJA TRAS
   ========================================================= */

function getRoutes(line) {

    if (Array.isArray(line.routes)) {

        return line.routes.filter(
            route =>
                route &&
                route.id &&
                String(route.id).startsWith("TP-")
        );
    }

    if (line.routes && typeof line.routes === "object") {

        return Object.entries(line.routes)
            .map(
                ([id, route]) => ({
                    id: id,
                    ...route
                })
            )
            .filter(
                route =>
                    route &&
                    route.id &&
                    String(route.id).startsWith("TP-")
            );
    }

    return [];
}

/* =========================================================
   STRONA Z LISTĄ LINII
   ========================================================= */

async function loadLines() {

    const container = document.getElementById("lines");

    try {

        const lines = await getJSON(
            BASE + "lines.json"
        );

let output = "";

const sortedLines = [...lines].sort((a, b) => {
    const aName = String(a.name);
    const bName = String(b.name);

    const aIsE = aName.toUpperCase().startsWith("E");
    const bIsE = bName.toUpperCase().startsWith("E");

    if (aIsE && !bIsE) return -1;
    if (!aIsE && bIsE) return 1;

    return aName.localeCompare(bName, "pl", {
        numeric: true,
        sensitivity: "base"
    });
});

for (let i = 0; i < sortedLines.length; i++) {
    const line = sortedLines[i];

    output +=
        '<span class="line-cell">' +
            '<a href="line.html?line=' +
            encodeURIComponent(line.id) +
            '">' +
            String(line.name) +
            '</a>' +
        '</span>';

    if ((i + 1) % 12 === 0) {
        output += "<br>";
    }
}

        container.innerHTML = output;

    } catch (error) {

        container.textContent =
            "BŁĄD: " + error.message;
    }
}


/* =========================================================
   STRONA LINII
   ========================================================= */

async function loadLine() {

    const lineId = getParam("line");

    if (!lineId) {
        window.location.href = "index.html";
        return;
    }

    try {

        const line = await getLine(lineId);

        const routes = getRoutes(line);

        document.title =
            "ZTM Warszawa - Linia " + line.line;

        document.getElementById("line-header").innerHTML =
            '<strong class="line-number">' +
            line.line +
            '</strong> - ' +
            ((line.description.toUpperCase()) || "");

        let output =
            "Trasa          Początek trasy                    Koniec trasy  (kierunek)\n\n";

        for (const route of routes) {

            output +=
                '<a href="route.html?line=' +
                encodeURIComponent(lineId) +
                '&route=' +
                encodeURIComponent(route.id) +
                '">' +

                padRight(route.name || route.id, 15) +
                padRight(route.from || "", 29) +
                "-->  " +
                padRight(route.to || "", 29) +

                "</a>\n\n";
        }

        document.getElementById("routes").innerHTML =
            output;

    } catch (error) {

        document.getElementById("line-header").textContent =
            "BŁĄD: " + error.message;
    }
}


/* =========================================================
   SPRAWDZENIE CZY TO OSTATNI PRZYSTANEK
   ========================================================= */

function isLastStop(route, index) {

    const stops = route.stops || [];

    let lastStopIndex = -1;

    for (let i = 0; i < stops.length; i++) {

        if (stops[i].name) {
            lastStopIndex = i;
        }
    }

    return index === lastStopIndex;
}


/* =========================================================
   OZNACZENIA PRZYSTANKU
   ========================================================= */

function getStopFlags(stop) {

    /*
     * K oraz WYS są celowo niewyświetlane.
     *
     * Pokazujemy tylko NŻ.
     */

    if (stop.request === true) {
        return "        NŻ";
    }

    return "";
}


/* =========================================================
   WIERSZ SAMEJ ULICY
   ========================================================= */

function formatStreetRow(stop) {

    if (!stop.street) {
        return "";
    }

    return padRight(
        stop.street.toUpperCase(),
        32
    );
}


/* =========================================================
   WIERSZ PRZYSTANKU
   ========================================================= */

function formatStopRow(
    stop,
    lineId,
    routeId,
    isLast,
    showStreet
) {

    /*
     * Ulica tylko przy wyświetlaniu jest uppercase.
     */

    const street =
        showStreet
            ? padRight(
                String(stop.street || "").toUpperCase(),
                32
            )
            : padRight("", 32);

    /*
     * Stała szerokość nazwy przystanku.
     */

    const name = padRight(
        stop.name || "",
        28
    );

    const number = padLeft(
        stop.number || "",
        3
    );

    /*
     * Czas przejazdu od początku wariantu.
     */

    const travelTime =
        stop.travelTime !== undefined
            ? String(stop.travelTime)
            : "";

    const timePart =
        "|" +
        padLeft(travelTime, 2) +
        "|";

    /*
     * NŻ ma być PRZED czasem.
     *
     * Zostawiamy mu stałą szerokość,
     * dzięki czemu nie przesuwa kolumny czasu.
     */

    const flagPart =
        stop.request === true
            ? " NŻ "
            : "    ";

    /*
     * Ostatni przystanek:
     * bez linku.
     */

    if (isLast) {

        return (
            street +
            name +
            " " +
            number +
            flagPart +
            timePart
        );
    }

    /*
     * Normalny przystanek:
     * link.
     */

    const stopUrl =
        "stop.html?line=" +
        encodeURIComponent(lineId) +
        "&route=" +
        encodeURIComponent(routeId) +
        "&stop=" +
        encodeURIComponent(getStopId(stop));

    return (
        street +

        '<a href="' +
        stopUrl +
        '">' +

        name +
        " " +
        number +

        "</a>" +

        flagPart +
        timePart
    );
}

/* =========================================================
   STRONA TRASY
   ========================================================= */

async function loadRoute() {

    const lineId = getParam("line");
    const routeId = getParam("route");

    if (!lineId || !routeId) {
        window.location.href = "index.html";
        return;
    }

    try {

        const line = await getLine(lineId);

        const routes = getRoutes(line);

        const route = routes.find(
            r => String(r.id) === String(routeId)
        );

        if (!route) {
            throw new Error("Nie znaleziono trasy.");
        }

        document.title =
            "ZTM Warszawa - Linia " + line.line;

        document.getElementById("route-header").innerHTML =
            '<strong class="line-number">' +
            line.line +
            '</strong> - ' +
            ((line.description.toUpperCase()) || "");

        let output =
            "Ulica lub --Miejscowość--        Przystanek                  Nr     Czasy\n"

        const stops = route.stops || [];

        /*
         * Ostatnia ulica/przystanek, którą faktycznie
         * pokazaliśmy.
         *
         * WAŻNE:
         * nie zmieniamy JSON-a.
         */

        let displayedStreet = "";

        for (let i = 0; i < stops.length; i++) {

            const stop = stops[i];

            output += "\n";

            /* ------------------------------------------------
               WIERSZ BEZ PRZYSTANKU
               ------------------------------------------------ */

            if (!stop.name) {

                /*
                 * Ulica sama w sobie jest ważną informacją.
                 *
                 * Jeżeli jest taka sama jak poprzednio
                 * wyświetlona ulica, nie powtarzamy jej.
                 */

                if (
                    stop.street &&
                    stop.street !== displayedStreet
                ) {

                    output +=
                        formatStreetRow(stop);

                    displayedStreet =
                        stop.street;
                }

                continue;
            }

            /* ------------------------------------------------
               PRZYSTANEK
               ------------------------------------------------ */

            const showStreet =
                stop.street !== displayedStreet;

            output +=
                formatStopRow(
                    stop,
                    lineId,
                    routeId,
                    isLastStop(route, i),
                    showStreet
                );

            /*
             * Zapamiętujemy ulicę nawet wtedy,
             * kiedy jej nie pokazaliśmy.
             *
             * Dzięki temu kolejny przystanek na tej samej
             * ulicy również jej nie pokaże.
             */

            if (stop.street) {
                displayedStreet =
                    stop.street;
            }
        }

        document.getElementById("stops").innerHTML =
            output;

    } catch (error) {

        document.getElementById("route-header").textContent =
            "BŁĄD: " + error.message;
    }
}


/* =========================================================
   ZNALEZIENIE PRZYSTANKU
   ========================================================= */

function findStop(route, stopId) {

    const stops = route.stops || [];

    return stops.find(
        stop =>
            stop.name &&
            getStopId(stop) === String(stopId)
    );
}


/* =========================================================
   ZNALEZIENIE TIMETABLE
   ========================================================= */

function getTimetable(line, route) {
    return route.timetable || null;
}


/* =========================================================
   STRONA PRZYSTANKU
   ========================================================= */

function getTimetableWidth(weekday) {

    let maxCount = 0;

    for (const hour of Object.keys(weekday)) {

        maxCount = Math.max(
            maxCount,
            weekday[hour].length
        );
    }

    return Math.max(
        30,
        maxCount * 5 + 8
    );
}

async function loadStop() {

    const lineId = getParam("line");
    const routeId = getParam("route");
    const stopId = getParam("stop");

    if (!lineId || !routeId || !stopId) {
        window.location.href = "index.html";
        return;
    }

    try {

        const line = await getLine(lineId);

        const routes = getRoutes(line);

        const route = routes.find(
            r => String(r.id) === String(routeId)
        );

        if (!route) {
            throw new Error("Nie znaleziono trasy.");
        }

        const stop = findStop(
            route,
            stopId
        );

        if (!stop) {
            throw new Error(
                "Nie znaleziono przystanku " + stopId
            );
        }

        /*
         * Ostatni przystanek nigdy nie jest dostępny.
         */

        const stopIndex =
            route.stops.indexOf(stop);

        if (isLastStop(route, stopIndex)) {

            throw new Error(
                "Nie można wybrać ostatniego przystanku tej trasy."
            );
        }

        document.title =
            "ZTM Warszawa - Linia " + line.line;

        const header =
            '<strong class="line-number">' +
            line.line +
            '</strong> - ' +
            ((line.description.toUpperCase()) || "");

        document.getElementById("stop-header").innerHTML =
            header;

		let output = "";
	
		const stopGroupUrl =
			"stop-group.html?group=" +
			encodeURIComponent(stop.groupId);
	
		document.getElementById(
		"stop-info"
		).innerHTML =
		"Przystanek: " +
		'<a href="' +
		stopGroupUrl +
		'">' +
		stop.name +
		"</a>" +
		" " +
		stop.number +
		"  -->  " +
		route.to +
		"\n\n\n";

        const timetable =
            getTimetable(line, route);

        if (!timetable) {

            output +=
                "Brak rozkładu jazdy dla tego przystanku.\n";

            document.getElementById("timetable").innerHTML  =
                output;

            return;
        }
		
		const timetableWidth = getTimetableWidth(
			timetable.weekday || {}
		);

        output +=
            " DZIEŃ POWSZEDNI".padEnd(timetableWidth) +
            "ŚWIĘTO i SOBOTA\n\n";

        output +=
            "|Godz. Minuty".padEnd(timetableWidth) +
            "|Godz. Minuty\n";

        output +=
            buildTimetable(
                timetable.weekday || {},
                timetable.saturday || {},
                stop.travelTime || 0
            );

        output +=
            "\n\n Rozkład ważny od " +
            (line.validFrom || timetable.validFrom || "") +
            "\n\n";

        output +=
            " OBJAŚNIENIE SYMBOLI:\n\n" +
            " [] - kurs realizowany przez pojazd niskopodłogowy\n";

        document.getElementById("timetable").textContent =
            output;

    } catch (error) {

        document.getElementById("timetable").textContent =
            "BŁĄD: " + error.message;
    }
}


/* =========================================================
   GENEROWANIE TABELI GODZIN
   ========================================================= */

function buildTimetable(
    weekday,
    saturday,
    offset
) {

    let output = "";

    const allTimes = [];
    const allSaturdayTimes = [];

    for (const hour of Object.keys(weekday)) {

        for (const minute of weekday[hour]) {

            const total =
                Number(hour) * 60 +
                Number(minute) +
                Number(offset);

            allTimes.push({
                hour: Math.floor(total / 60) % 24,
                minute: total % 60
            });
        }
    }

    for (const hour of Object.keys(saturday)) {

        for (const minute of saturday[hour]) {

            const total =
                Number(hour) * 60 +
                Number(minute) +
                Number(offset);

            allSaturdayTimes.push({
                hour: Math.floor(total / 60) % 24,
                minute: total % 60
            });
        }
    }

    const hours = new Set([
        ...allTimes.map(x => x.hour),
        ...allSaturdayTimes.map(x => x.hour)
    ]);

    const sortedHours =
        Array.from(hours).sort(
            (a, b) => a - b
        );

    /*
     * Ustalamy dynamiczną szerokość lewej kolumny.
     *
     * Każdy odjazd zajmuje 5 znaków:
     * [00] + spacja
     *
     * Dzięki temu nawet przy częstotliwości
     * co 2 minuty wszystkie odjazdy się mieszczą.
     */

    let maxWeekday = 0;
    let maxSaturday = 0;

    for (const hour of sortedHours) {

        const weekdayCount =
            allTimes.filter(
                x => x.hour === hour
            ).length;

        const saturdayCount =
            allSaturdayTimes.filter(
                x => x.hour === hour
            ).length;

        maxWeekday =
            Math.max(
                maxWeekday,
                weekdayCount
            );

        maxSaturday =
            Math.max(
                maxSaturday,
                saturdayCount
            );
    }

    /*
     * Szerokość kolumny zależy od największej liczby
     * odjazdów występujących w jednej godzinie.
     *
     * Minimum zachowuje dotychczasowy wygląd.
     */

    const weekdayWidth =
        Math.max(
            30,
            maxWeekday * 5 + 8
        );

    for (const hour of sortedHours) {

        const weekdayMinutes =
            allTimes
                .filter(
                    x => x.hour === hour
                )
                .map(
                    x => x.minute
                )
                .sort(
                    (a, b) => a - b
                );

        const saturdayMinutes =
            allSaturdayTimes
                .filter(
                    x => x.hour === hour
                )
                .map(
                    x => x.minute
                )
                .sort(
                    (a, b) => a - b
                );

        const left =
            "| " +
            padLeft(
                String(hour),
                2
            ) +
            " | " +
            formatMinutes(
                weekdayMinutes.map(
                    minute => ({
                        minute: minute
                    })
                )
            );

        const right =
            "| " +
            padLeft(
                String(hour),
                2
            ) +
            " | " +
            formatMinutes(
                saturdayMinutes.map(
                    minute => ({
                        minute: minute
                    })
                )
            );

        output +=
            left.padEnd(weekdayWidth) +
            right +
            "\n";
    }

    return output;
}

/* =========================================================
   DODAWANIE OFFSETU
   ========================================================= */

function calculateTimes(
    minutes,
    offset
) {

    return minutes.map(minute => {

        let total =
            minute + offset;

        let hourShift =
            Math.floor(total / 60);

        let newMinute =
            total % 60;

        return {
            minute: newMinute,
            hourShift: hourShift
        };
    });
}


/* =========================================================
   FORMATOWANIE MINUT
   ========================================================= */

function formatMinutes(times) {

    if (times.length === 0) {
        return "";
    }

    return times
        .map(time => {

            const minute =
                String(time.minute).padStart(2, "0");

            return "[" + minute + "]";
        })
        .join(" ");
}

/* =========================================================
   FUNKCJE POMOCNICZE
   ========================================================= */

function padRight(
    text,
    length
) {

    text = String(text);

    if (text.length >= length) {
        return text;
    }

    return (
        text +
        " ".repeat(
            length - text.length
        )
    );
}


function padLeft(
    text,
    length
) {

    text = String(text);

    if (text.length >= length) {
        return text;
    }

    return (
        " ".repeat(
            length - text.length
        ) +
        text
    );
}

/* =========================================================
   ZESPÓŁ PRZYSTANKOWY
   ========================================================= */

/*
 * Identyfikator konkretnego przystanku:
 * numer zespołu + numer słupka.
 *
 * NIE zapisujemy stopId w JSON-ie.
 * Jest wyliczany tylko w JS.
 */

function getStopId(stop) {

    return (
        String(stop.groupId || "") +
        String(stop.number || "").padStart(2, "0")
    );
}


/*
 * Typ przystanku.
 */

function getStopType(stop) {

    if (stop.terminus === true) {
        return "krańcowy";
    }

    if (stop.request === true) {
        return "na żądanie";
    }

    return "stały";
}


/*
 * Link do linii.
 */

function formatLineLink(line) {

    return (
        '<a href="line.html?line=' +
        encodeURIComponent(line.line) +
        '">' +
        line.line +
        "</a>"
    );
}


/*
 * STRONA ZESPOŁU PRZYSTANKOWEGO
 *
 * URL:
 *
 * stop-group.html?group=0001
 */

async function loadStopGroup() {

    const groupId = getParam("group");

    if (!groupId) {
        window.location.href = "index.html";
        return;
    }

    try {

        const lines =
            await getJSON(
                BASE + "lines.json"
            );

        const stops = [];

        /*
         * Przeszukujemy wszystkie linie i warianty.
         */
        for (const lineInfo of lines) {

            const line =
                await getLine(lineInfo.id);

            const routes =
                getRoutes(line);

            for (const route of routes) {

                const routeStops =
                    route.stops || [];

                for (const stop of routeStops) {

                    if (
                        !stop.name ||
                        String(stop.groupId) !==
                        String(groupId)
                    ) {
                        continue;
                    }

                    stops.push({
                        line: line,
                        route: route,
                        stop: stop
                    });
                }
            }
        }

        if (stops.length === 0) {

            throw new Error(
                "Nie znaleziono zespołu przystankowego."
            );
        }

        const groupName =
            stops[0].stop.name;

        document.title =
            "ZTM Warszawa - " +
            groupName;

        document.getElementById(
            "group-header"
        ).textContent =
            groupName;

        /*
         * Grupujemy po NUMERZE konkretnego słupka.
         *
         * 01, 02, 05, 06 itd. są osobnymi przystankami.
         */
        const groupedStops = new Map();

        for (const item of stops) {

            const stop = item.stop;

            const key =
                String(stop.number || "");

            if (!groupedStops.has(key)) {

                groupedStops.set(key, {
                    stop: stop,
                    items: []
                });
            }

            groupedStops.get(key).items.push(item);
        }

        /*
         * Sortowanie słupków według numeru.
         */
        const sortedStops =
            Array.from(groupedStops.values())
                .sort((a, b) => {

                    const numberA =
                        parseInt(
                            a.stop.number || "0",
                            10
                        );

                    const numberB =
                        parseInt(
                            b.stop.number || "0",
                            10
                        );

                    return numberA - numberB;
                });

        let output = "";

        /*
         * Kolejność typów.
         */
        const typeOrder = [
            "stały",
            "na żądanie",
            "krańcowy",
            "dla wysiadających"
        ];

        /*
         * Każdy numer słupka = osobny blok.
         */
        for (const group of sortedStops) {

            const stop =
                group.stop;

            /*
             * Pierwsza konwertowana linia,
             * czyli pierwsza linia z lines.json,
             * która ma ten słupek.
             */
            const firstItem =
                group.items[0];

            const firstLine =
                firstItem.line;

            const firstLineRoutes =
                getRoutes(firstLine);

            let destination = "";

            let sourceRoute = null;
            let sourceIndex = -1;

            /*
             * Znajdujemy ten konkretny słupek
             * na pierwszej konwertowanej linii.
             */
            for (const route of firstLineRoutes) {

                const routeStops =
                    route.stops || [];

                const index =
                    routeStops.findIndex(
                        candidate =>
                            candidate.name &&
                            String(candidate.groupId) ===
                            String(stop.groupId) &&
                            String(candidate.number) ===
                            String(stop.number)
                    );

                if (index !== -1) {

                    sourceRoute = route;
                    sourceIndex = index;

                    break;
                }
            }

            /*
             * Szukamy pierwszego następnego
             * zespołu przystankowego o innej nazwie.
             */
            if (sourceRoute) {

                const routeStops =
                    sourceRoute.stops || [];

                for (
                    let i = sourceIndex + 1;
                    i < routeStops.length;
                    i++
                ) {

                    const nextStop =
                        routeStops[i];

                    if (!nextStop.name) {
                        continue;
                    }

                    if (
                        normalizeStopGroupName(
                            nextStop.name
                        ) !==
                        normalizeStopGroupName(
                            stop.name
                        )
                    ) {

                        destination =
                            nextStop.name;

                        break;
                    }
                }

                /*
                 * Fallback:
                 * ostatni rzeczywisty przystanek
                 * pierwszej konwertowanej trasy.
                 */
                if (!destination) {

                    for (
                        let i = routeStops.length - 1;
                        i >= 0;
                        i--
                    ) {

                        if (routeStops[i].name) {

                            destination =
                                routeStops[i].name;

                            break;
                        }
                    }
                }
            }

            /*
             * Ulica
             */
            output +=
                "     Ulica: " +
                String(
                    stop.street || ""
                ).toUpperCase() +
                "\n";

            /*
             * Przystanek
             */
            output +=
                "Przystanek: " +
                stop.name +
                " " +
                stop.number +
                "  -->  " +
                destination +
                "\n";

            /*
             * Nagłówek.
             */
            output +=
                "Typ przystanku      Linie\n";

            /*
             * Grupujemy linie według typu.
             *
             * Ta sama linia na kilku wariantach
             * wystąpi tylko raz.
             */
            const typeLines = new Map();

            for (const item of group.items) {

                const line =
                    item.line;

                const lineStop =
                    item.stop;

                const type =
                    getStopType(lineStop);

                const lineKey =
                    String(line.line);

                if (!typeLines.has(type)) {
                    typeLines.set(type, new Map());
                }

                if (
                    !typeLines
                        .get(type)
                        .has(lineKey)
                ) {

                    typeLines
                        .get(type)
                        .set(
                            lineKey,
                            line
                        );
                }
            }

            /*
             * Wypisujemy:
             *
             * stały:
             * na żądanie:
             * krańcowy:
             * dla wysiadających:
             *
             * i dopiero za dwukropkiem
             * wszystkie linie.
             */
            for (const type of typeOrder) {

                const linesOfType =
                    typeLines.get(type);

                if (
                    !linesOfType ||
                    linesOfType.size === 0
                ) {
                    continue;
                }

                const sortedLines =
                    Array.from(
                        linesOfType.entries()
                    ).sort(
                        ([a], [b]) => {

                            const aIsE =
                                String(a)
                                    .toUpperCase()
                                    .startsWith("E");

                            const bIsE =
                                String(b)
                                    .toUpperCase()
                                    .startsWith("E");

                            if (aIsE && !bIsE) {
                                return -1;
                            }

                            if (!aIsE && bIsE) {
                                return 1;
                            }

                            return a.localeCompare(
                                b,
                                "pl",
                                {
                                    numeric: true,
                                    sensitivity: "base"
                                }
                            );
                        }
                    );

                output +=
                    "- " +
                    padRight(
                        type + ":",
                        18
                    );

                for (
                    const [, line]
                    of sortedLines
                ) {

                    output +=
                        formatLineLink(line) +
                        "  ";
                }

                output += "\n";
            }

            output += "\n\n";
        }

        document.getElementById(
            "group-info"
        ).innerHTML =
            output;

    } catch (error) {

        document.getElementById(
            "group-info"
        ).textContent =
            "BŁĄD: " +
            error.message;
    }
}

function normalizeStopGroupName(name) {

    return String(name || "")
        .trim()
        .toUpperCase()
        .replace(/\s+/g, " ");
}

/* =========================================================
   STRONA Z LISTĄ ZESPOŁÓW PRZYSTANKOWYCH
   ========================================================= */

/* =========================================================
   STRONA Z LISTĄ ZESPOŁÓW PRZYSTANKOWYCH
   ========================================================= */

function getGroupDistrict(group, stopsData) {

    if (!group || !stopsData) {
        return "";
    }

    const normalize = value =>
        String(value || "")
            .trim()
            .toUpperCase()
            .replace(/\s+/g, " ");

    /*
     * Zbieramy wszystkie ulice występujące
     * w przystankach tego zespołu.
     */
    const streets = new Set();

    for (const stop of Object.values(group.stops || {})) {

        for (const street of (stop.streets || [])) {

            const key = normalize(street);

            if (key) {
                streets.add(key);
            }
        }
    }

    /*
     * Szukamy ulic w stops.json.
     */
    for (const street of streets) {

        if (stopsData[street]) {
            return stopsData[street];
        }
    }

    return "";
}

async function loadStopGroups() {

    const container =
        document.getElementById("groups");

    if (!container) {
        return;
    }

    try {

        const [data, stopsData] = await Promise.all([
			getJSON(BASE + "stops/index.json"),
			getJSON(BASE + "stops.json")
		]);

        /*
         * Obsługujemy oba warianty:
         *
         * 1. { "groups": [...] }
         * 2. [ ... ]
         */

        let groups = [];

        if (Array.isArray(data)) {

            groups = [...data];

        } else if (
            data &&
            Array.isArray(data.groups)
        ) {

            groups = [...data.groups];
        }

        if (groups.length === 0) {

            container.textContent =
                "Brak zespołów przystankowych.";

            console.warn(
                "stops/index.json nie zawiera zespołów:",
                data
            );

            return;
        }

        /*
         * ----------------------------------------------------
         * SORTOWANIE
         * ----------------------------------------------------
         */

        groups.sort((a, b) => {

            const nameA =
                String(a?.name || "").trim();

            const nameB =
                String(b?.name || "").trim();

            /*
             * Zespoły bez nazwy na końcu.
             */

            if (!nameA && !nameB) {

                return String(a?.id || "")
                    .localeCompare(
                        String(b?.id || ""),
                        "pl",
                        {
                            numeric: true
                        }
                    );
            }

            if (!nameA) {
                return 1;
            }

            if (!nameB) {
                return -1;
            }

            return nameA.localeCompare(
                nameB,
                "pl",
                {
                    numeric: true,
                    sensitivity: "base"
                }
            );
        });

        /*
         * ----------------------------------------------------
         * ZNAKI INDEKSU
         * ----------------------------------------------------
         */

        const indexChars = [];

        for (const group of groups) {

            const name =
                String(group?.name || "").trim();

            if (!name) {
                continue;
            }

            const firstChar =
                name.charAt(0).toUpperCase();

            if (!indexChars.includes(firstChar)) {

                indexChars.push(firstChar);
            }
        }

        /*
         * Cyfry najpierw, potem alfabet polski.
         */

        indexChars.sort((a, b) => {

            const digitA =
                /^\d/.test(a);

            const digitB =
                /^\d/.test(b);

            if (digitA && !digitB) {
                return -1;
            }

            if (!digitA && digitB) {
                return 1;
            }

            return a.localeCompare(
                b,
                "pl",
                {
                    numeric: true,
                    sensitivity: "base"
                }
            );
        });

        /*
         * ----------------------------------------------------
         * INDEKS
         * ----------------------------------------------------
         */

        let indexOutput = "";

        for (
            let i = 0;
            i < indexChars.length;
            i++
        ) {

            const char =
                indexChars[i];

            indexOutput +=
                '<a href="#group-index-' +
                i +
                '">' +
                escapeHtml(char) +
                "</a>";

            if (
                i <
                indexChars.length - 1
            ) {
                indexOutput += " ";
            }
        }

        /*
         * ----------------------------------------------------
         * LISTA
         * ----------------------------------------------------
         */

        let listOutput =
            "Nazwa zespołu przystanków        Dzielnica/miejscowość\n\n";

        let previousFirstChar = "";

        for (const group of groups) {

            const name =
                String(group?.name || "").trim();

            /*
             * Pomijamy wpisy bez nazwy.
             */

            if (!name) {
                continue;
            }

            /*
             * ID jest wymagane do linku.
             */

            const groupId =
                group?.id;

            if (
                groupId === undefined ||
                groupId === null ||
                String(groupId).trim() === ""
            ) {

                console.warn(
                    "Zespół bez ID:",
                    group
                );

                continue;
            }

            const firstChar =
                name.charAt(0).toUpperCase();

            /*
             * ------------------------------------------------
             * KOTWICA
             * ------------------------------------------------
             */

            let anchor = "";

            if (
                firstChar !==
                previousFirstChar
            ) {

                const index =
                    indexChars.indexOf(
                        firstChar
                    );

                if (index !== -1) {

                    anchor =
                        '<a id="group-index-' +
                        index +
                        '"></a>';
                }

                previousFirstChar =
                    firstChar;
            }

            /*
             * ------------------------------------------------
             * MIEJSCOWOŚĆ
             * ------------------------------------------------
             */

			const groupNameNormalized =
				normalizeStopGroupName(name);
			
			let district = "";
			
			for (const [stopGroupName, stopGroupDistrict] of Object.entries(stopsData)) {
			
				if (
					normalizeStopGroupName(stopGroupName) ===
					groupNameNormalized
				) {
					district = String(
						stopGroupDistrict || ""
					).trim();
			
					break;
				}
			}

            /*
             * ------------------------------------------------
             * NAZWA
             * ------------------------------------------------
             */

            const namePart =
                padRight(
                    name,
                    32
                );

            /*
             * ------------------------------------------------
             * WIERSZ
             * ------------------------------------------------
             */

            listOutput +=
                anchor +

                '<a href="stop-group.html?group=' +
                encodeURIComponent(
                    String(groupId)
                ) +
                '">' +

                escapeHtml(namePart) +

                "</a> " +

                escapeHtml(district) +

                "\n";
        }

        /*
         * ----------------------------------------------------
         * WYNIK
         * ----------------------------------------------------
         */

        container.innerHTML =
            '<div class="stop-index">' +
                indexOutput +
            '</div>' +

            '<pre class="stop-list">' +
                listOutput +
            '</pre>';

    } catch (error) {

        console.error(
            "Błąd podczas wczytywania zespołów:",
            error
        );

        container.textContent =
            "BŁĄD: " +
            error.message;
    }
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}