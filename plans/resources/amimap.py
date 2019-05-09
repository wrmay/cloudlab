import os
import sys
import yaml

inputfile = 'AmazonLinux2.txt'

if __name__ == '__main__':
	result = dict()
	region = None
	region_attributes = None
	with open(inputfile, 'r') as f:
		line = f.readline()
		while len(line) > 0:
			if 'ami' not in line:
				if region is not None:
					result[region] = region_attributes
					
				region = line.strip()
				region_attributes = dict()
			else:
				if 'ebs' in line and 'minimal' not in line:
					region_attributes['amazonlinux2ami'] = line.strip().split()[0]
					
			line = f.readline()
			
	yaml.dump(result, sys.stdout)
				
		