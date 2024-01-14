import requests


def getNeedetRate(rate: float, value: int) -> int:
    return int((4.9 - rate) * 10) * value


def get_info(art: int) -> requests.Response:
    """
    Получает доступную информацию о товаре по его артикулу

    Args:
        art (int): Артикул товара

    Returns:
        requests.Response / None: Вернёт None в случае неудачи, если данные получены вернёт Responce
    """
    for i in range(1, 20):
        try:
            r = requests.get(
                f'https://basket-{"0" if i < 10 else ""}{i}.wb.ru/vol{str(art//100000)}/part{str(art//1000)}/{art}/info/ru/card.json'
            )
        except Exception:
            return None
        if r.status_code == 200:
            return r
    return None
