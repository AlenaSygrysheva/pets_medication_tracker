"""Renders a pet's card (PetReportData) into PDF bytes with fpdf2.

DejaVu Sans is bundled in app/assets/fonts because the built-in PDF fonts have no
Cyrillic and the Docker image has no system fonts.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from fpdf import FPDF

if TYPE_CHECKING:
    from app.services.pet_report_service import PetReportData

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT = "DejaVu"

SEX_LABELS = {"male": "самец", "female": "самка", "unknown": "неизвестно"}
REPRODUCTIVE_LABELS = {
    "intact": "не стерилизовано",
    "sterilized": "стерилизовано",
    "unknown": "неизвестно",
}

TEXT = (33, 37, 41)
MUTED = (108, 117, 125)
ACCENT = (59, 130, 246)  # matches the app's blue-500


def _d(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _t(value: datetime, time_format: str) -> str:
    if time_format == "12":
        return f"{value.hour % 12 or 12}:{value.minute:02d} {'AM' if value.hour < 12 else 'PM'}"
    return f"{value.hour:02d}:{value.minute:02d}"


def _times_per_day(n: int) -> str:
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} раза в день"
    return f"{n} раз в день"


class _CardPdf(FPDF):
    def __init__(self, pet_name: str):
        super().__init__(format="A4")
        self.pet_name = pet_name
        self.add_font(FONT, "", str(FONTS_DIR / "DejaVuSans.ttf"))
        self.add_font(FONT, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(auto=True, margin=16)
        self.set_title(f"Карточка питомца — {pet_name}")
        self.set_creator("PetMed")

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(FONT, "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"{self.pet_name} · стр. {self.page_no()}/{{nb}}", align="R")

    # --- building blocks ---------------------------------------------------
    def section(self, title: str) -> None:
        if self.get_y() > self.h - 50:  # don't leave a heading alone at the bottom
            self.add_page()
        self.ln(4)
        self.set_font(FONT, "B", 14)
        self.set_text_color(*TEXT)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def subsection(self, title: str) -> None:
        self.ln(2)
        self.set_font(FONT, "B", 11.5)
        self.set_text_color(*TEXT)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def field(self, label: str, value: str) -> None:
        # write() instead of markdown so "**" in user text can't change formatting.
        self.set_text_color(*TEXT)
        self.set_font(FONT, "B", 10.5)
        self.write(6, f"{label}: ")
        self.set_font(FONT, "", 10.5)
        self.write(6, value)
        self.ln(6)

    def para(self, value: str, *, muted: bool = False, size: float = 10.5, indent: float = 0) -> None:
        self.set_text_color(*(MUTED if muted else TEXT))
        self.set_font(FONT, "", size)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 5.5, value, new_x="LMARGIN", new_y="NEXT")

    def _height(self, value: str, line_h: float, style: str, indent: float = 0) -> float:
        self.set_font(FONT, style, 10.5)
        width = self.w - self.l_margin - self.r_margin - indent
        return line_h * len(self.multi_cell(width, line_h, value, dry_run=True, output="LINES"))

    def item(self, head: str, lines: list[str]) -> None:
        """A list entry: bold first line, then indented detail lines. Kept on one
        page when it fits on one."""
        needed = self._height(head, 6, "B") + sum(self._height(line, 5.5, "", 5) for line in lines) + 2.5
        if self.get_y() + needed > self.page_break_trigger and needed < self.page_break_trigger - self.t_margin:
            self.add_page()
        self.set_text_color(*TEXT)
        self.set_font(FONT, "B", 10.5)
        self.multi_cell(0, 6, head, new_x="LMARGIN", new_y="NEXT")
        for line in lines:
            self.para(line, indent=5)
        self.ln(2.5)


def render_pet_report(data: PetReportData) -> bytes:
    pet, req = data.pet, data.request
    tf = req.time_format
    pdf = _CardPdf(pet.name)
    pdf.add_page()

    # Title
    pdf.set_font(FONT, "B", 20)
    pdf.set_text_color(*TEXT)
    pdf.cell(0, 11, f"Карточка питомца: {pet.name}", new_x="LMARGIN", new_y="NEXT")
    pdf.para(f"Сформирована {_d(data.generated_on)}", muted=True, size=9.5)

    # 1. General info
    pdf.section("Общая информация")
    pdf.field("Кличка", pet.name)
    pdf.field("Пол", SEX_LABELS.get(pet.sex, "неизвестно"))
    pdf.field("Вес", f"{pet.weight_kg:g} кг" if pet.weight_kg else "не указан")
    pdf.field("Репродуктивность", REPRODUCTIVE_LABELS.get(pet.reproductive_status, "неизвестно"))

    # 2. Diagnoses
    pdf.section("Диагнозы")
    if not data.diagnoses:
        pdf.para("Диагнозы не выбраны", muted=True)
    for d in data.diagnoses:
        confirmed = (
            f"Подтверждён врачом{': ' + d.doctor_name if d.doctor_name else ''}"
            if d.confirmed_by_vet else "Не подтверждён врачом"
        )
        lines = [confirmed]
        if d.comments:
            lines.append(f"Комментарий: {d.comments}")
        pdf.item(d.name, lines)

    # 3. Treatment for the chosen period
    pdf.section("Лечение")
    pdf.para(f"Период: {_d(req.date_from)} — {_d(req.date_to)}", muted=True, size=9.5)

    pdf.subsection("Препараты")
    if not data.courses:
        pdf.para("За этот период курсов не было", muted=True)
    for c in data.courses:
        if c.status == "active":
            head = f"В процессе — {c.drug}"
            period = f"Начало: {_d(c.start)}, окончание: {_d(c.end)}"
        else:
            head = f"Завершён — {c.drug}"
            period = f"Начало: {_d(c.start)}, конец: {_d(c.end)}"
            if c.status == "cancelled":
                period += " (курс отменён)"
        pdf.item(head, [f"Дозировка: {c.dosage}, {_times_per_day(c.frequency_per_day)}", period])

    pdf.subsection("Приёмы врача")
    if not data.vet_visits:
        pdf.para("За этот период приёмов не было", muted=True)
    for v in data.vet_visits:
        lines = [f"Клиника: {v.clinic_name}"]
        if v.clinic_address:
            lines.append(f"Адрес: {v.clinic_address}")
        if v.clinic_phone:
            lines.append(f"Телефон: {v.clinic_phone}")
        if v.clinic_website:
            lines.append(f"Сайт: {v.clinic_website}")
        if v.doctor_name:
            lines.append(f"Врач: {v.doctor_name}")
        if v.comments:
            lines.append(f"Комментарий: {v.comments}")
        status = "состоялся" if v.completed else "запланирован"
        pdf.item(f"{_d(v.appointment_at.date())} {_t(v.appointment_at, tf)} — {status}", lines)

    # 4. Diary: optional, only when entries were picked
    if data.diary_entries:
        pdf.section("Дневник состояния")
        shift = timedelta(minutes=req.tz_offset_minutes)
        for e in data.diary_entries:
            local = e.created_at.replace(tzinfo=None) - shift
            pdf.item(f"{_d(local.date())} {_t(local, tf)}", [e.text])

    return bytes(pdf.output())
