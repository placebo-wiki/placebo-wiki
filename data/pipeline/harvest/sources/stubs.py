class Stub(Exception):
    """The source is planned but not wired yet; the run reports it without raising an alert."""


def stub(reason: str):
    def fetch(substance: dict, limit: int):
        raise Stub(reason)
        yield
    return fetch


ALL = {
    "youtube": stub("нужен ключ YouTube Data API; расшифровка аудио выключена"),
    "ozon": stub("нужна сессия покупателя и сервер-посредник"),
    "wildberries": stub("нужна сессия покупателя и сервер-посредник"),
    "yandex_market": stub("нужна сессия покупателя и сервер-посредник"),
    "telegram": stub("нужна сессия Telegram и список каналов"),
}
