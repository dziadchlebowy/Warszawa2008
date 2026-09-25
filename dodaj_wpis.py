import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from html import escape
from pathlib import Path
import shutil
import re


class NewsEditor:
    def __init__(self, root):
        self.root = root

        self.root.title("Warszawa 2008 — dodawanie aktualności")
        self.root.geometry("950x780")
        self.root.minsize(800, 650)

        self.path_var = tk.StringVar()

        # Licznik kolorów / tagów
        self.color_counter = 0

        self.build_ui()

    # ==========================================================
    # INTERFEJS
    # ==========================================================

    def build_ui(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill="both", expand=True)

        # ------------------------------------------------------
        # PLIK
        # ------------------------------------------------------

        ttk.Label(
            main,
            text="Plik index.html:"
        ).pack(anchor="w")

        path_frame = ttk.Frame(main)
        path_frame.pack(
            fill="x",
            pady=(4, 15)
        )

        self.path_entry = ttk.Entry(
            path_frame,
            textvariable=self.path_var
        )

        self.path_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            path_frame,
            text="Wybierz...",
            command=self.choose_file
        ).pack(
            side="left",
            padx=(8, 0)
        )

        # ------------------------------------------------------
        # DATA
        # ------------------------------------------------------

        ttk.Label(
            main,
            text="Data wpisu:"
        ).pack(anchor="w")

        self.date_entry = ttk.Entry(main)

        self.date_entry.pack(
            fill="x",
            pady=(4, 12)
        )

        # Domyślna data
        self.date_entry.insert(
            0,
            "26 września 2026"
        )

        # ------------------------------------------------------
        # TYTUŁ
        # ------------------------------------------------------

        ttk.Label(
            main,
            text="Tytuł:"
        ).pack(anchor="w")

        self.title_entry = ttk.Entry(main)

        self.title_entry.pack(
            fill="x",
            pady=(4, 12)
        )

        # ------------------------------------------------------
        # EDYTOR
        # ------------------------------------------------------

        ttk.Label(
            main,
            text="Treść wpisu:"
        ).pack(anchor="w")

        ttk.Label(
            main,
            text="Zaznacz tekst i użyj przycisków formatowania."
        ).pack(anchor="w")

        # ------------------------------------------------------
        # PASEK FORMATOWANIA
        # ------------------------------------------------------

        toolbar = ttk.Frame(main)
        toolbar.pack(
            fill="x",
            pady=(5, 5)
        )

        # Pogrubienie
        ttk.Button(
            toolbar,
            text="B",
            width=4,
            command=self.toggle_bold
        ).pack(
            side="left",
            padx=(0, 3)
        )

        # Pochylenie
        ttk.Button(
            toolbar,
            text="I",
            width=4,
            command=self.toggle_italic
        ).pack(
            side="left",
            padx=3
        )

        # Podkreślenie
        ttk.Button(
            toolbar,
            text="U",
            width=4,
            command=self.toggle_underline
        ).pack(
            side="left",
            padx=3
        )

        # Kolor
        ttk.Button(
            toolbar,
            text="Kolor tekstu",
            command=self.choose_color
        ).pack(
            side="left",
            padx=(10, 3)
        )

        # Sygnatura
        ttk.Button(
            toolbar,
            text="Sygnatura",
            command=self.make_signature
        ).pack(
            side="left",
            padx=(10, 3)
        )

        # Separator
        ttk.Separator(
            toolbar,
            orient="vertical"
        ).pack(
            side="left",
            fill="y",
            padx=10
        )

        # Wstawienie przykładowej sygnatury
        ttk.Button(
            toolbar,
            text='Wstaw "//dziad"',
            command=self.insert_signature
        ).pack(
            side="left"
        )

        # ------------------------------------------------------
        # POLE TEKSTOWE
        # ------------------------------------------------------

        content_frame = ttk.Frame(main)

        content_frame.pack(
            fill="both",
            expand=True,
            pady=(4, 10)
        )

        self.content_text = tk.Text(
            content_frame,
            wrap="word",
            undo=True,
            font=("Segoe UI", 11)
        )

        self.content_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            content_frame,
            orient="vertical",
            command=self.content_text.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.content_text.configure(
            yscrollcommand=scrollbar.set
        )

        # ------------------------------------------------------
        # OPCJE
        # ------------------------------------------------------

        options = ttk.Frame(main)

        options.pack(
            fill="x",
            pady=(0, 10)
        )

        self.backup_var = tk.BooleanVar(
            value=True
        )

        ttk.Checkbutton(
            options,
            text="Utwórz kopię zapasową index.html przed zapisem",
            variable=self.backup_var
        ).pack(
            anchor="w"
        )

        # ------------------------------------------------------
        # PRZYCISKI
        # ------------------------------------------------------

        buttons = ttk.Frame(main)

        buttons.pack(
            fill="x",
            pady=(5, 0)
        )

        ttk.Button(
            buttons,
            text="Wyczyść",
            command=self.clear_form
        ).pack(
            side="left"
        )

        ttk.Button(
            buttons,
            text="Dodaj wpis do index.html",
            command=self.add_news
        ).pack(
            side="right"
        )

        # Ctrl + Enter
        self.root.bind(
            "<Control-Return>",
            lambda event: self.add_news()
        )

        # Skróty klawiaturowe
        self.content_text.bind(
            "<Control-b>",
            lambda event: self.toggle_bold()
        )

        self.content_text.bind(
            "<Control-i>",
            lambda event: self.toggle_italic()
        )

        self.content_text.bind(
            "<Control-u>",
            lambda event: self.toggle_underline()
        )

    # ==========================================================
    # PLIK
    # ==========================================================

    def choose_file(self):
        filename = filedialog.askopenfilename(
            title="Wybierz index.html",
            filetypes=[
                ("Pliki HTML", "*.html;*.htm"),
                ("Wszystkie pliki", "*.*")
            ]
        )

        if filename:
            self.path_var.set(filename)

    # ==========================================================
    # FORMATOWANIE
    # ==========================================================

    def get_selection(self):
        try:
            start = self.content_text.index("sel.first")
            end = self.content_text.index("sel.last")
            return start, end
        except tk.TclError:
            messagebox.showwarning(
                "Brak zaznaczenia",
                "Najpierw zaznacz tekst, który chcesz sformatować."
            )
            return None, None

    def toggle_tag(self, tag):
        start, end = self.get_selection()

        if start is None:
            return

        ranges = self.content_text.tag_ranges(tag)

        already_active = False

        for i in range(0, len(ranges), 2):

            tag_start = self.content_text.index(ranges[i])
            tag_end = self.content_text.index(ranges[i + 1])

            if (
                self.content_text.compare(tag_start, "<=", start)
                and self.content_text.compare(tag_end, ">=", end)
            ):
                already_active = True
                break

        if already_active:
            self.content_text.tag_remove(
                tag,
                start,
                end
            )
        else:
            self.content_text.tag_add(
                tag,
                start,
                end
            )

    def toggle_bold(self):
        self.toggle_tag("bold")

    def toggle_italic(self):
        self.toggle_tag("italic")

    def toggle_underline(self):
        self.toggle_tag("underline")

    # ==========================================================
    # KOLOR
    # ==========================================================

    def choose_color(self):
        start, end = self.get_selection()

        if start is None:
            return

        result = colorchooser.askcolor(
            title="Wybierz kolor tekstu"
        )

        if not result or not result[1]:
            return

        color = result[1].lower()

        self.color_counter += 1

        tag_name = f"color_{self.color_counter}"

        self.content_text.tag_configure(
            tag_name,
            foreground=color
        )

        self.content_text.tag_add(
            tag_name,
            start,
            end
        )

    # ==========================================================
    # SYGNATURA
    # ==========================================================

    def make_signature(self):
        start, end = self.get_selection()

        if start is None:
            return

        self.content_text.tag_add(
            "signature",
            start,
            end
        )

    def insert_signature(self):
        self.content_text.insert(
            tk.INSERT,
            "//dziad",
            "signature"
        )

    # ==========================================================
    # CZYSZCZENIE
    # ==========================================================

    def clear_form(self):
        self.title_entry.delete(
            0,
            tk.END
        )

        self.content_text.delete(
            "1.0",
            tk.END
        )

    # ==========================================================
    # POBIERANIE FORMATOWANIA DLA ZNAKU
    # ==========================================================

    def get_tags_at(self, index):
        return self.content_text.tag_names(index)

    # ==========================================================
    # KONWERSJA TEKSTU NA HTML
    # ==========================================================

    def text_to_html(self):
        """
        Konwertuje zawartość Text na HTML,
        zachowując formatowanie.
        """

        text = self.content_text.get(
            "1.0",
            "end-1c"
        )

        if not text.strip():
            return ""

        lines = text.split("\n")

        result = []

        for line_number, line in enumerate(lines, start=1):

            start_index = f"{line_number}.0"
            end_index = f"{line_number}.end"

            if not line:
                continue

            html_line = self.format_line(
                start_index,
                end_index
            )

            if html_line.strip():
                result.append(
                    html_line
                )

        # ------------------------------------------------------
        # ŁĄCZENIE ZWYKŁYCH LINII W AKAPITY
        # ------------------------------------------------------

        paragraphs = []

        current = []

        for item in result:

            if item.startswith(
                '<div class="signature">'
            ):

                if current:
                    paragraphs.append(
                        "<p>" +
                        " ".join(current) +
                        "</p>"
                    )

                    current = []

                paragraphs.append(
                    item
                )

            else:

                current.append(item)

        if current:
            paragraphs.append(
                "<p>" +
                " ".join(current) +
                "</p>"
            )

        return "\n".join(
            "        " + paragraph
            for paragraph in paragraphs
        )

    # ==========================================================
    # FORMATOWANIE POJEDYNCZEJ LINII
    # ==========================================================

    def format_line(self, start, end):
        """
        Zamienia pojedynczą linię tekstu
        na HTML z zachowaniem tagów.
        """

        index = start
        result = []

        while self.content_text.compare(
            index,
            "<",
            end
        ):

            next_index = self.content_text.index(
                f"{index} + 1 char"
            )

            char = self.content_text.get(
                index,
                next_index
            )

            tags = self.get_tags_at(index)

            # --------------------------------------------------
            # ZNAKI HTML
            # --------------------------------------------------

            char = escape(char)

            # --------------------------------------------------
            # SYGNATURA
            # --------------------------------------------------

            if "signature" in tags:

                # Sygnatura obsługiwana osobno.
                # Jeżeli znajduje się w zwykłym akapicie,
                # traktujemy ją jako tekst.
                char = char

            # --------------------------------------------------
            # BOLD
            # --------------------------------------------------

            if "bold" in tags:
                char = f"<strong>{char}</strong>"

            # --------------------------------------------------
            # ITALIC
            # --------------------------------------------------

            if "italic" in tags:
                char = f"<em>{char}</em>"

            # --------------------------------------------------
            # UNDERLINE
            # --------------------------------------------------

            if "underline" in tags:
                char = f"<u>{char}</u>"

            # --------------------------------------------------
            # KOLOR
            # --------------------------------------------------

            colors = [
                tag
                for tag in tags
                if tag.startswith("color_")
            ]

            if colors:

                color_tag = colors[-1]

                # Tkinter nie daje prostego API do
                # pobierania konfiguracji taga,
                # dlatego pobieramy foreground.

                color = self.content_text.tag_cget(
                    color_tag,
                    "foreground"
                )

                if color:
                    char = (
                        f'<span style="color: {color};">'
                        f'{char}'
                        f'</span>'
                    )

            result.append(char)

            index = next_index

        return "".join(result)

    # ==========================================================
    # SPECJALNA KONWERSJA SYGNATUR
    # ==========================================================

    def make_signature_html(self):
        """
        Osobna obsługa sygnatur.
        """

        text = self.content_text.get(
            "1.0",
            "end-1c"
        )

        lines = text.split("\n")

        result = []

        for number, line in enumerate(lines, start=1):

            if not line.strip():
                continue

            start = f"{number}.0"
            end = f"{number}.end"

            tags = self.content_text.tag_names(start)

            if "signature" in tags:

                value = escape(line.strip())

                result.append(
                    f'<div class="signature">{value}</div>'
                )

        return result

    # ==========================================================
    # NOWA METODA — LEPSZA KONWERSJA Z SYGNATURAMI
    # ==========================================================

    def generate_content_html(self):
        """
        Buduje HTML na podstawie tekstu i tagów Tkintera.

        Zwykłe linie:
            <p>...</p>

        Sygnatura:
            <div class="signature">...</div>
        """

        total_lines = int(
            self.content_text.index("end-1c").split(".")[0]
        )

        paragraphs = []

        current_parts = []

        for line_number in range(1, total_lines + 1):

            start = f"{line_number}.0"
            end = f"{line_number}.end"

            line = self.content_text.get(
                start,
                end
            )

            if not line.strip():

                if current_parts:
                    paragraphs.append(
                        "<p>" +
                        "".join(current_parts) +
                        "</p>"
                    )

                    current_parts = []

                continue

            # Czy cała linia jest sygnaturą?
            line_tags = self.content_text.tag_names(
                start
            )

            if "signature" in line_tags:

                if current_parts:
                    paragraphs.append(
                        "<p>" +
                        "".join(current_parts) +
                        "</p>"
                    )

                    current_parts = []

                value = escape(
                    line.strip()
                )

                paragraphs.append(
                    f'<div class="signature">{value}</div>'
                )

                continue

            # Zwykła linia
            formatted = self.format_line(
                start,
                end
            )

            current_parts.append(
                formatted
            )

        if current_parts:
            paragraphs.append(
                "<p>" +
                "".join(current_parts) +
                "</p>"
            )

        return "\n".join(
            "        " + item
            for item in paragraphs
        )

    # ==========================================================
    # DODAWANIE WPISU
    # ==========================================================

    def add_news(self):

        # ------------------------------------------------------
        # PLIK
        # ------------------------------------------------------

        path_text = self.path_var.get().strip()

        if not path_text:

            messagebox.showwarning(
                "Brak pliku",
                "Najpierw wybierz plik index.html."
            )

            return

        index_path = Path(path_text)

        if not index_path.is_file():

            messagebox.showerror(
                "Nie znaleziono pliku",
                f"Nie znaleziono pliku:\n\n{index_path}"
            )

            return

        # ------------------------------------------------------
        # DANE
        # ------------------------------------------------------

        date = self.date_entry.get().strip()

        title = self.title_entry.get().strip()

        content = self.content_text.get(
            "1.0",
            "end-1c"
        ).strip()

        # ------------------------------------------------------
        # WALIDACJA
        # ------------------------------------------------------

        if not date:

            messagebox.showwarning(
                "Brak daty",
                "Wpisz datę wpisu."
            )

            return

        if not title:

            messagebox.showwarning(
                "Brak tytułu",
                "Wpisz tytuł wpisu."
            )

            return

        if not content:

            messagebox.showwarning(
                "Brak treści",
                "Wpisz treść wpisu."
            )

            return

        # ------------------------------------------------------
        # ODCZYT INDEX.HTML
        # ------------------------------------------------------

        try:

            html = index_path.read_text(
                encoding="utf-8"
            )

        except Exception as exc:

            messagebox.showerror(
                "Błąd odczytu",
                f"Nie udało się odczytać pliku:\n\n{exc}"
            )

            return

        # ------------------------------------------------------
        # SZUKANIE PIERWSZEGO NEWS-CARD
        # ------------------------------------------------------

        marker = '<article class="news-card">'

        if marker not in html:

            messagebox.showerror(
                "Nie znaleziono miejsca",
                'W pliku nie znaleziono:\n\n'
                '<article class="news-card">\n\n'
                "Plik nie został zmieniony."
            )

            return

        # ------------------------------------------------------
        # TREŚĆ HTML
        # ------------------------------------------------------

        article_content = self.generate_content_html()

        # ------------------------------------------------------
        # ARTICLE
        # ------------------------------------------------------

        article = (
            '      <article class="news-card">\n'
            f'        <div class="news-card__date">'
            f'{escape(date)}'
            f'</div>\n'
            f'        <h3>{escape(title)}</h3>\n'
            f'{article_content}\n'
            '      </article>\n'
            '\n'
        )

        # ------------------------------------------------------
        # WSTAWIENIE PRZED PIERWSZYM WPISem
        # ------------------------------------------------------

        new_html = html.replace(
            marker,
            article + "      " + marker,
            1
        )

        # ------------------------------------------------------
        # BACKUP
        # ------------------------------------------------------

        if self.backup_var.get():

            backup_path = index_path.with_name(
                index_path.name + ".bak"
            )

            try:

                shutil.copy2(
                    index_path,
                    backup_path
                )

            except Exception as exc:

                messagebox.showerror(
                    "Błąd kopii zapasowej",
                    "Nie udało się utworzyć kopii zapasowej.\n\n"
                    f"{exc}\n\n"
                    "Plik nie został zmieniony."
                )

                return

        # ------------------------------------------------------
        # ZAPIS
        # ------------------------------------------------------

        try:

            index_path.write_text(
                new_html,
                encoding="utf-8",
                newline=""
            )

        except Exception as exc:

            messagebox.showerror(
                "Błąd zapisu",
                f"Nie udało się zapisać index.html:\n\n{exc}"
            )

            return

        # ------------------------------------------------------
        # GOTOWE
        # ------------------------------------------------------

        messagebox.showinfo(
            "Gotowe",
            "Wpis został dodany!\n\n"
            f"Data: {date}\n"
            f"Tytuł: {title}\n\n"
            f"Plik:\n{index_path}"
        )

        self.title_entry.delete(
            0,
            tk.END
        )

        self.content_text.delete(
            "1.0",
            tk.END
        )


# ==============================================================
# START
# ==============================================================

if __name__ == "__main__":

    root = tk.Tk()

    try:
        root.tk.call(
            "tk",
            "scaling",
            1.15
        )
    except tk.TclError:
        pass

    app = NewsEditor(root)

    root.mainloop()