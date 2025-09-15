from typing import List, Tuple
from collections import Counter


class DictHelper:
    @staticmethod
    def sum_dict_values(dict_list: List[dict]):
        if dict_list:
            return dict(sum((Counter(d) for d in dict_list), Counter()))

    @staticmethod
    def sort_dict_by_values(data: dict, reverse: bool = False):
        """ "
        Returns a new dictionary sorted by values.

        Args:
            d (dict): The dictionary to sort.
            reverse (bool): Set to True for descending order.

        Returns:
            dict: A new dictionary sorted by values.
        """
        return dict(sorted(data.items(), key=lambda c: c[1], reverse=reverse))

    @staticmethod
    def remove_keys(data: dict, keys: List[str]):
        for key in keys:
            if key in data:
                del data[key]
        return data

    @staticmethod
    def include_keys(data: dict, keys: List[str]):
        """
        Modifies the dictionary in place, keeping only the specified keys.

        Args:
            data (dict): The original dictionary to modify.
            keys (List[str]): The list of keys to retain.
        """
        for key in list(data.keys()):
            if key not in keys:
                del data[key]

    @staticmethod
    def extract_multiple_keys(data: dict, keys: List[str]) -> Tuple:
        """
        Extracts values from a dictionary for multiple keys, maintaining order.

        Args:
            data (dict): The dictionary to extract values from.
            keys (List[str]): The list of keys to extract values for.

        Returns:
            Tuple: A tuple of values corresponding to the provided keys.
                Missing keys will return None.
        """
        return tuple(data.get(key) for key in keys)
