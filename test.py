import re

pattern = '\((.*?)\)'
string = 'Ethernet: Support KTH125 device'

match = re.split(pattern, string)
print(match)
