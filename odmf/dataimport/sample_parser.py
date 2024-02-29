import re
from datetime import datetime

"""
Tools to parse sample names into sites, datasets, datetime values etc.
The parser is defined using a yml file.

Example:
"""
example = r"""
pattern: (\w+?)_([0-9\.]+_[0-9]+\:[0-9]+)_?(?:[-+]?[0-9\.]+)
site:
  group: 1
  map:
    F1: 137
    F2: 147
    F3: 201
    B1: 123
    B2: 138
    B3: 203 
date:
  group: 2
  format: "%d%m%y_%H:%M"
level:
  group: 3
"""
class SampleParserPart:
    def __init__(self, pattern: str, group: int, type: callable):
        self.pattern = re.compile(pattern)
        self.group = group
        self.type = type

    def __call__(self, sample: str):
        if match := self.pattern.match(sample):
            try:
                value = match.group(self.group)
                return self.type(value)
            except IndexError:
                return None
        else:
            return None

class SiteParser(SampleParserPart):
    def __init__(self, pattern: str, group: int, map: dict=None):
        self.map = map or {}
        super().__init__(pattern, group, self.parse_site)

    def parse_site(self, raw_site: str):
        try:
            return self.map.get(raw_site, int(raw_site))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid site, {raw_site} - does not match pattern: {self}, nor is it a number")

class DateParser(SampleParserPart):
    def __init__(self, pattern: str, group: int, format: str):
        fmt_fnct = lambda date: datetime.strptime(date, format)
        super().__init__(pattern, group, fmt_fnct)

class IntParser(SampleParserPart):
    def __init__(self, pattern: str, group: int):
        super().__init__(pattern, group, int)

class FloatParser(SampleParserPart):
    def __init__(self, pattern: str, group: int):
        super().__init__(pattern, group, float)

class SampleParser:
    """
    Parses a complex sample name consisting meta information in a condensed way

    Eg. : "F1_040222_11:40_-0.6" can be read as sample at site F1 (which is translated to 127) at 2022-02-04 11:40 at -0.6 m

    The list of parsers can easily be extended, not all parsers need to be used

    As a callable, the sample is parsed to a dictionary with site, date, dataset, level etc.

    The parsers can easily be extended use the existing partial parsers as an example. However the import
    code needs adjustment too.
    """

    parsers = {
        'time': DateParser,
        'site': SiteParser,
        'dataset': IntParser,
        'level': FloatParser,
        'instrument' : IntParser
    }

    def __init__(self, data: dict):
        pattern = data.pop('pattern')
        self.parts = {
            k: self.parsers[k](pattern=pattern, **data[k])
            for k in data
        }
    def __call__(self, sample):
        return {
            k: self.parts[k](sample)
            for k in self.parts
        }


if __name__ == '__main__':
    import yaml
    data = yaml.safe_load(example)
    print(data)
    sampler = SampleParser(data)
    print(yaml.safe_dump(sampler('F1_040720_22:41')))
    print(yaml.safe_dump(sampler('12_040720_22:42_-0.6')))
