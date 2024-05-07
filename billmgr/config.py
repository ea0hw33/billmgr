import billmgr.misc
from functools import lru_cache


@lru_cache(maxsize=1)
def __get_billmgr_params():
    elems = billmgr.misc.Mgrctl("paramlist")["elem"]
    # elems - список, где каждый параметр лежит в отдельном словаре: [{'DBName', 'billmgr'}, ...].
    # Поэтому сначала идем по list'у, а внутри достаем параметр:значение из словаря
    return {key: value for elem_dict in elems for key, value in elem_dict.items()}


def get_param(name: str):
    return __get_billmgr_params().get(name, "")
