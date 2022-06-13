"""
@author: qiudeliang

All rights reserved.
"""

import re


def fuzzy_finder(user_input, collection):
    suggestions = []
    pattern = '.*?'.join(user_input)
    regex = re.compile(pattern)
    for item in collection:
        match = regex.search(item)
        if match:
            suggestions.append((len(match.group()),
                                match.start(),
                                item))
    return [x for _, _, x in sorted(suggestions)]
