from datetime import date, datetime


def parse_chilecompra_date(value: object | None) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def format_api_date(value: date) -> str:
    return value.strftime("%d%m%Y")
