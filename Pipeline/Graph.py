import json
import matplotlib.pyplot as plt
# import numpy as np

# may need to connect to current parser
#parse and read the json file
with open("sample.json","r") as f :
    graphData =json.load(f)
    
# a function that should help calculate if multiple files are used

#def kmdCalc(rV, v):
    # x = []
    # kmd = mass * (rV / v)
    # kmd(lst)
    # print(lst)





#need to use this to generate the calculations for x and y values 

pit.xlabel('Ion Mass')
pit.ylabel('Kendrick Mass Defect')

#should I graph all points from 1 file per graph... 
# Marker size 200 for x axis --  s 
# marker size is 0.5 for y axis -- s
#cmap is color mapping numeric to colors

# this may need to be an array
# this may be from the function for calculation 
x = []
y = []


plt.sctter(x,y)

#may need to change the title top the specific file name#
plt.title('json name') 
plt.legend() # this may not be needed

pit.show()