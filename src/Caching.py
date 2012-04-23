'''
Created on Apr 22, 2012

@author: yong
'''    
import tempfile 

class Caching():
    def __init__(self):
       pass
    
    def temp_file(self,in_filename,chunksize=24*1024):    
        with open(in_filename, 'rb') as infile:
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                while True:
                    chunk = infile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    temp.write(chunk)
                temp.flush()

        return temp.name