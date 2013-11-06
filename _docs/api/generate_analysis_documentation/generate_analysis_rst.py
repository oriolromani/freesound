# Generate skeleton for documentation, 
# add essentia documentation links by hand

import yaml


header = """
.. _analysis-docs:

Analysis Descriptor Documentation
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

.. contents::
    :depth: 3
    :backlinks: top


Analysis Settings
>>>>>>>>>>>>>>>>>

The analysis sample rate is 44100Hz and the audio file's channels are mixed down
to mono. For the lowlevel namespace the frame size is 2048 samples with a hop
size of 1024, while for the tonal namespace the frame size is 4096 and the hop
size 2048.


Acronyms for the statistics
>>>>>>>>>>>>>>>>>>>>>>>>>>>

Generally, the lowlevel descriptors have the statistics mean, max, min, var,
dmean, dmean2, dvar, and dvar2. These should be read as follows.

========= =====================================
Statistic
========= =====================================
mean      The arithmetic mean
max       The maximum value
min       The minimum value
var       The variance
dmean     The mean of the derivative
dmean2    The mean of the second derivative
dvar      The variance of the derivative
dvar2     The variance of the second derivative
========= =====================================

"""

curl_str = "    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/"
image_str = "    .. image:: _static/descriptors/"
height_str = "        :height: 300px"
algorithm_doc_str = "http://essentia.upf.edu/documentation/reference/streaming_"
sorted_namespaces = ["metadata","lowlevel","rhythm","tonal"]

top = yaml.load(open('example.yaml'))
mapping = dict()
for line in open("algorithm_mapping.csv"):
	desc,alg = line[:-1].split(",")
	mapping[desc] = alg

print header

for k in sorted_namespaces:
	ns = k[0].upper()+k[1:]
	print ns+ " Descriptors"
	print ">>>>>>>>>>>>>>>>>>>>\n\n"
	for d in top[k].keys():
		descriptor = k+"."+d
		print descriptor
		print "-------------------------"
		print "\n::\n"
		print curl_str+k+"/"+d
		if mapping[descriptor] !="None":
			print "\n**Essentia Algorithm**\n"
			print algorithm_doc_str+mapping[descriptor]+".html"
		if type(top[k][d]) ==dict:
			stats = top[k][d]
			print "\n\n**Stats**::\n\n"
			for s in stats.keys():
				print "/"+s
			if "mean" in stats.keys():
				print "\n\n**Distribution in Freesound**\n"
				if  type(stats['mean'])==list:
					for i in range(len(stats['mean'])):
						img = image_str+descriptor+".mean.%03d"%i
						print img+".png"
						print height_str
				elif  type(stats['mean'])==float:
					print image_str+descriptor+".mean.png"
					print height_str
		print "\n\n"
		