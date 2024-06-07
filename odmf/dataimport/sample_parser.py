import re
from datetime import datetime

"""
Tools to parse sample names into sites, datasets, datetime values etc.
The parser is defined using a yml file.

Example:
"""
example = r"""
pattern: (\w+?)_([0-9\.]+_[0-9]+\:[0-9]+)_?([\-\+]?[0-9\.]+)?
site:
  group: 1
  map:
    F1: 137
    F2: 147
    F3: 201
    B1: 123
    B2: 138
    B3: 203 
time:
  group: 2
  format: "%d%m%y_%H:%M"
level:
  group: 3
  factor: -0.01
"""


class SampleParserPart:
    """
    Describes a section of a sample name that can be parsed into some meaningful information to find a suitable dataset.

    Used as a superclass for concrete parsings
    """
    def __init__(self, pattern: str, group: int, type: callable):
        """

        :param pattern: A re pattern to identify the sample's name part
        :param group: The group number of the re pattern
        :param type: A callable that returns the parsed object from the string part
        """
        self.pattern = re.compile(pattern)
        self.group = group
        self.type = type

    def __call__(self, sample: str):
        """
        Returns the parsed object from the sample name
        """
        if match := self.pattern.match(sample):
            try:
                value = match.group(self.group)
                return self.type(value)
            except IndexError:
                return None
        else:
            return None


class IntParser(SampleParserPart):
    """
    Parses an int from a sample name. Simple specialization of SampleParserPart.
    """
    def __init__(self, pattern: str, group: int):
        super().__init__(pattern, group, int)


class FloatParser(SampleParserPart):
    """
    Parses an float from a sample name, with an optional factor.

    The factor can be used for scaling Eg. if you need a level, the level can be given as 60 meaning 60cm below ground and translated by the
    factor -0.01 to m
    """
    def __init__(self, pattern: str, group: int, factor: float=1.0):
        super().__init__(pattern, group, self.to_float_with_factor)
        self.factor = factor

    def to_float_with_factor(self, raw_val:str):
        if raw_val:
            val = float(raw_val)
            return val * self.factor
        else:
            return None



class SiteParser(SampleParserPart):
    """
    Parses a site id (int) from a sample name.

    If the sample name includes unconventional site names, a dictionaty can be used to translate
    the site name to the site number.
    """
    def __init__(self, pattern: str, group: int, map: dict = None):
        self.map = map or {}
        super().__init__(pattern, group, self.parse_site)

    def parse_site(self, raw_site: str):
        try:
            return self.map.get(raw_site) or int(raw_site)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid site, {raw_site} - does not match pattern: {self.pattern}, nor is it a number")


class DateParser(SampleParserPart):
    """
    Parses a date from a sample name. Uses the given date format
    """
    def __init__(self, pattern: str, group: int, format: str):
        """

        :param pattern: A re pattern to identify the sample's name part
        :param group: The group number of the re pattern
        :param format: A date format eg. %Y-%m-%d
        """
        fmt_fnct = lambda date: datetime.strptime(date, format)
        super().__init__(pattern, group, fmt_fnct)



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
        'instrument': IntParser
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
    print(yaml.safe_dump(sampler('12_040720_22:42_60')))
