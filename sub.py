import re

text = 'Performance Call #1 - Follow UP Email To:masahisa.hashimoto@jci-hitachi.com 2018/01/19 16:20.html'
print text

# comp = re.compile('[^A-Z^a-z^0-9^ ]')
# comp.sub('', text)
# print comp

a = re.findall(r'[^\*"/:?\\|<>]', text, re.S) 
a = "".join(a)
print(a)