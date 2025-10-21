import json
import matplotlib.pyplot as plt
import numpy as np

# create a baby parser to read the Json 


# may need to connect to current parser
#parse and read the json file
with open("CVBS_1_Dis_neg_1.json","r") as f :
    graphData = json.load(f)
    
# a function that should help calculate if multiple files are used

#def kmdCalc(rV, v):
    # x = []
    # kmd = mass * (rV / v)
    # kmd(lst)
    # print(lst)

x = [float(entry["base_peak_mz"]) for entry in graphData]
y = [float(entry["base_peak_intensity"]) for entry in graphData]

plt.xlim(150,800)
#need to use this to generate the calculations for x and y values 

plt.xlabel('Ion Mass')
plt.ylabel('Kendrick Mass Defect')

#should I graph all points from 1 file per graph... 
# Marker size 200 for x axis --  s 
# marker size is 0.5 for y axis -- s
#cmap is color mapping numeric to colors

# this may need to be an array
# this may be from the function for calculation 



plt.scatter(x,y)
plt.title('KMD Signal to Noise Dertermination Plot') 
#plt.legend() # this may not be needed
plt.show()